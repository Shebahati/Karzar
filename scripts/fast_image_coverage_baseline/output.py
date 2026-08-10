"""External Artifact packaging for IMG-FAST-01A."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import STATES
from .contracts import BaselineError, ProductClassification, ScanResult

HISTORICAL_IMG02A = {
    "label": "historical_reference_only",
    "date": "2026-08-03",
    "database": "karzar_staging",
    "transaction_read_only": "on",
    "total_products": 5918,
    "products_with_image_rows": 1194,
    "total_product_images": 1194,
    "valid_local_image_rows": 1193,
    "external_remote_rows": 1,
    "source_doc": "docs/EXISTING_IMAGE_AUDIT.md",
}


BASELINE_CSV_FIELDS = [
    "product_id",
    "sku",
    "brand_key",
    "category_id",
    "category_slug",
    "product_name",
    "image_state",
    "primary_image_present",
    "primary_image_reference_type",
    "primary_image_reference",
    "local_file_exists",
    "decode_ok",
    "width",
    "height",
    "placeholder_flag",
    "broken_flag",
    "fast_coverage_needed",
    "notes",
]

UNIVERSE_CSV_FIELDS = [
    "product_id",
    "sku",
    "brand_key",
    "category_id",
    "category_slug",
    "product_name",
    "current_state",
    "priority_tier",
    "priority_basis",
    "reason_code",
    "current_primary_reference",
    "suggested_discovery_lane",
    "reusable_image_id",
    "reusable_image_url",
    "reusable_is_primary",
    "reusable_display_order",
    "reusable_width",
    "reusable_height",
    "reusable_selection_reason",
    "notes",
]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def state_counts(classifications: list[ProductClassification]) -> dict[str, int]:
    c = Counter(x.image_state for x in classifications)
    return {s: int(c.get(s, 0)) for s in STATES}


def build_summary(
    scan: ScanResult,
    *,
    semantic_second_run_stable: bool | None,
    drift_rows: int,
    run_label: str,
) -> dict[str, Any]:
    counts = state_counts(scan.classifications)
    catalog_total = scan.catalog_total
    summed = sum(counts[s] for s in STATES)
    ids = [c.product_id for c in scan.classifications]
    dup = len(ids) - len(set(ids))
    missing = catalog_total - len(set(ids))

    existing_repair = counts["promotable_existing_image"]
    internet = (
        counts["missing_all_images"]
        + counts["broken_only"]
        + counts["known_placeholder_only"]
    )
    ambiguous = counts["ambiguous_current_state"]
    non_usable = existing_repair + internet + ambiguous

    with_any = sum(
        1
        for c in scan.classifications
        if c.primary_image_present or c.images_count > 0
    )
    with_multi = sum(1 for c in scan.classifications if c.images_count > 1)
    with_reusable = sum(
        1 for c in scan.classifications if c.image_state == "promotable_existing_image"
    )

    brand_counter: Counter[str] = Counter()
    cat_counter: Counter[str] = Counter()
    for c in scan.classifications:
        if c.image_state in {
            "missing_all_images",
            "broken_only",
            "known_placeholder_only",
        }:
            brand_counter[c.brand_key or "(none)"] += 1
            cat_counter[c.category_slug or c.category_name or str(c.category_id) or "(none)"] += 1

    if summed != catalog_total:
        raise BaselineError(
            "reconcile",
            f"state sum {summed} != catalog_total {catalog_total}",
        )
    if dup != 0:
        raise BaselineError("reconcile", f"duplicate_product_ids_across_states={dup}")
    if missing != 0:
        raise BaselineError("reconcile", f"missing_catalog_product_ids={missing}")

    return {
        "task_id": "IMG-FAST-01A",
        "run_label": run_label,
        "completed_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authority_mode": "live_public_storefront_api",
        "database_accessed": False,
        "database_modified": False,
        "ProductImage_modified": False,
        "application_storage_mutations": 0,
        "API_write_requests": scan.counters.api_write_requests,
        "external_discovery_requests": scan.counters.external_discovery_requests,
        "images_discovered_from_third_parties": 0,
        "images_downloaded_for_application": 0,
        "images_applied": 0,
        "storefront_asset_validation_requests": scan.counters.asset_validation_requests,
        "product_list_requests": scan.counters.product_list_requests,
        "product_detail_requests": scan.counters.product_detail_requests,
        "count_429": scan.counters.count_429,
        "count_5xx_exhausted": scan.counters.count_5xx_exhausted,
        "other_exhausted_network_failures": scan.counters.other_exhausted_network_failures,
        **scan.authority_notes,
        "catalog_total": catalog_total,
        "usable_primary": counts["usable_primary"],
        "promotable_existing_image": counts["promotable_existing_image"],
        "missing_all_images": counts["missing_all_images"],
        "broken_only": counts["broken_only"],
        "known_placeholder_only": counts["known_placeholder_only"],
        "ambiguous_current_state": counts["ambiguous_current_state"],
        "existing_asset_repair_universe_total": existing_repair,
        "internet_discovery_universe_total": internet,
        "ambiguous_triage_universe_total": ambiguous,
        "total_non_usable_primary": non_usable,
        "duplicate_product_ids_across_states": dup,
        "missing_catalog_product_ids": missing,
        "products_with_any_current_image": with_any,
        "products_with_multiple_existing_images": with_multi,
        "products_with_nonprimary_reusable_asset": with_reusable,
        "top_20_brands_by_internet_discovery": brand_counter.most_common(20),
        "top_20_categories_by_internet_discovery": cat_counter.most_common(20),
        "semantic_second_run_stable": semantic_second_run_stable,
        "drift_rows": drift_rows,
        "historical_reference_only": HISTORICAL_IMG02A,
        "storefront_visibility_predicate": (
            "public non-super-admin list forces is_active=True "
            "(app/api/endpoints/products_catalog.py); soft-deleted excluded by list path"
        ),
        "coverage_entity_granularity": "one Product entity per storefront list row",
        "primary_image_selection_rule": (
            "thumbnail from get_thumbnail_url: is_primary else images[0]; "
            "images ordered (not is_primary, display_order, id)"
        ),
        "priority_tier_policy": "unassigned unless public API exposes business priority (none found)",
    }


def write_artifact_package(
    package_dir: Path,
    scan: ScanResult,
    *,
    summary: dict[str, Any],
    drift_rows: list[dict[str, Any]],
) -> list[Path]:
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=False)

    baseline_rows = []
    for c in scan.classifications:
        baseline_rows.append(
            {
                "product_id": c.product_id,
                "sku": c.sku,
                "brand_key": c.brand_key or "",
                "category_id": c.category_id if c.category_id is not None else "",
                "category_slug": c.category_slug or "",
                "product_name": c.name,
                "image_state": c.image_state,
                "primary_image_present": c.primary_image_present,
                "primary_image_reference_type": "thumbnail_url" if c.primary_image_present else "none",
                "primary_image_reference": c.primary_image_reference or "",
                "local_file_exists": "",
                "decode_ok": "" if c.primary_decode_ok is None else c.primary_decode_ok,
                "width": c.primary_width if c.primary_width is not None else "",
                "height": c.primary_height if c.primary_height is not None else "",
                "placeholder_flag": c.placeholder_flag,
                "broken_flag": c.broken_flag,
                "fast_coverage_needed": c.fast_coverage_needed,
                "notes": c.notes,
            }
        )
    _write_csv(package_dir / "catalog-image-baseline.csv", BASELINE_CSV_FIELDS, baseline_rows)

    def universe_row(c: ProductClassification) -> dict[str, Any]:
        return {
            "product_id": c.product_id,
            "sku": c.sku,
            "brand_key": c.brand_key or "",
            "category_id": c.category_id if c.category_id is not None else "",
            "category_slug": c.category_slug or "",
            "product_name": c.name,
            "current_state": c.image_state,
            "priority_tier": c.priority_tier,
            "priority_basis": c.priority_basis,
            "reason_code": c.reason_code,
            "current_primary_reference": c.primary_image_reference or "",
            "suggested_discovery_lane": c.suggested_discovery_lane or "",
            "reusable_image_id": c.reusable_image_id if c.reusable_image_id is not None else "",
            "reusable_image_url": c.reusable_image_url or "",
            "reusable_is_primary": "" if c.reusable_is_primary is None else c.reusable_is_primary,
            "reusable_display_order": ""
            if c.reusable_display_order is None
            else c.reusable_display_order,
            "reusable_width": c.reusable_width if c.reusable_width is not None else "",
            "reusable_height": c.reusable_height if c.reusable_height is not None else "",
            "reusable_selection_reason": c.reusable_selection_reason or "",
            "notes": c.notes,
        }

    fast = [c for c in scan.classifications if c.fast_coverage_needed]
    repair = [c for c in scan.classifications if c.image_state == "promotable_existing_image"]
    internet = [
        c
        for c in scan.classifications
        if c.image_state in {"missing_all_images", "broken_only", "known_placeholder_only"}
    ]
    amb = [c for c in scan.classifications if c.image_state == "ambiguous_current_state"]

    _write_csv(package_dir / "fast-coverage-universe.csv", UNIVERSE_CSV_FIELDS, [universe_row(c) for c in fast])
    _write_csv(
        package_dir / "existing-asset-repair-universe.csv",
        UNIVERSE_CSV_FIELDS,
        [universe_row(c) for c in repair],
    )
    _write_csv(
        package_dir / "internet-discovery-universe.csv",
        UNIVERSE_CSV_FIELDS,
        [universe_row(c) for c in internet],
    )
    _write_csv(
        package_dir / "ambiguous-triage-universe.csv",
        UNIVERSE_CSV_FIELDS,
        [universe_row(c) for c in amb],
    )

    # coverage aggregates
    by_brand: Counter[tuple[str, str]] = Counter()
    by_cat: Counter[tuple[str, str]] = Counter()
    by_state: Counter[str] = Counter()
    for c in scan.classifications:
        by_state[c.image_state] += 1
        by_brand[(c.brand_key or "(none)", c.image_state)] += 1
        by_cat[(c.category_slug or str(c.category_id) or "(none)", c.image_state)] += 1

    _write_csv(
        package_dir / "coverage-by-brand.csv",
        ["brand_key", "image_state", "count"],
        [{"brand_key": b, "image_state": s, "count": n} for (b, s), n in sorted(by_brand.items())],
    )
    _write_csv(
        package_dir / "coverage-by-category.csv",
        ["category_key", "image_state", "count"],
        [{"category_key": k, "image_state": s, "count": n} for (k, s), n in sorted(by_cat.items())],
    )
    _write_csv(
        package_dir / "coverage-by-image-state.csv",
        ["image_state", "count"],
        [{"image_state": s, "count": by_state[s]} for s in STATES],
    )

    asset_rows = []
    for v in scan.asset_validations:
        asset_rows.append(
            {
                "normalized_url": v.normalized_url,
                "url": v.url,
                "http_status": v.http_status if v.http_status is not None else "",
                "final_url": v.final_url or "",
                "content_type": v.content_type or "",
                "byte_size": v.byte_size if v.byte_size is not None else "",
                "decode_ok": v.decode_ok,
                "width": v.width if v.width is not None else "",
                "height": v.height if v.height is not None else "",
                "sha256": v.sha256 or "",
                "is_known_placeholder": v.is_known_placeholder,
                "error": v.error or "",
                "transient_exhausted": v.transient_exhausted,
            }
        )
    _write_csv(
        package_dir / "asset-validation.csv",
        [
            "normalized_url",
            "url",
            "http_status",
            "final_url",
            "content_type",
            "byte_size",
            "decode_ok",
            "width",
            "height",
            "sha256",
            "is_known_placeholder",
            "error",
            "transient_exhausted",
        ],
        asset_rows,
    )

    _write_csv(
        package_dir / "run-drift.csv",
        [
            "product_id",
            "run1_state",
            "run2_state",
            "run1_thumbnail",
            "run2_thumbnail",
            "change_reason",
        ],
        drift_rows,
    )

    (package_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    readme = f"""# IMG-FAST-01A — Live storefront catalog image baseline

Authority mode: **live public storefront API** (explicit `--api-base`; no code default).

This package is a **read-only baseline**. It does not discover, download-for-apply, or mutate ProductImage rows.

## Counts

- catalog_total: {summary['catalog_total']}
- usable_primary: {summary['usable_primary']}
- promotable_existing_image: {summary['promotable_existing_image']}
- missing_all_images: {summary['missing_all_images']}
- broken_only: {summary['broken_only']}
- known_placeholder_only: {summary['known_placeholder_only']}
- ambiguous_current_state: {summary['ambiguous_current_state']}

## Universes

- existing_asset_repair_universe: {summary['existing_asset_repair_universe_total']}
- internet_discovery_universe: {summary['internet_discovery_universe_total']}
- ambiguous_triage_universe: {summary['ambiguous_triage_universe_total']}
- total_non_usable_primary: {summary['total_non_usable_primary']}

## Historical reference (not current authority)

See `summary.json` → `historical_reference_only` (IMG-02A-01 @ 2026-08-03).

## Safety

- database_accessed: false
- database_modified: false
- ProductImage_modified: false
- API_write_requests: 0
- external_discovery_requests: 0
"""
    (package_dir / "README.md").write_text(readme, encoding="utf-8")

    payload_files = sorted(
        p for p in package_dir.iterdir() if p.is_file() and p.name != "checksums.sha256"
    )
    lines = []
    for p in payload_files:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {p.name}")
    (package_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return payload_files + [package_dir / "checksums.sha256"]


def verify_checksums(package_dir: Path) -> dict[str, int]:
    checksum_file = package_dir / "checksums.sha256"
    if not checksum_file.is_file():
        raise BaselineError("checksum", "checksums.sha256 missing")
    listed: dict[str, str] = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(None, 1)
        listed[name.strip()] = digest.strip()
    regular = [
        p for p in package_dir.iterdir() if p.is_file() and p.name != "checksums.sha256"
    ]
    failures = 0
    for p in regular:
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        exp = listed.get(p.name)
        if exp is None or exp != got:
            failures += 1
    uncovered = sum(1 for p in regular if p.name not in listed)
    extra = sum(1 for name in listed if not (package_dir / name).is_file())
    return {
        "checksum_entries": len(listed),
        "regular_payload_files_excluding_checksums_file": len(regular),
        "checksum_failures": failures + extra,
        "checksum_uncovered_files": uncovered,
    }


def zip_package(package_dir: Path, zip_path: Path) -> str:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(package_dir.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=p.relative_to(package_dir).as_posix())
    return hashlib.sha256(zip_path.read_bytes()).hexdigest()
