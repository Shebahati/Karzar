#!/usr/bin/env python3
"""Build immutable official INSIZE rebuild plan from reconstruction evidence.

Read-only against production. Writes plan artifacts under data/catalog-target/
and review package under .local-scratch/insize-official-writer/.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.official_insize_rebuild import (  # noqa: E402
    ApplyAbort,
    build_plan_from_evidence,
    sha256_file,
    write_csv,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=ROOT / ".local-scratch/insize-wave1-official-rebuild",
    )
    parser.add_argument(
        "--snapshot-csv",
        type=Path,
        default=ROOT / ".local-scratch/insize-wave1-quality-audit/wave1_158_snapshot.csv",
    )
    parser.add_argument(
        "--allowlist-csv",
        type=Path,
        default=ROOT
        / ".local-scratch/global-commerce-safety-containment/approved_sale_allowlist_158.csv",
    )
    parser.add_argument(
        "--priority-csv",
        type=Path,
        default=ROOT / ".local-scratch/insize-wave1-quality-audit/wave1_priority_queue.csv",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / ".local-scratch/insize-official-writer",
    )
    parser.add_argument(
        "--plan-csv",
        type=Path,
        default=ROOT / "data/catalog-target/insize_official_rebuild_plan.csv",
    )
    parser.add_argument(
        "--plan-json",
        type=Path,
        default=ROOT / "data/catalog-target/insize_official_rebuild_plan.json",
    )
    args = parser.parse_args(argv)

    try:
        built = build_plan_from_evidence(
            evidence_dir=args.evidence_dir,
            snapshot_csv=args.snapshot_csv,
            allowlist_csv=args.allowlist_csv,
            priority_csv=args.priority_csv,
        )
    except ApplyAbort as exc:
        print(f"ABORT: {exc}", file=sys.stderr)
        return 2

    plan_rows = built["plan_rows"]
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    plan_fields = [
        "product_id",
        "site_sku",
        "current_name",
        "proposed_name",
        "current_short_description_hash",
        "proposed_short_description",
        "current_description_hash",
        "proposed_description",
        "current_specifications_hash",
        "proposed_specifications",
        "current_meta_title",
        "proposed_meta_title",
        "current_meta_description_hash",
        "proposed_meta_description",
        "official_model",
        "official_product_name",
        "official_source_id",
        "official_source_page",
        "official_fact_count",
        "mapping_class",
        "title_class",
        "completeness",
        "priority_class",
        "expected_updated_at",
    ]
    write_csv(args.plan_csv, plan_rows, plan_fields)
    write_csv(out / "official_rebuild_plan.csv", plan_rows, plan_fields)
    plan_sha = sha256_file(args.plan_csv)

    plan_json = {
        "plan_sha256": plan_sha,
        "ready_input": built["ready_input"],
        "plan_rows": len(plan_rows),
        "stats": built["stats"],
        "writer_contract": built["writer_contract"],
        "recommended_first_apply_skus": [r["site_sku"] for r in built["recommended_first_apply"]],
        "rows": plan_rows,
    }
    args.plan_json.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "official_rebuild_plan.json").write_text(
        json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_csv(out / "title_change_review.csv", built["title_review"])
    write_csv(out / "excluded_partial.csv", built["excluded_partial"])
    write_csv(out / "excluded_ambiguous.csv", built["excluded_ambiguous"])
    write_csv(out / "excluded_material_identity.csv", built["excluded_material"])
    write_csv(out / "excluded_manual_title.csv", built["excluded_manual_title"])

    diffs = []
    for row in plan_rows:
        for field, cur_key, prop_key in [
            ("name", "current_name", "proposed_name"),
            ("short_description", "current_short_description", "proposed_short_description"),
            ("description", "current_description", "proposed_description"),
            ("specifications", "current_specifications", "proposed_specifications"),
            ("meta_title", "current_meta_title", "proposed_meta_title"),
            ("meta_description", "current_meta_description", "proposed_meta_description"),
        ]:
            cur = row.get(cur_key) or ""
            prop = row.get(prop_key) or ""
            if cur != prop:
                diffs.append(
                    {
                        "product_id": row["product_id"],
                        "sku": row["site_sku"],
                        "field": field,
                        "current_value_summary": (cur[:120] + "…") if len(cur) > 120 else cur,
                        "proposed_value_summary": (prop[:120] + "…") if len(prop) > 120 else prop,
                        "official_source": row["official_source_id"],
                        "source_page": row["official_source_page"],
                    }
                )
    write_csv(out / "content_diff_review.csv", diffs)

    # Shopmill exclusion scan across PROPOSED content only (legacy current_* may mention Shopmill).
    matches = []
    for row in plan_rows:
        blob = "\n".join(
            [
                str(row.get("proposed_name") or ""),
                str(row.get("proposed_short_description") or ""),
                str(row.get("proposed_description") or ""),
                str(row.get("proposed_specifications") or ""),
                str(row.get("proposed_meta_title") or ""),
                str(row.get("proposed_meta_description") or ""),
                str(row.get("official_source_id") or ""),
            ]
        )
        if re.search(r"shopmill|shopmilltools", blob, re.I):
            matches.append(f"{row['site_sku']}: proposed content contains forbidden token")
    scan_text = (
        "SHOPMILL_EXCLUSION_SCAN\n"
        "NOTE: Legacy Shopmill data was explicitly excluded from this official rebuild plan.\n"
        "Scanned fields: proposed_name, proposed_short_description, proposed_description, "
        "proposed_specifications, proposed_meta_title, proposed_meta_description, official_source_id.\n"
        f"matches={len(matches)}\n"
        + ("\n".join(matches) if matches else "OK: 0 matches\n")
    )
    (out / "shopmill_exclusion_scan.txt").write_text(scan_text, encoding="utf-8")

    summary = {
        "plan_sha256": plan_sha,
        "ready_input": built["ready_input"],
        "plan_rows": len(plan_rows),
        "stats": built["stats"],
        "recommended_first_apply_count": built["stats"]["RECOMMENDED_FIRST_APPLY_COUNT"],
        "recommended_first_apply_skus": [r["site_sku"] for r in built["recommended_first_apply"]],
        "priority_blockers_in_plan": [
            r["site_sku"] for r in plan_rows if r.get("priority_class") == "BLOCKS_CONVERSION"
        ],
        "shopmill_scan_matches": len(matches),
        "artifacts": {
            "plan_csv": str(args.plan_csv),
            "plan_json": str(args.plan_json),
            "out_dir": str(out),
        },
        "production_mutation": "ZERO",
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if len(matches) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
