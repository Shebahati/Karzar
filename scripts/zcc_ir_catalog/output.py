"""Write Phase 1 artifacts. Generated crawl data belongs under /data (gitignored)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zcc_ir_catalog import PARSER_VERSION, SOURCE_SITE
from zcc_ir_catalog.models import BrandRow, CategoryMapRow, QualityIssue, ReconcileRow, SourceProduct

PRODUCT_CSV_FIELDS = [
    "source_site",
    "source_url",
    "canonical_url",
    "source_product_id",
    "source_slug",
    "source_internal_sku",
    "brand",
    "brand_normalized",
    "brand_evidence",
    "sku",
    "manufacturer_code",
    "model",
    "part_number",
    "name_fa",
    "name_original",
    "category_path",
    "source_category",
    "source_subcategory",
    "source_category_url",
    "short_description",
    "price_raw",
    "price_currency",
    "price_normalized",
    "price_status",
    "availability_raw",
    "availability_normalized",
    "main_image_url",
    "gallery_count",
    "gallery_image_urls",
    "image_source",
    "source_last_modified",
    "crawl_timestamp",
    "evidence_method",
    "parse_confidence",
    "parse_flags",
    "jsonld_brand",
    "commerce_authority",
    "parser_version",
    "product_type",
]


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "|".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _cell(row.get(k)) for k in fieldnames})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def product_csv_row(product: SourceProduct) -> dict[str, Any]:
    data = product.as_dict()
    data["category_path"] = " > ".join(product.category_path)
    data["gallery_image_urls"] = "|".join(product.gallery_image_urls)
    data["parse_flags"] = "|".join(product.parse_flags)
    return data


def build_summary(
    *,
    products: list[SourceProduct],
    brands: list[BrandRow],
    categories: list[CategoryMapRow],
    reconcile_rows: list[ReconcileRow],
    karzar_only: int,
    failures: list[dict[str, Any]],
    quality: list[QualityIssue],
    extra: dict[str, Any],
) -> dict[str, Any]:
    unique_skus = {
        (p.brand_normalized or "", p.part_number)
        for p in products
        if p.part_number
    }
    rec_counts = Counter(r.status for r in reconcile_rows)
    map_counts = Counter(c.mapping_status for c in categories)
    brand_counts = {b.normalized_brand or b.brand_source_name: b.product_count for b in brands}
    return {
        "source": SOURCE_SITE,
        "crawl_mode": "read_only",
        "parser_version": PARSER_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_products": len(products),
        "unique_skus": len(unique_skus),
        "brands": brand_counts,
        "categories": len(categories),
        "products_with_price": sum(1 for p in products if p.price_status == "ok"),
        "products_without_price": sum(1 for p in products if p.price_status != "ok"),
        "products_with_images": sum(1 for p in products if p.main_image_url),
        "products_without_images": sum(1 for p in products if not p.main_image_url),
        "existing_exact": rec_counts.get("EXISTING_EXACT", 0),
        "existing_different_content": rec_counts.get("EXISTING_DIFFERENT_CONTENT", 0),
        "existing_different_price": rec_counts.get("EXISTING_DIFFERENT_PRICE", 0),
        "existing_different_availability": rec_counts.get("EXISTING_DIFFERENT_AVAILABILITY", 0),
        "create_candidates": rec_counts.get("CREATE_CANDIDATE", 0),
        "ambiguous": rec_counts.get("AMBIGUOUS", 0),
        "review": rec_counts.get("REVIEW", 0),
        "invalid_source_record": rec_counts.get("INVALID_SOURCE_RECORD", 0),
        "karzar_only": karzar_only,
        "crawl_failures": len(failures),
        "category_mapping": dict(map_counts),
        "quality": {i.kind: i.count for i in quality},
        "production_db_mutation": False,
        **extra,
    }


def write_artifacts(
    output_dir: Path,
    *,
    products: list[SourceProduct],
    brands: list[BrandRow],
    categories: list[CategoryMapRow],
    reconcile_rows: list[ReconcileRow],
    karzar_only: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    quality: list[QualityIssue],
    summary: dict[str, Any],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "products_csv": output_dir / "zcc_ir_products.csv",
        "products_json": output_dir / "zcc_ir_products.json",
        "brands_csv": output_dir / "zcc_ir_brands.csv",
        "categories_csv": output_dir / "zcc_ir_categories.csv",
        "category_mapping_csv": output_dir / "zcc_ir_category_mapping.csv",
        "reconciliation_csv": output_dir / "zcc_ir_karzar_reconciliation.csv",
        "reconciliation_json": output_dir / "zcc_ir_karzar_reconciliation.json",
        "failures_csv": output_dir / "zcc_ir_crawl_failures.csv",
        "quality_json": output_dir / "zcc_ir_quality.json",
        "summary_json": output_dir / "zcc_ir_summary.json",
        "karzar_only_csv": output_dir / "zcc_ir_karzar_only.csv",
    }
    write_csv(paths["products_csv"], PRODUCT_CSV_FIELDS, [product_csv_row(p) for p in products])
    write_json(paths["products_json"], [p.as_dict() for p in products])
    write_csv(
        paths["brands_csv"],
        [
            "brand_source_name",
            "normalized_brand",
            "karzar_brand_match",
            "karzar_brand_id",
            "confidence",
            "status",
            "product_count",
            "evidence",
        ],
        [asdict(b) for b in brands],
    )
    write_csv(
        paths["categories_csv"],
        [
            "source_category_path",
            "source_category_name",
            "source_product_count",
            "karzar_category_id",
            "karzar_category_path",
            "mapping_status",
            "mapping_confidence",
            "mapping_reason",
        ],
        [asdict(c) for c in categories],
    )
    write_csv(
        paths["category_mapping_csv"],
        [
            "source_category_path",
            "source_category_name",
            "source_product_count",
            "karzar_category_id",
            "karzar_category_path",
            "mapping_status",
            "mapping_confidence",
            "mapping_reason",
        ],
        [asdict(c) for c in categories],
    )
    rec_fields = [
        "source_url",
        "brand_normalized",
        "manufacturer_code",
        "source_internal_sku",
        "name_fa",
        "status",
        "match_method",
        "karzar_id",
        "karzar_sku",
        "karzar_name",
        "karzar_brand",
        "source_price_toman",
        "karzar_price_toman",
        "source_availability",
        "karzar_availability",
        "review_reason",
        "commerce_authority",
        "parse_flags",
    ]
    write_csv(paths["reconciliation_csv"], rec_fields, [asdict(r) for r in reconcile_rows])
    write_json(paths["reconciliation_json"], [asdict(r) for r in reconcile_rows])
    write_csv(
        paths["failures_csv"],
        ["url", "status", "error", "phase"],
        failures,
    )
    write_csv(
        paths["karzar_only_csv"],
        ["id", "sku", "brand", "brand_key", "name", "base_price", "is_available"],
        karzar_only,
    )
    write_json(paths["quality_json"], [asdict(q) for q in quality])
    write_json(paths["summary_json"], summary)
    return {k: str(v) for k, v in paths.items()}
