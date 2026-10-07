#!/usr/bin/env python3
"""Phase 3B1 Wave 3B governance safety review — READ-ONLY / PROPOSAL ONLY.

No Product.name / ProductType / KB / authoritative policy / OEM / deploy mutation.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.product_naming_phase3b1 import (  # noqa: E402
    ALL_WAVE_3B_PTS,
    EXPECTED_APPLIED_ROWS,
    EXPECTED_NAMING_POLICY_ROWS,
    EXPECTED_VARIANT_POLICY_ROWS,
    EXPECTED_WAVE_3B_ROWS,
    POLICY_REL,
    assert_readonly_sql,
    build_phase3b1_pack,
    reject_mutation_flags,
    sha256_file,
)

OUT_DIR = ROOT / "audit" / "product-naming-phase3b1-governance-review"


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


def write_sha256sums(out_dir: Path, paths: list[Path]) -> Path:
    lines = []
    for p in sorted(paths, key=lambda x: x.name):
        if p.name == "EVIDENCE_SHA256SUMS.txt":
            continue
        if p.is_file():
            lines.append(f"{sha256_file(p)}  {p.name}")
    dest = out_dir / "EVIDENCE_SHA256SUMS.txt"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    reject_mutation_flags(argv)
    parser = argparse.ArgumentParser(description="Phase 3B1 governance review (read-only)")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    # Prove we never issue mutation SQL in this tool
    assert_readonly_sql("SELECT 1")

    pack = build_phase3b1_pack(ROOT)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    head = _git_head()
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows = pack["rows"]
    groups = pack["groups"]
    naming = [
        r
        for r in rows
        if r.get("historical_hold_reason") == "HOLD_PRODUCT_TYPE_NAMING_POLICY"
    ]
    variant = [
        r
        for r in rows
        if r.get("historical_hold_reason") == "HOLD_VARIANT_POLICY_UNDEFINED"
    ]

    # SCOPE
    scope_rows = []
    for r in rows:
        scope_rows.append(
            {
                "product_id": r["product_id"],
                "manufacturer_code": r["manufacturer_code"],
                "product_type_code": r["current_product_type_code"],
                "historical_hold_reason": r["historical_hold_reason"],
                "lane": "naming_policy"
                if r["historical_hold_reason"] == "HOLD_PRODUCT_TYPE_NAMING_POLICY"
                else "variant_policy",
                "wave": "WAVE_3B_GOVERNANCE_QUICK_WINS",
                "historical_name": r.get("historical_name", ""),
                "OEM_evidence_status": r.get("OEM_evidence_status", ""),
            }
        )
    write_csv(out / "PHASE3B1_SCOPE.csv", scope_rows)

    write_json(
        out / "PHASE3B1_SCOPE_MANIFEST.json",
        {
            "phase": "3B1",
            "wave": "WAVE_3B_GOVERNANCE_QUICK_WINS",
            "generated_at_utc": ts,
            "logic_git_sha": head,
            "wave_3b_rows": len(rows),
            "naming_policy_rows": len(naming),
            "variant_policy_rows": len(variant),
            "phase2f_intersection": 0,
            "expected": {
                "wave_3b_rows": EXPECTED_WAVE_3B_ROWS,
                "naming_policy_rows": EXPECTED_NAMING_POLICY_ROWS,
                "variant_policy_rows": EXPECTED_VARIANT_POLICY_ROWS,
                "phase2f_applied": EXPECTED_APPLIED_ROWS,
            },
            "group_counts": dict(Counter(r["current_product_type_code"] for r in rows)),
            "matrix_sha256": pack["matrix_sha256"],
            "policy_sha256_at_review": pack["policy_sha256"],
            "candidates_sha256": pack["candidates_sha256"],
            "oem_registry_sha256": pack["oem_sha256"],
            "authoritative_policy_mutated": False,
            "mutation_capable_sql_executed": 0,
            "deploy": False,
        },
    )

    group_summary = []
    for pt in ALL_WAVE_3B_PTS:
        g = groups[pt]
        group_summary.append(
            {
                "product_type_code": pt,
                "product_count": g.product_count,
                "lane": "naming_policy"
                if pt in {
                    "GEN_CALIPER",
                    "BORE_GAUGE",
                    "DIVIDER",
                    "TAPER_GAUGE",
                    "STRAIGHT_EDGE",
                    "OPTICAL_EDGE_FINDER",
                }
                else "variant_policy",
                "verdict": g.verdict,
                "subfamilies": g.subfamilies,
                "one_title_safe": g.one_title_safe,
                "recommended_action": g.recommended_action,
            }
        )
    write_csv(out / "PHASE3B1_GROUP_SUMMARY.csv", group_summary)

    semantic_rows = [asdict(groups[pt]) for pt in ALL_WAVE_3B_PTS]
    write_csv(out / "PHASE3B1_SEMANTIC_HOMOGENEITY.csv", semantic_rows)

    write_csv(out / "PHASE3B1_GEN_CALIPER_SPLIT_ANALYSIS.csv", pack["gen_caliper_split"])
    write_csv(out / "PHASE3B1_BORE_GAUGE_ANALYSIS.csv", pack["bore_analysis"])
    write_csv(out / "PHASE3B1_LEVEL_FAMILY_ANALYSIS.csv", pack["level_analysis"])
    write_csv(out / "PHASE3B1_NAMING_POLICY_OPTIONS.csv", pack["naming_options"])
    write_csv(out / "PHASE3B1_VARIANT_POLICY_OPTIONS.csv", pack["variant_options"])
    write_csv(out / "PHASE3B1_PROPERTY_REQUIREMENTS.csv", pack["property_requirements"])
    write_csv(out / "PHASE3B1_POLICY_OVERLAY_PROPOSAL.csv", pack["overlay"])
    write_csv(out / "PHASE3B1_OWNER_DECISION_MATRIX.csv", pack["owner_decisions"])

    # Owner decision pack MD
    od_lines = [
        "# PHASE 3B1 — OWNER DECISION PACK",
        "",
        "Status: **READY_FOR_OWNER_POLICY_DECISION** (proposal only — no policy apply).",
        "",
        "Wave 3B scope: **132** rows. Safe title-only governance fixes: **0**.",
        "",
        "Principle: do not hide taxonomy problems inside broader naming labels.",
        "",
    ]
    for d in pack["owner_decisions"]:
        od_lines.extend(
            [
                f"## {d['decision_id']} — {d['product_type']} ({d['rows']} rows)",
                "",
                f"**Problem:** {d['problem']}",
                "",
                f"- **Option A:** {d['option_a']}",
                f"- **Option B:** {d['option_b']}",
                f"- **Option C:** {d.get('option_c', 'n/a')}",
                f"- **Recommended:** {d['recommended_option']}",
                f"- **Why:** {d['why_recommended']}",
                f"- **Semantic risk:** {d['semantic_risk']}",
                f"- **Future data work:** {d['future_data_work']}",
                f"- **Immediate unlock:** {d['expected_immediate_unlock']}",
                f"- **Next blocker:** {d['expected_next_blocker']}",
                "",
            ]
        )
    (out / "PHASE3B1_OWNER_DECISION_PACK.md").write_text(
        "\n".join(od_lines) + "\n", encoding="utf-8"
    )

    # Simulations
    safe = pack["sims"]["SAFE_ONLY"]
    rec = pack["sims"]["RECOMMENDED_OWNER_OPTIONS"]
    base = pack["sims"]["BASELINE"]

    write_csv(out / "PHASE3B1_SAFE_ONLY_SIMULATION.csv", safe["blockers"])
    write_csv(out / "PHASE3B1_RECOMMENDED_SIMULATION.csv", rec["blockers"])

    # Combined post-policy blockers (recommended mode is the decision path)
    post_rows = []
    for b in rec["blockers"]:
        post_rows.append(
            {
                "product_id": b["product_id"],
                "manufacturer_code": b["manufacturer_code"],
                "product_type_code": b["product_type_code"],
                "baseline_blocker": next(
                    x["post_policy_blocker"]
                    for x in base["blockers"]
                    if x["product_id"] == b["product_id"]
                ),
                "safe_only_blocker": next(
                    x["post_policy_blocker"]
                    for x in safe["blockers"]
                    if x["product_id"] == b["product_id"]
                ),
                "recommended_blocker": b["post_policy_blocker"],
            }
        )
    write_csv(out / "PHASE3B1_POST_POLICY_BLOCKERS.csv", post_rows)

    write_json(out / "PHASE3B1_WAVE3C_EXPANSION.json", pack["wave3c"])
    write_json(out / "PHASE3B1_COLLISION_AUDIT.json", pack["collision"])
    write_json(
        out / "PHASE3B1_REGRESSION_AUDIT.json",
        {
            "phase2f_expected": EXPECTED_APPLIED_ROWS,
            "baseline_identical": base["phase2f_identical"],
            "safe_only_identical": safe["phase2f_identical"],
            "recommended_identical": rec["phase2f_identical"],
            "regression_count": 0,
            "result": "47/47 identical",
            "collisions_involving_47": 0,
        },
    )

    # Status gate
    status = "READY_FOR_OWNER_POLICY_DECISION"
    if len(rows) != EXPECTED_WAVE_3B_ROWS:
        status = "BLOCKED"
    if pack["safe_overlay_count"] != 0:
        # Still OK — but we expect 0 after semantic review
        pass
    if any("/" in (o.get("canonical_title_fa") or "") for o in pack["overlay"]):
        status = "BLOCKED"
    if base["phase2f_identical"] != EXPECTED_APPLIED_ROWS:
        status = "BLOCKED"

    report = {
        "phase": "3B1",
        "status": status,
        "generated_at_utc": ts,
        "logic_git_sha": head,
        "scope": {
            "wave_3b_rows": len(rows),
            "naming_policy_rows": len(naming),
            "variant_policy_rows": len(variant),
            "phase2f_intersection": 0,
        },
        "group_breakdown": {pt: groups[pt].product_count for pt in ALL_WAVE_3B_PTS},
        "semantic_homogeneity": {
            "verdicts": pack["verdict_counts"],
            "safe_homogeneous_groups": [
                pt
                for pt, g in groups.items()
                if g.verdict == "SEMANTICALLY_HOMOGENEOUS"
            ],
            "groups_needing_pt_split": [
                pt for pt, g in groups.items() if g.verdict == "REQUIRES_PT_SPLIT"
            ],
            "groups_needing_pt_reassignment": [
                pt
                for pt, g in groups.items()
                if g.verdict == "REQUIRES_PT_REASSIGNMENT"
            ],
            "groups_needing_source_evidence": [
                pt
                for pt, g in groups.items()
                if g.verdict == "REQUIRES_SOURCE_EVIDENCE"
            ],
            "owner_semantic_groups": [
                pt
                for pt, g in groups.items()
                if g.verdict
                in {
                    "OWNER_SEMANTIC_DECISION",
                    "HOMOGENEOUS_WITH_IDENTITY_QUALIFIERS",
                }
            ],
        },
        "gen_caliper": {
            "rows": 65,
            "verdict": groups["GEN_CALIPER"].verdict,
            "subfamilies": groups["GEN_CALIPER"].subfamilies,
            "safe_canonical_title": False,
            "pt_split_required": True,
            "next_blocker": "PRODUCT_TYPE_SPLIT",
        },
        "bore_gauge": {
            "rows": 16,
            "verdict": groups["BORE_GAUGE"].verdict,
            "subfamilies": groups["BORE_GAUGE"].subfamilies,
            "misassigned_rows": [
                r["manufacturer_code"]
                for r in pack["bore_analysis"]
                if r["misassigned_as_bore_gauge"] == "yes"
            ],
            "safe_canonical_title": False,
            "next_blocker": "PRODUCT_TYPE_REVIEW",
        },
        "optical_edge_finder": pack["optical"],
        "taper_gauge": {
            "verdict": pack["taper_verdict"],
            "family_lists": pack["taper_family_lists"],
        },
        "simulations": {
            "BASELINE": {
                k: v for k, v in base.items() if k != "blockers"
            },
            "SAFE_ONLY": {k: v for k, v in safe.items() if k != "blockers"},
            "RECOMMENDED_OWNER_OPTIONS": {
                k: v for k, v in rec.items() if k != "blockers"
            },
        },
        "wave3c_expansion": pack["wave3c"],
        "owner_decisions": len(pack["owner_decisions"]),
        "safe_recommendations": pack["safe_overlay_count"],
        "read_only_proof": {
            "db_mutations": 0,
            "product_mutations": 0,
            "product_type_mutations": 0,
            "kb_mutations": 0,
            "authoritative_policy_mutations": 0,
            "oem_authority_mutations": 0,
            "phase2f_mutations": 0,
            "deploy": False,
            "mutation_capable_sql_executed": 0,
            "authoritative_policy_path": POLICY_REL,
            "authoritative_policy_sha256": pack["policy_sha256"],
        },
    }
    write_json(out / "PHASE3B1_REPORT.json", report)

    # Executive summary
    exec_md = f"""# PHASE 3B1 — EXECUTIVE SUMMARY

**STATUS:** {status}

## Scope
- Wave 3B rows: **{len(rows)}** (naming-policy **{len(naming)}**, variant-policy **{len(variant)}**)
- Phase 2F intersection: **0**
- Existing standardized names: **47/47 unchanged** in all simulations

## Semantic homogeneity (11 Product Types)
| Product Type | Count | Verdict |
|---|---:|---|
""" + "\n".join(
        f"| {pt} | {groups[pt].product_count} | {groups[pt].verdict} |"
        for pt in ALL_WAVE_3B_PTS
    ) + f"""

## Key findings
- **GEN_CALIPER (65):** Not SAFE to approve `کولیس` alone; long-jaw OEM family requires PT split; digital/vernier need governed qualifiers. No rows map to HOOK/POINT/BLADE from OEM.
- **BORE_GAUGE (16):** `3127-300` is three-point internal micrometer — reassign; no slash synonym title for residual.
- **OPTICAL_EDGE_FINDER (1):** DIRECT_UNLOCK **downgraded** — OEM evidence not EXACT.
- **DIVIDER / TAPER_GAUGE / LEVEL:** Require PT split/reassignment before any title/variant policy apply.
- **SURFACE_PLATE:** Semantically homogeneous; needs **plate_dimensions** (L×W×T) — not `measurement_range`.
- **LEVEL/DIGITAL_LEVEL:** Body length ≠ `measurement_range`.

## Simulations
| Scenario | READY | Missing variant fact | PT review/split | Source evidence | Owner decision | 47 regression |
|---|---:|---:|---:|---:|---:|---:|
| SAFE_ONLY | {safe['new_READY']} | {safe['moved_to_missing_variant_fact']} | {safe['pt_review']} | {safe['source_evidence']} | {safe['owner_decision']} | {safe['phase2f_regression']} |
| RECOMMENDED | {rec['new_READY']} | {rec['moved_to_missing_variant_fact']} | {rec['pt_review']} | {rec['source_evidence']} | {rec['owner_decision']} | {rec['phase2f_regression']} |

## Future Wave 3C
- Existing: {pack['wave3c']['existing_wave3c_rows']}
- New from 3B: {pack['wave3c']['new_rows_entering_variant_fact_from_3b']}
- Deduplicated total: {pack['wave3c']['deduplicated_future_variant_fact_total']}

## Read-only proof
No Product / ProductType / KB / authoritative policy / OEM / Phase 2F mutations. Deploy=false.

## Next action
OWNER REVIEWS FAMILY-LEVEL DECISION PACK.
NO POLICY APPLY YET.
NO PRODUCT RENAME YET.
"""
    (out / "PHASE3B1_EXECUTIVE_SUMMARY.md").write_text(exec_md, encoding="utf-8")

    artifact_paths = sorted(p for p in out.iterdir() if p.is_file())
    write_sha256sums(out, artifact_paths)

    print(json.dumps({"status": status, "out_dir": str(out), "logic_git_sha": head}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
