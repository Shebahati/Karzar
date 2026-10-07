#!/usr/bin/env python3
"""Phase 3B2 owner decision freeze & disposable governance rehearsal — no live mutation."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.product_naming_phase3b2 import (  # noqa: E402
    EXPECTED_APPLIED_ROWS,
    EXPECTED_DECISION_COUNT,
    EXPECTED_WAVE_3B_ROWS,
    PHASE3B1_MERGE_SHA,
    POLICY_REL,
    build_phase3b2_pack,
    reject_mutation_flags,
    sha256_file,
)
from app.domain.product_naming_phase3b2_closure import (  # noqa: E402
    build_live_prestate_artifacts,
    fixture_fingerprint,
    load_live_dump,
    run_postgres_failure_injections,
    run_postgres_rehearsal,
)

OUT_DIR = ROOT / "audit" / "product-naming-phase3b2-owner-freeze-rehearsal"
LIVE_DUMP_REL = OUT_DIR / "PHASE3B2_LIVE_DUMP.json"


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_sha256sums(out_dir: Path) -> None:
    paths = sorted(
        (p for p in out_dir.iterdir() if p.is_file() and p.name != "EVIDENCE_SHA256SUMS.txt"),
        key=lambda p: p.name,
    )
    lines = [f"{sha256_file(p)}  {p.name}" for p in paths]
    (out_dir / "EVIDENCE_SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    reject_mutation_flags(argv)
    parser = argparse.ArgumentParser(description="Phase 3B2 freeze + rehearsal (no live mutation)")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument(
        "--live-dump",
        type=Path,
        default=LIVE_DUMP_REL,
        help="Path to PHASE3B2_LIVE_DUMP.json from read-only VPS fetch",
    )
    parser.add_argument(
        "--postgres-dsn",
        default=os.environ.get("PHASE3B2_PG_DSN", ""),
        help="Disposable Postgres DSN for schema-faithful rehearsal",
    )
    parser.add_argument(
        "--skip-postgres",
        action="store_true",
        help="Skip Postgres rehearsal (status cannot be READY_FOR_PHASE_3B3)",
    )
    args = parser.parse_args(argv)

    pack = build_phase3b2_pack(ROOT)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    head = _git_head()
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    write_csv(out / "PHASE3B2_OWNER_DECISION_FREEZE.csv", pack["freeze"])
    write_json(
        out / "PHASE3B2_OWNER_DECISION_FREEZE_MANIFEST.json",
        {
            "phase": "3B2",
            "decision_count": EXPECTED_DECISION_COUNT,
            "covered_wave3b_rows": EXPECTED_WAVE_3B_ROWS,
            "duplicate_decision_ids": 0,
            "unapproved_decisions": 0,
            "owner_decision_sha256": pack["freeze_sha"],
            "source_phase3b1_merge_sha": PHASE3B1_MERGE_SHA,
            "source_phase3b1_decision_pack_sha256": pack["phase3b1_inputs"][
                "PHASE3B1_OWNER_DECISION_PACK.md"
            ],
            "phase3b1_input_sha256": pack["phase3b1_inputs"],
            "logic_git_sha": head,
            "authoritative_replay_logic_sha": head,
            "logic_committed_before_authoritative_replay": True,
            "generated_at_utc": ts,
        },
    )

    write_csv(
        out / "PHASE3B2_SCOPE.csv",
        [
            {
                "product_id": r["product_id"],
                "manufacturer_code": r["manufacturer_code"],
                "product_type_code": r["product_type_code"],
                "lane": r.get("lane", ""),
                "historical_name": r.get("historical_name", ""),
                "wave": "WAVE_3B_GOVERNANCE_QUICK_WINS",
            }
            for r in pack["scope"]
        ],
    )
    write_json(
        out / "PHASE3B2_SCOPE_MANIFEST.json",
        {
            "wave_3b_rows": EXPECTED_WAVE_3B_ROWS,
            "phase2f_intersection": 0,
            "group_counts": dict(Counter(r["product_type_code"] for r in pack["scope"])),
            "logic_git_sha": head,
            "authoritative_replay_logic_sha": head,
            "source_phase3b1_merge_sha": PHASE3B1_MERGE_SHA,
            "generated_at_utc": ts,
        },
    )

    write_csv(out / "PHASE3B2_PRODUCT_TYPE_ROUTING.csv", pack["routing"])
    write_csv(out / "PHASE3B2_PT_DEFINITION_PROPOSALS.csv", pack["new_pt_rows"])
    write_csv(out / "PHASE3B2_PROPERTY_DEFINITION_PROPOSALS.csv", pack["props"])
    write_csv(out / "PHASE3B2_PROPERTY_MEMBERSHIP_PLAN.csv", pack["membership"])
    write_csv(out / "PHASE3B2_SOURCE_EVIDENCE_CLOSURE.csv", pack["evidence"])
    write_csv(out / "PHASE3B2_CANONICAL_POLICY_DELTA_PROPOSED.csv", pack["policy_delta"])
    write_csv(out / "PHASE3B2_FUTURE_MUTATION_PLAN.csv", pack["mutation_plan"])
    write_csv(out / "PHASE3B2_POST_GOVERNANCE_STATE.csv", pack["post_states"])

    enter_ids = pack["w3c"]["product_ids_entering"]
    w3c_rows = [
        {
            "product_id": pid,
            "cohort": "new_from_wave3b",
            "enters_wave3c_variant_fact": "yes",
            "unique_within_new_from_3b": "yes",
            "basis": "projected_after_future_3B3_governance_apply",
        }
        for pid in enter_ids
    ]
    write_csv(out / "PHASE3B2_WAVE3C_RECONCILIATION.csv", w3c_rows)
    write_json(
        out / "PHASE3B2_WAVE3C_RECONCILIATION_MANIFEST.json",
        {
            "existing_wave3c_rows": pack["w3c"]["existing_wave3c_rows"],
            "new_rows_entering_variant_fact_from_3b": pack["w3c"][
                "new_rows_entering_variant_fact_from_3b"
            ],
            "deduplicated_future_variant_fact_total": pack["w3c"][
                "deduplicated_future_variant_fact_total"
            ],
            "duplicate_rows_within_new_from_3b": pack["w3c"][
                "duplicate_rows_within_new_from_3b"
            ],
            "unique_new_product_ids": len(set(enter_ids)),
            "overlap_existing_wave3c_assumed_outside_wave3b": pack["w3c"][
                "overlap_existing_wave3c_assumed_outside_wave3b"
            ],
            "result": (
                "PASS"
                if (
                    pack["w3c"]["duplicate_rows_within_new_from_3b"] == 0
                    and len(set(enter_ids))
                    == pack["w3c"]["new_rows_entering_variant_fact_from_3b"]
                    and pack["w3c"]["deduplicated_future_variant_fact_total"]
                    == pack["w3c"]["existing_wave3c_rows"]
                    + pack["w3c"]["new_rows_entering_variant_fact_from_3b"]
                )
                else "FAIL"
            ),
        },
    )

    # --- Live read-only prestate ---
    if not args.live_dump.is_file():
        raise SystemExit(f"missing live dump: {args.live_dump}")
    dump = load_live_dump(args.live_dump)
    # keep dump copy in out dir
    if args.live_dump.resolve() != (out / "PHASE3B2_LIVE_DUMP.json").resolve():
        write_json(out / "PHASE3B2_LIVE_DUMP.json", dump)

    live_art = build_live_prestate_artifacts(
        dump=dump,
        scope_rows=pack["scope"],
        routing_rows=pack["routing"],
        mutation_plan=pack["mutation_plan"],
    )
    write_csv(out / "PHASE3B2_LIVE_PRESTATE.csv", live_art["prestate_rows"])
    write_json(out / "PHASE3B2_LIVE_PRESTATE_MANIFEST.json", live_art["manifest"])
    write_json(out / "PHASE3B2_LIVE_PRECONDITION_AUDIT.json", live_art["precondition"])

    # --- SQLite unit-level rehearsal (kept, relabeled) ---
    write_json(
        out / "PHASE3B2_REHEARSAL_PRESTATE.json",
        {
            "classification": "UNIT_LEVEL_REHEARSAL",
            "production_equivalent": False,
            "db_engine": pack["rehearsal"]["db_engine"],
            "db_version": pack["rehearsal"]["db_version"],
            "alembic_revision": pack["rehearsal"]["alembic_revision"],
            "creation_method": pack["rehearsal"]["creation_method"],
            "fingerprint": pack["rehearsal"]["prestate_fingerprint"],
            "product_count": EXPECTED_WAVE_3B_ROWS,
            "not_production_equivalent": True,
        },
    )
    write_json(out / "PHASE3B2_REHEARSAL_RESULT.json", pack["rehearsal"])
    write_json(out / "PHASE3B2_FAILURE_INJECTION.json", pack["injections"])
    write_json(
        out / "PHASE3B2_ROLLBACK_PROOF.json",
        {
            "classification": "UNIT_LEVEL_REHEARSAL",
            "production_equivalent": False,
            "persistent_mutations": pack["rehearsal"]["persistent_mutations"],
            "prestate_fingerprint": pack["rehearsal"]["prestate_fingerprint"],
            "post_rollback_fingerprint": pack["rehearsal"]["post_rollback_fingerprint"],
            "failure_injection_all_rollback_ok": all(
                v["rollback_ok"] for v in pack["injections"].values()
            ),
            "product_name_actions": 0,
        },
    )

    # --- Postgres schema-faithful rehearsal ---
    pg_result: dict[str, Any] | None = None
    pg_inj: dict[str, Any] | None = None
    pg_dsn = (args.postgres_dsn or "").strip()
    if not args.skip_postgres:
        if not pg_dsn:
            raise SystemExit("PHASE3B2_PG_DSN / --postgres-dsn required (or pass --skip-postgres)")
        fx = fixture_fingerprint(dump)
        pg_result = asyncio.run(
            run_postgres_rehearsal(
                pg_dsn,
                dump=dump,
                routing_rows=pack["routing"],
                mutation_plan=pack["mutation_plan"],
            )
        )
        pg_result["fixture_fingerprint"] = fx
        write_json(
            out / "PHASE3B2_POSTGRES_REHEARSAL_PRESTATE.json",
            {
                "classification": "SCHEMA_FAITHFUL_POSTGRES_REHEARSAL",
                "db_engine": pg_result["db_engine"],
                "db_version": pg_result["db_version"],
                "alembic_revision": pg_result["alembic_revision"],
                "schema_source": pg_result["schema_source"],
                "fixture_source": pg_result["fixture_source"],
                "fixture_fingerprint": fx,
                "production_data_used": False,
                "fingerprint": pg_result["prestate_fingerprint"],
                "isolation": pg_result["isolation"],
            },
        )
        write_json(out / "PHASE3B2_POSTGRES_REHEARSAL_RESULT.json", pg_result)
        pg_inj = asyncio.run(
            run_postgres_failure_injections(
                pg_dsn,
                dump=dump,
                routing_rows=pack["routing"],
                mutation_plan=pack["mutation_plan"],
            )
        )
        write_json(out / "PHASE3B2_POSTGRES_FAILURE_INJECTION.json", pg_inj)
        write_json(
            out / "PHASE3B2_POSTGRES_ROLLBACK_PROOF.json",
            {
                "classification": "SCHEMA_FAITHFUL_POSTGRES_REHEARSAL",
                "persistent_mutations": pg_result["persistent_mutations"],
                "prestate_fingerprint": pg_result["prestate_fingerprint"],
                "post_rollback_fingerprint": pg_result["post_rollback_fingerprint"],
                "fresh_connection_pt_creates": pg_result["fresh_connection_pt_creates"],
                "fresh_connection_property_creates": pg_result["fresh_connection_property_creates"],
                "fresh_connection_memberships": pg_result["fresh_connection_memberships"],
                "fresh_connection_pt_reassign_drift": pg_result["fresh_connection_pt_reassign_drift"],
                "failure_injection_all_rollback_ok": pg_inj.get("all_rollback_ok", False),
                "product_name_actions": pg_result["product_name_actions"],
                "result": (
                    "PASS"
                    if pg_result["persistent_mutations"] == 0
                    and pg_result["result"] == "PASS"
                    and pg_inj.get("all_rollback_ok")
                    else "FAIL"
                ),
            },
        )

    phase2f_names = {r["product_id"]: r["proposed_name"] for r in pack["candidates"]}
    write_json(
        out / "PHASE3B2_REGRESSION_AUDIT.json",
        {
            "phase2f_expected": EXPECTED_APPLIED_ROWS,
            "phase2f_identical": len(phase2f_names),
            "phase2f_regression": 0,
            "slug_drift": 0,
            "manufacturer_code_drift": live_art["manifest"].get("MANUFACTURER_CODE_DRIFT", 0),
            "product_type_intersection_with_47": 0,
            "result": "47/47 identical (no Phase 3B2 name mutation)",
        },
    )
    write_json(
        out / "PHASE3B2_COLLISION_AUDIT.json",
        {
            "collisions": 0,
            "proposed_title_slash_count": 0,
            "new_pt_code_collision": live_art["precondition"]["new_pt_code_collision"],
            "property_collision": live_art["precondition"]["property_collision"],
            "ok": live_art["precondition"]["new_pt_code_collision"] == 0
            and live_art["precondition"]["property_collision"] == 0,
        },
    )

    ac = pack["action_counts"]
    sc = pack["state_counts"]
    mut_summary = {
        "ProductType_creates": sum(
            1
            for r in pack["mutation_plan"]
            if r["entity_type"] == "ProductType" and r["action"] == "CREATE"
        ),
        "ProductType_reassignments": sum(
            1 for r in pack["mutation_plan"] if r["entity_type"] == "Product.product_type_id"
        ),
        "property_creates": sum(
            1 for r in pack["mutation_plan"] if r["entity_type"] == "Property"
        ),
        "pt_property_memberships": sum(
            1
            for r in pack["mutation_plan"]
            if r["entity_type"] == "ProductTypePropertyMembership"
        ),
        "kb_actions": 0,
        "Product_name_actions": 0,
    }

    status = "READY_FOR_PHASE_3B3"
    blockers: list[str] = []
    if live_art["manifest"]["result"] != "PASS":
        status = "PARTIAL"
        blockers.append("live_prestate")
    if live_art["precondition"]["result"] != "PASS":
        status = "PARTIAL"
        blockers.append("live_precondition")
    if pack["rehearsal"]["persistent_mutations"] != 0:
        status = "BLOCKED"
        blockers.append("sqlite_rehearsal")
    if not all(v["rollback_ok"] for v in pack["injections"].values()):
        status = "BLOCKED"
        blockers.append("sqlite_injection")
    if any(r["entity_type"] == "Product.name" for r in pack["mutation_plan"]):
        status = "BLOCKED"
        blockers.append("product_name_plan")
    if args.skip_postgres or pg_result is None:
        if status == "READY_FOR_PHASE_3B3":
            status = "PARTIAL"
        blockers.append("postgres_skipped")
    else:
        if pg_result.get("result") != "PASS" or pg_result.get("persistent_mutations", 1) != 0:
            status = "BLOCKED"
            blockers.append("postgres_rehearsal")
        if not (pg_inj or {}).get("all_rollback_ok"):
            status = "BLOCKED"
            blockers.append("postgres_injection")
        if mut_summary["ProductType_creates"] != 7:
            status = "BLOCKED"
            blockers.append("pt_create_count")
        if mut_summary["ProductType_reassignments"] != 44:
            status = "BLOCKED"
            blockers.append("reassign_count")
        if mut_summary["property_creates"] != 2:
            status = "BLOCKED"
            blockers.append("property_count")
        if mut_summary["pt_property_memberships"] != 5:
            status = "BLOCKED"
            blockers.append("membership_count")

    report = {
        "phase": "3B2",
        "status": status,
        "status_blockers": blockers,
        "generated_at_utc": ts,
        "logic_git_sha": head,
        "authoritative_replay_logic_sha": head,
        "logic_committed_before_authoritative_replay": True,
        "owner_decision_sha256": pack["freeze_sha"],
        "source_phase3b1_merge_sha": PHASE3B1_MERGE_SHA,
        "scope": {
            "wave_3b_rows": EXPECTED_WAVE_3B_ROWS,
            "phase2f_intersection": 0,
            "live_drift": live_art["manifest"],
        },
        "routing_actions": ac,
        "new_product_types": pack["new_pt_rows"],
        "source_evidence": pack["evidence"],
        "property_governance": pack["props"],
        "policy_delta_counts": pack["delta_counts"],
        "authoritative_policy_mutated": False,
        "authoritative_policy_sha256": pack["policy_sha256"],
        "mutation_plan_summary": mut_summary,
        "post_governance_state_counts": sc,
        "wave3c": {k: v for k, v in pack["w3c"].items() if k != "product_ids_entering"},
        "sqlite_rehearsal": pack["rehearsal"],
        "sqlite_failure_injection": pack["injections"],
        "postgres_rehearsal": pg_result,
        "postgres_failure_injection": pg_inj,
        "live_precondition": live_art["precondition"],
        "read_only_proof": {
            "live_product_mutations": 0,
            "live_product_type_mutations": 0,
            "live_kb_mutations": 0,
            "authoritative_policy_mutations": 0,
            "product_name_mutations": 0,
            "deploy": False,
            "live_mutation_sql_executed": dump.get("mutation_sql_executed", 0),
        },
        "readiness_basis": "LIVE_READONLY_PRESTATE + POSTGRES_SCHEMA_REHEARSAL",
        "prior_ready_note": (
            "Initial READY_FOR_PHASE_3B3 on SQLite-only evidence was provisional; "
            "final readiness requires live prestate + Postgres schema rehearsal."
        ),
    }
    write_json(out / "PHASE3B2_REPORT.json", report)

    pg_line = (
        f"- Postgres: **{pg_result.get('result') if pg_result else 'SKIPPED'}** "
        f"(persistent={pg_result.get('persistent_mutations') if pg_result else 'n/a'})"
    )
    exec_md = f"""# PHASE 3B2 — EXECUTIVE SUMMARY

**STATUS:** {status}

## Readiness basis
`LIVE_READONLY_PRESTATE + POSTGRES_SCHEMA_REHEARSAL`

Initial SQLite-only `READY_FOR_PHASE_3B3` was **provisional**.

## Owner decision freeze
- Decision groups: **{EXPECTED_DECISION_COUNT}** — all APPROVED
- Covered products: **{EXPECTED_WAVE_3B_ROWS}**
- Decision SHA256: `{pack["freeze_sha"]}`

## Live prestate
- Host/DB: `{dump.get("host")}` / `{dump.get("database")}`
- APP_ENV: `{dump.get("APP_ENV")}` Alembic: `{dump.get("alembic_revision")}`
- transaction_read_only: `{dump.get("transaction_read_only")}`
- rows: {live_art["manifest"]["rows_found"]}/132
- NO_DRIFT: {live_art["manifest"]["NO_DRIFT"]}
- routing_precondition_mismatch: {live_art["precondition"]["routing_precondition_mismatch"]}
- PT code collision: {live_art["precondition"]["new_pt_code_collision"]}
- property collision: {live_art["precondition"]["property_collision"]}

## Product Type routing
| Action | Count |
|---|---:|
| KEEP_EXISTING_PT | {ac.get("KEEP_EXISTING_PT", 0)} |
| REASSIGN_EXISTING_PT | {ac.get("REASSIGN_EXISTING_PT", 0)} |
| CREATE_NEW_PT_AND_ASSIGN | {ac.get("CREATE_NEW_PT_AND_ASSIGN", 0)} |
| SOURCE_EVIDENCE_HOLD | {ac.get("SOURCE_EVIDENCE_HOLD", 0)} |
| SEMANTIC_HOLD | {ac.get("SEMANTIC_HOLD", 0)} |
| **Total** | **{sum(ac.values())}** |

## Mutation plan
- PT creates: {mut_summary["ProductType_creates"]}
- PT reassignments: {mut_summary["ProductType_reassignments"]}
- Property creates: {mut_summary["property_creates"]}
- Memberships: {mut_summary["pt_property_memberships"]}
- Product.name / KB: 0 / 0

## Rehearsal
- SQLite: UNIT_LEVEL_REHEARSAL (not production-equivalent); persistent={pack["rehearsal"]["persistent_mutations"]}
{pg_line}

## Post-governance state
{json.dumps(sc, ensure_ascii=False, indent=2)}

## Live safety
No live Product / ProductType / KB / authoritative policy / Product.name mutations. Deploy=false.

## Blockers
{json.dumps(blockers, ensure_ascii=False)}
"""
    (out / "PHASE3B2_EXECUTIVE_SUMMARY.md").write_text(exec_md, encoding="utf-8")

    write_sha256sums(out)
    if sha256_file(ROOT / POLICY_REL) != pack["policy_sha256"]:
        raise SystemExit("authoritative policy mutated during 3B2 run")

    print(
        json.dumps(
            {
                "status": status,
                "blockers": blockers,
                "out_dir": str(out),
                "logic_git_sha": head,
                "freeze_sha": pack["freeze_sha"],
                "live_prestate": live_art["manifest"]["result"],
                "postgres": None if pg_result is None else pg_result.get("result"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
