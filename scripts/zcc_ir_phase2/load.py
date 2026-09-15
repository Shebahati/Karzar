"""Load Phase-1 artifacts and Karzar snapshots (read-only)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from catalog_target.core import CurrentProduct
from catalog_target.snapshot import load_current_catalog
from zcc_ir_catalog.models import ReconcileRow, SourceProduct
from zcc_ir_catalog.output import PRODUCT_CSV_FIELDS, product_csv_row


def _parse_list_field(raw: str | None) -> list[str]:
    if not raw:
        return []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            pass
    return [p.strip() for p in raw.split("|") if p.strip()]


def source_product_from_dict(row: dict[str, Any]) -> SourceProduct:
    category_path = row.get("category_path")
    if isinstance(category_path, list):
        path = [str(p) for p in category_path]
    else:
        path = _parse_list_field(str(category_path or ""))
        if len(path) == 1 and " > " in path[0]:
            path = [p.strip() for p in path[0].split(" > ") if p.strip()]
    flags = row.get("parse_flags")
    if isinstance(flags, list):
        parse_flags = [str(f) for f in flags]
    else:
        parse_flags = _parse_list_field(str(flags or ""))
    gallery = row.get("gallery_image_urls")
    if isinstance(gallery, list):
        gallery_urls = [str(u) for u in gallery]
    else:
        gallery_urls = _parse_list_field(str(gallery or ""))
    specs = row.get("technical_specs")
    if not isinstance(specs, dict):
        specs = {}
    attrs = row.get("attributes")
    if not isinstance(attrs, dict):
        attrs = {}
    return SourceProduct(
        source_site=str(row.get("source_site") or "zcc.ir"),
        source_url=str(row.get("source_url") or ""),
        canonical_url=row.get("canonical_url"),
        source_product_id=row.get("source_product_id"),
        source_slug=row.get("source_slug"),
        source_internal_sku=row.get("source_internal_sku"),
        brand=row.get("brand"),
        brand_normalized=row.get("brand_normalized"),
        brand_evidence=row.get("brand_evidence"),
        sku=row.get("sku"),
        manufacturer_code=row.get("manufacturer_code"),
        model=row.get("model"),
        part_number=row.get("part_number"),
        name_fa=row.get("name_fa"),
        name_original=row.get("name_original"),
        category_path=path,
        source_category=row.get("source_category"),
        source_subcategory=row.get("source_subcategory"),
        source_category_url=row.get("source_category_url"),
        short_description=row.get("short_description"),
        description=row.get("description"),
        price_raw=row.get("price_raw"),
        price_currency=row.get("price_currency"),
        price_normalized=row.get("price_normalized"),
        price_status=row.get("price_status"),
        availability_raw=row.get("availability_raw"),
        availability_normalized=row.get("availability_normalized"),
        main_image_url=row.get("main_image_url"),
        gallery_image_urls=gallery_urls,
        technical_specs={str(k): str(v) for k, v in specs.items()},
        attributes={str(k): str(v) for k, v in attrs.items()},
        weight=row.get("weight"),
        dimensions=row.get("dimensions"),
        source_last_modified=row.get("source_last_modified"),
        crawl_timestamp=row.get("crawl_timestamp"),
        evidence_method=str(row.get("evidence_method") or ""),
        parse_confidence=str(row.get("parse_confidence") or ""),
        parse_flags=parse_flags,
        jsonld_brand=row.get("jsonld_brand"),
        image_source=row.get("image_source"),
        gallery_count=int(row.get("gallery_count") or len(gallery_urls)),
        commerce_authority=str(row.get("commerce_authority") or "SOURCE_VALUE_OBSERVED;AUTHORITY_NOT_YET_APPROVED"),
        parser_version=str(row.get("parser_version") or ""),
        product_type=row.get("product_type"),
    )


def load_phase1_products(phase1_dir: Path) -> tuple[list[SourceProduct], dict[str, Any]]:
    json_path = phase1_dir / "zcc_ir_products.json"
    csv_path = phase1_dir / "zcc_ir_products.csv"
    meta: dict[str, Any] = {"phase1_dir": str(phase1_dir)}
    if json_path.is_file():
        rows = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError(f"expected list in {json_path}")
        meta["source_file"] = str(json_path)
        return [source_product_from_dict(r) for r in rows], meta
    if csv_path.is_file():
        products: list[SourceProduct] = []
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row["category_path"] = row.get("category_path") or ""
                row["parse_flags"] = row.get("parse_flags") or ""
                row["gallery_image_urls"] = row.get("gallery_image_urls") or ""
                products.append(source_product_from_dict(row))
        meta["source_file"] = str(csv_path)
        return products, meta
    raise FileNotFoundError(f"Phase-1 products not found under {phase1_dir}")


def load_phase1_reconcile(phase1_dir: Path) -> list[ReconcileRow]:
    json_path = phase1_dir / "zcc_ir_karzar_reconciliation.json"
    if not json_path.is_file():
        return []
    rows = json.loads(json_path.read_text(encoding="utf-8"))
    out: list[ReconcileRow] = []
    for row in rows:
        out.append(
            ReconcileRow(
                source_url=str(row.get("source_url") or ""),
                brand_normalized=row.get("brand_normalized"),
                manufacturer_code=row.get("manufacturer_code"),
                source_internal_sku=row.get("source_internal_sku"),
                name_fa=row.get("name_fa"),
                status=str(row.get("status") or ""),
                match_method=row.get("match_method"),
                karzar_id=row.get("karzar_id"),
                karzar_sku=row.get("karzar_sku"),
                karzar_name=row.get("karzar_name"),
                karzar_brand=row.get("karzar_brand"),
                source_price_toman=row.get("source_price_toman"),
                karzar_price_toman=row.get("karzar_price_toman"),
                source_availability=row.get("source_availability"),
                karzar_availability=row.get("karzar_availability"),
                review_reason=row.get("review_reason"),
                commerce_authority=str(row.get("commerce_authority") or ""),
                parse_flags=str(row.get("parse_flags") or ""),
            )
        )
    return out


def load_phase1_summary(phase1_dir: Path) -> dict[str, Any]:
    path = phase1_dir / "zcc_ir_summary.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_karzar_catalog(
    *,
    snapshot_path: str | None = None,
    read_db: bool = False,
) -> tuple[list[CurrentProduct], str, str]:
    products, kind, note = load_current_catalog(snapshot_path=snapshot_path, read_db=read_db)
    return products, kind, note


def export_products_json(path: Path, products: list[SourceProduct]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([p.as_dict() for p in products], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_products_csv(path: Path, products: list[SourceProduct]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRODUCT_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for product in products:
            writer.writerow(product_csv_row(product))
