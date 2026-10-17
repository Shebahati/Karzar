#!/usr/bin/env python3
"""Recompute Phase 1B corrected reports from preserved production census (no DB I/O)."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_phase1b_baseline import (  # noqa: E402  # noqa: E402
    CANONICAL_PRESERVED_PRODUCT_METRICS,
    REMOVED_L1_HELICOIL_ROOT_IDS,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    CategoryRow,
    audit_megamenu_references,
    build_helicoil_cohort_reports,
    build_working_manifest,
    category_census_csv_fields,
    category_row_to_census_dict,
    compare_category_ids_phase0b,
    global_product_counts,
    historical_drift,
    is_tx_owner_scope_category,
    scan_numeric_category_dependencies,
    tx_owner_scope_product_ids,
    validate_product_census_export,
    write_csv,
    write_sha256sums,
)

PRESERVED_BASELINE_SHA = "dd7ab67ff10d063426600b9a5e33132fe4c78078"
ARTIFACT_NAMES = [
    "00-PRODUCTION-IDENTITY.json",
    "01-CATEGORY-CENSUS.csv",
    "02-PRODUCT-CATEGORY-CENSUS.csv",
    "03-CATEGORY-PRODUCT-METRICS.csv",
    "04-CATEGORY-PT-COVERAGE.csv",
    "05-PHASE1B-CURRENT-TARGET-WORKING-MANIFEST.csv",
    "06-OWNER-SCOPE-CANDIDATES.csv",
    "07-MIXED-SEMANTIC-CATEGORIES.csv",
    "08-NUMERIC-CATEGORY-ID-DEPENDENCIES.csv",
    "09-SEO-MEGAMENU-IMPACT-BASELINE.csv",
    "10-HISTORICAL-DRIFT.json",
    "11-CATEGORY-DRIFT-BY-ID.json",
    "11-MEGAMENU-REFERENTIAL-IMPACT.json",
    "12-HELICOIL-THREAD-REPAIR-COHORT.csv",
    "12-HELICOIL-PRODUCT-COHORT.csv",
    "08-NUMERIC-DEPENDENCY-SCAN-SUMMARY.json",
    "CORRECTION_JOURNAL.json",
    "SUMMARY.json",
    "FINAL_REPORT.md",
]


def _load_category_rows(path: Path) -> list[CategoryRow]:
    rows: list[CategoryRow] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                CategoryRow(
                    category_id=int(raw["category_id"]),
                    name=raw["name"],
                    slug=raw["slug"],
                    parent_id=int(raw["parent_id"]) if raw.get("parent_id") else None,
                    parent_name=raw.get("parent_name", ""),
                    full_path=raw.get("full_path", ""),
                    depth=int(raw.get("depth") or 0),
                    is_leaf=raw.get("is_leaf", "").lower() == "true",
                    is_selectable=raw.get("is_selectable", "").lower() == "true",
                    child_count=int(raw.get("child_count") or 0),
                    megamenu_hidden=raw.get("megamenu_hidden", "").lower() == "true",
                    megamenu_as_leaf=raw.get("megamenu_as_leaf", "").lower() == "true",
                    hesabfa_category_code=raw.get("hesabfa_category_code", ""),
                    spec_template_key=raw.get("spec_template_key", ""),
                    direct_live=int(raw.get("direct_product_count") or 0),
                    descendant_live=int(raw.get("descendant_product_count") or 0),
                    active=int(raw.get("active_count") or 0),
                    available=int(raw.get("available_count") or 0),
                    priced=int(raw.get("priced_count") or 0),
                    imaged=int(raw.get("imaged_count") or 0),
                    visible=int(raw.get("visible_count") or 0),
                    sellable=int(raw.get("sellable_count") or 0),
                    pt_assigned=int(raw.get("product_type_assigned_count") or 0),
                    pt_missing=int(raw.get("product_type_missing_count") or 0),
                )
            )
    return rows


def _preserve_original(out_dir: Path) -> Path:
    preserved = out_dir / "preserved-evidence" / PRESERVED_BASELINE_SHA[:12]
    preserved.mkdir(parents=True, exist_ok=True)
    for name in ARTIFACT_NAMES:
        src = out_dir / name
        if src.is_file() and not (preserved / name).is_file():
            shutil.copy2(src, preserved / name)
    return preserved


def _megamenu_groups_from_baseline_csv(path: Path) -> list[dict[str, str]]:
    groups: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("record_type") == "category_hub":
                continue
            if not row.get("nav_group_id"):
                continue
            groups.append(
                {
                    "nav_group_id": row.get("nav_group_id", ""),
                    "slug": row.get("slug", ""),
                    "label": row.get("label", ""),
                    "sort_order": row.get("sort_order", ""),
                    "is_enabled": row.get("is_enabled", ""),
                    "highlight": row.get("highlight", ""),
                    "root_category_ids": row.get("root_category_ids", ""),
                }
            )
    return groups


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15",
    )
    parser.add_argument("--correction-head", default="")
    args = parser.parse_args(argv)

    out_dir = args.audit_dir
    preserved = _preserve_original(out_dir)

    category_rows = _load_category_rows(out_dir / "01-CATEGORY-CENSUS.csv")
    with (out_dir / "02-PRODUCT-CATEGORY-CENSUS.csv").open(encoding="utf-8", newline="") as handle:
        products = list(csv.DictReader(handle))
    validate_product_census_export(products)

    live_ids = {r.category_id for r in category_rows}
    id_comparison = compare_category_ids_phase0b(repo_root=ROOT, current_category_ids=live_ids)
    structure = json.loads((out_dir / "10-HISTORICAL-DRIFT.json").read_text(encoding="utf-8")).get(
        "current_structure"
    ) or {}
    if not structure:
        structure = {
            "total_categories": len(category_rows),
            "l1": sum(1 for r in category_rows if r.depth == 1),
            "l2": sum(1 for r in category_rows if r.depth == 2),
            "l3": sum(1 for r in category_rows if r.depth == 3),
            "leaves": sum(1 for r in category_rows if r.is_leaf),
            "selectable": sum(1 for r in category_rows if r.is_selectable),
            "empty_categories": sum(1 for r in category_rows if r.descendant_live == 0),
            "categoryless_live_products": 0,
        }

    global_counts = global_product_counts(products)
    for key, expected in CANONICAL_PRESERVED_PRODUCT_METRICS.items():
        actual = global_counts.get(key)
        if actual != expected:
            raise RuntimeError(
                f"canonical_product_metric_mismatch key={key} expected={expected} got={actual}"
            )
    drift = historical_drift(structure, global_counts, id_comparison=id_comparison)
    if drift.get("live_products_delta") != 0:
        raise RuntimeError("historical_drift_live_products_delta_must_be_zero")
    if drift.get("sellable_delta") != 4:
        raise RuntimeError("historical_drift_sellable_delta_must_be_plus_four")
    if drift.get("visible_delta") != 0:
        raise RuntimeError("historical_drift_visible_delta_must_be_zero")
    (out_dir / "10-HISTORICAL-DRIFT.json").write_text(
        json.dumps(drift, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out_dir / "11-CATEGORY-DRIFT-BY-ID.json").write_text(
        json.dumps(id_comparison, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    depth_by_id = {r.category_id: r.depth for r in category_rows}
    name_by_id = {r.category_id: r.name for r in category_rows}
    megamenu_groups = _megamenu_groups_from_baseline_csv(out_dir / "09-SEO-MEGAMENU-IMPACT-BASELINE.csv")
    megamenu_audit = audit_megamenu_references(
        megamenu_groups=megamenu_groups,
        live_category_ids=live_ids,
        category_depth_by_id=depth_by_id,
        category_name_by_id=name_by_id,
        phase0b_removed_ids=REMOVED_L1_HELICOIL_ROOT_IDS,
    )
    (out_dir / "11-MEGAMENU-REFERENTIAL-IMPACT.json").write_text(
        json.dumps(megamenu_audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    helicoil_cat, helicoil_prod = build_helicoil_cohort_reports(category_rows, products)
    write_csv(
        out_dir / "12-HELICOIL-THREAD-REPAIR-COHORT.csv",
        list(helicoil_cat[0].keys()) if helicoil_cat else category_census_csv_fields() + ["cohort", "semantic_class"],
        helicoil_cat,
    )
    write_csv(
        out_dir / "12-HELICOIL-PRODUCT-COHORT.csv",
        list(helicoil_prod[0].keys()) if helicoil_prod else ["product_id"],
        helicoil_prod,
    )

    dep_scan = scan_numeric_category_dependencies(ROOT, live_category_names=name_by_id)
    (out_dir / "08-NUMERIC-DEPENDENCY-SCAN-SUMMARY.json").write_text(
        json.dumps(
            {
                k: v
                for k, v in dep_scan.items()
                if k != "dependencies"
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_csv(
        out_dir / "08-NUMERIC-CATEGORY-ID-DEPENDENCIES.csv",
        [
            "file",
            "line",
            "numeric_id",
            "context",
            "source_class",
            "resolved_live_category",
            "runtime_relevance",
            "risk",
            "required_future_kz_cat",
        ],
        dep_scan["dependencies"],
    )

    manifest = build_working_manifest(category_rows, products)
    if len(manifest) != 135:
        raise RuntimeError(f"manifest_row_count_expected_135 got={len(manifest)}")
    if not all(m.get("review_status") == "UNREVIEWED" for m in manifest):
        raise RuntimeError("manifest_review_status_must_remain_UNREVIEWED")
    census_by_id = {r.category_id: r for r in category_rows}
    for row in manifest:
        cid = int(row["current_category_id"])
        cat = census_by_id.get(cid)
        if cat is None:
            raise RuntimeError(f"manifest_category_missing_in_census id={cid}")
        if row["direct_product_count"] != str(cat.direct_live):
            raise RuntimeError(f"manifest_metric_mismatch direct_live id={cid}")
        if row["sellable_product_count"] != str(cat.sellable):
            raise RuntimeError(f"manifest_metric_mismatch sellable id={cid}")
    write_csv(
        out_dir / "05-PHASE1B-CURRENT-TARGET-WORKING-MANIFEST.csv",
        list(manifest[0].keys()),
        manifest,
    )

    owner_rows = [
        {**category_row_to_census_dict(r), "cohort": "TX_OWNER_001_SCOPE"}
        for r in category_rows
        if is_tx_owner_scope_category(r.category_id)
    ]
    write_csv(
        out_dir / "06-OWNER-SCOPE-CANDIDATES.csv",
        category_census_csv_fields() + ["cohort"],
        owner_rows,
    )

    owner_products = tx_owner_scope_product_ids(products)
    identity = json.loads((out_dir / "00-PRODUCTION-IDENTITY.json").read_text(encoding="utf-8"))
    identity["read_only_transaction_enforcement"] = (
        "v2_code_requires_explicit_read_only_transactions_for_live_reruns"
    )
    identity["collection_consistency_note"] = (
        "Preserved census collected in an observation window (2026-10-15T09:34:39Z); "
        "not a single atomic DB snapshot. Corrections recomputed from preserved CSV evidence."
    )
    (out_dir / "00-PRODUCTION-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = {
        "status": "READY_FOR_OWNER_REVIEW",
        "correction_applied_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preserved_baseline_sha": PRESERVED_BASELINE_SHA,
        "preserved_evidence_dir": str(preserved),
        "identity": identity,
        "structure": structure,
        "global_product_counts": global_counts,
        "category_id_drift": id_comparison,
        "megamenu_referential_impact": {
            "missing_refs": len(megamenu_audit.get("missing_category_references", [])),
            "historical_removed_refs": len(
                megamenu_audit.get("historical_removed_category_references", [])
            ),
        },
        "helicoil_cohort": {
            "category_rows": len(helicoil_cat),
            "product_rows": len(helicoil_prod),
            "category_55_direct_live": next(
                (r.direct_live for r in category_rows if r.category_id == 55),
                0,
            ),
        },
        "numeric_dependency_scan": {
            "raw_hit_count": dep_scan["raw_hit_count"],
            "deduped_source_hits": dep_scan["deduped_hit_count"],
            "excluded_generated_path_skips": dep_scan["excluded_generated_path_skips"],
            "hits_by_source_class": dep_scan["hits_by_source_class"],
            "watchlist_unresolved_count": len(dep_scan["watchlist_unresolved_hits"]),
        },
        "manifest_rows": len(manifest),
        "manifest_unreviewed": sum(1 for m in manifest if m.get("review_status") == "UNREVIEWED"),
        "owner_scope_categories": len(TX_OWNER_SCOPE_CATEGORY_IDS),
        "owner_scope_products_unique": len(owner_products),
        "tx_owner_scope_category_ids": sorted(TX_OWNER_SCOPE_CATEGORY_IDS),
    }
    (out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    journal = {
        "preserved_original_sha": PRESERVED_BASELINE_SHA,
        "preserved_copy_path": str(preserved),
        "correction_head": args.correction_head or "pending_commit",
        "corrected_at_utc": summary["correction_applied_at_utc"],
        "defects_addressed": [
            "category_drift_by_id_with_removed_186_187_188",
            "megamenu_dangling_references_report",
            "helicoil_zwnj_normalization",
            "numeric_dependency_generated_exclusion_and_classification",
            "readonly_transaction_enforcement_in_code",
            "tx_owner_scope_ids_157_158_159_160",
            "readonly_psql_output_parsing_and_bypass_prevention",
            "product_census_schema_aware_global_metrics",
        ],
        "production_rerun": False,
        "limitations": [
            "Census CSVs unchanged from preserved snapshot; megamenu/dependency/helicoil reports recomputed.",
        ],
    }
    (out_dir / "CORRECTION_JOURNAL.json").write_text(
        json.dumps(journal, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = (out_dir / "FINAL_REPORT.md").read_text(encoding="utf-8")
    appendix = f"""
## Correction pass ({summary['correction_applied_at_utc']})

- Preserved original evidence: `{preserved}`
- Removed L1 categories (Phase 0B → current): {id_comparison.get('removed_category_ids')}
- Megamenu dangling refs: {summary['megamenu_referential_impact']}
- Helicoil cohort categories: {summary['helicoil_cohort']['category_rows']} (cat 55 direct={summary['helicoil_cohort']['category_55_direct_live']})
- Numeric deps: raw={dep_scan['raw_hit_count']} deduped={dep_scan['deduped_hit_count']} generated_skips={dep_scan['excluded_generated_path_skips']}
"""
    if "## Correction pass" not in report:
        (out_dir / "FINAL_REPORT.md").write_text(report + appendix, encoding="utf-8")

    write_sha256sums(out_dir, [n for n in ARTIFACT_NAMES if (out_dir / n).is_file()])
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
