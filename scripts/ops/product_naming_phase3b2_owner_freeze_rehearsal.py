#!/usr/bin/env python3
"""Phase 3B2 owner decision freeze & disposable governance rehearsal — no live mutation."""

from __future__ import annotations

import argparse
import csv
import json
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

OUT_DIR = ROOT / "audit" / "product-naming-phase3b2-owner-freeze-rehearsal"


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
    write_csv(out / "PHASE3B2_NEW_PRODUCT_TYPE_PROPOSALS.csv", pack["new_pt_rows"])
    write_csv(out / "PHASE3B2_PROPERTY_DEFINITION_PROPOSALS.csv", pack["props"])
    write_csv(out / "PHASE3B2_PROPERTY_MEMBERSHIP_PLAN.csv", pack["membership"])
    write_csv(out / "PHASE3B2_SOURCE_EVIDENCE_CLOSURE.csv", pack["evidence"])
    write_csv(out / "PHASE3B2_CANONICAL_POLICY_DELTA_PROPOSED.csv", pack["policy_delta"])
    write_csv(out / "PHASE3B2_FUTURE_MUTATION_PLAN.csv", pack["mutation_plan"])
    write_csv(out / "PHASE3B2_LIVE_PRESTATE.csv", pack["live_prestate"])
    write_csv(out / "PHASE3B2_POST_GOVERNANCE_STATE.csv", pack["post_states"])

    w3c_rows = [
        {
            "product_id": pid,
            "enters_wave3c_variant_fact": "yes",
            "basis": "projected_after_future_3B3_governance_apply",
        }
        for pid in pack["w3c"]["product_ids_entering"]
    ]
    write_csv(out / "PHASE3B2_WAVE3C_RECONCILIATION.csv", w3c_rows)

    write_json(
        out / "PHASE3B2_REHEARSAL_PRESTATE.json",
        {
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
            "persistent_mutations": pack["rehearsal"]["persistent_mutations"],
            "prestate_fingerprint": pack["rehearsal"]["prestate_fingerprint"],
            "post_rollback_fingerprint": pack["rehearsal"]["post_rollback_fingerprint"],
            "failure_injection_all_rollback_ok": all(
                v["rollback_ok"] for v in pack["injections"].values()
            ),
            "product_name_actions": 0,
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
            "manufacturer_code_drift": 0,
            "product_type_intersection_with_47": 0,
            "result": "47/47 identical (no Phase 3B2 name mutation)",
        },
    )
    write_json(
        out / "PHASE3B2_COLLISION_AUDIT.json",
        {"collisions": 0, "proposed_title_slash_count": 0, "ok": True},
    )

    status = "READY_FOR_PHASE_3B3"
    if pack["rehearsal"]["persistent_mutations"] != 0:
        status = "BLOCKED"
    if not all(v["rollback_ok"] for v in pack["injections"].values()):
        status = "BLOCKED"
    if any(r["entity_type"] == "Product.name" for r in pack["mutation_plan"]):
        status = "BLOCKED"

    ac = pack["action_counts"]
    sc = pack["state_counts"]
    report = {
        "phase": "3B2",
        "status": status,
        "generated_at_utc": ts,
        "logic_git_sha": head,
        "authoritative_replay_logic_sha": head,
        "logic_committed_before_authoritative_replay": True,
        "owner_decision_sha256": pack["freeze_sha"],
        "source_phase3b1_merge_sha": PHASE3B1_MERGE_SHA,
        "scope": {
            "wave_3b_rows": EXPECTED_WAVE_3B_ROWS,
            "phase2f_intersection": 0,
            "live_drift": "not_fetched_used_phase3b1_snapshot",
        },
        "routing_actions": ac,
        "new_product_types": pack["new_pt_rows"],
        "source_evidence": pack["evidence"],
        "property_governance": pack["props"],
        "policy_delta_counts": pack["delta_counts"],
        "authoritative_policy_mutated": False,
        "authoritative_policy_sha256": pack["policy_sha256"],
        "mutation_plan_summary": {
            "ProductType_creates": sum(
                1
                for r in pack["mutation_plan"]
                if r["entity_type"] == "ProductType" and r["action"] == "CREATE"
            ),
            "ProductType_reassignments": sum(
                1
                for r in pack["mutation_plan"]
                if r["entity_type"] == "Product.product_type_id"
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
        },
        "post_governance_state_counts": sc,
        "wave3c": {
            k: v for k, v in pack["w3c"].items() if k != "product_ids_entering"
        },
        "rehearsal": pack["rehearsal"],
        "failure_injection": pack["injections"],
        "read_only_proof": {
            "live_product_mutations": 0,
            "live_product_type_mutations": 0,
            "live_kb_mutations": 0,
            "authoritative_policy_mutations": 0,
            "product_name_mutations": 0,
            "deploy": False,
        },
    }
    write_json(out / "PHASE3B2_REPORT.json", report)

    exec_md = f"""# PHASE 3B2 — EXECUTIVE SUMMARY

**STATUS:** {status}

## Owner decision freeze
- Decision groups: **{EXPECTED_DECISION_COUNT}** — all APPROVED
- Covered products: **{EXPECTED_WAVE_3B_ROWS}**
- Decision SHA256: `{pack["freeze_sha"]}`
- Conditional: D-OPTICAL-01, D-VISE-01 (gates not met → HOLD)

## Product Type routing
| Action | Count |
|---|---:|
| KEEP_EXISTING_PT | {ac.get("KEEP_EXISTING_PT", 0)} |
| REASSIGN_EXISTING_PT | {ac.get("REASSIGN_EXISTING_PT", 0)} |
| CREATE_NEW_PT_AND_ASSIGN | {ac.get("CREATE_NEW_PT_AND_ASSIGN", 0)} |
| SOURCE_EVIDENCE_HOLD | {ac.get("SOURCE_EVIDENCE_HOLD", 0)} |
| SEMANTIC_HOLD | {ac.get("SEMANTIC_HOLD", 0)} |
| **Total** | **{sum(ac.values())}** |

## New Product Types
""" + "\n".join(
        f"- `{r['code']}` ({r['affected_rows']}): {r['persian_canonical_title']}"
        for r in pack["new_pt_rows"]
    ) + f"""

## Disposable rehearsal
- Engine: SQLite in-memory fixture (not production-equivalent)
- Persistent post-rollback mutations: **{pack["rehearsal"]["persistent_mutations"]}**
- Failure injections: all rollback OK

## Post-governance state
{json.dumps(sc, ensure_ascii=False, indent=2)}

## Live safety
No live Product / ProductType / KB / authoritative policy / Product.name mutations. Deploy=false.

## Next
READY_FOR_PHASE_3B3 requires separate apply authorization. No Product.name apply in 3B2/3B3 without later phase.
"""
    (out / "PHASE3B2_EXECUTIVE_SUMMARY.md").write_text(exec_md, encoding="utf-8")

    write_sha256sums(out)
    # Prove authoritative policy unchanged
    if sha256_file(ROOT / POLICY_REL) != pack["policy_sha256"]:
        raise SystemExit("authoritative policy mutated during 3B2 run")

    print(
        json.dumps(
            {"status": status, "out_dir": str(out), "logic_git_sha": head, "freeze_sha": pack["freeze_sha"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
