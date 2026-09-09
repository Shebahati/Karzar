#!/usr/bin/env python3
"""READ-ONLY exact mapper: supplier stock → catalog snapshot. No production mutation.

Does not invent activation candidates without a validated stock source.
Does not repair TERMA price exceptions from stock.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.supplier_stock import (  # noqa: E402
    CatalogProduct,
    FreshnessPolicy,
    activation_candidates_from_mapping,
    map_stock_to_catalog,
    validate_stock_source,
    write_json,
    write_mapping_csv,
)


def _load_catalog_csv(path: Path) -> list[CatalogProduct]:
    rows: list[CatalogProduct] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            brand = (r.get("brand") or r.get("brand_key") or r.get("brand_name") or "").strip()
            sku = (r.get("sku") or "").strip()
            if not sku:
                continue
            active = str(r.get("is_active", "")).lower() in {"1", "true", "t", "yes"}
            deleted = bool((r.get("deleted_at") or "").strip())
            rows.append(
                CatalogProduct(
                    product_id=str(r.get("product_id") or r.get("id") or ""),
                    brand=brand,
                    sku=sku,
                    model=str(r.get("model") or ""),
                    is_active=active,
                    deleted=deleted,
                )
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stock_path", type=Path)
    p.add_argument("--brand", required=True)
    p.add_argument("--catalog-csv", type=Path, required=True, help="Local catalog snapshot CSV")
    p.add_argument("--supplier", default="")
    p.add_argument("--source-date", default=None)
    p.add_argument("--allow-exact-model", action="store_true")
    p.add_argument("--no-dasqua-pack-a", action="store_true")
    p.add_argument("--quantity-is-sellable-stock", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--current-enough-days", type=int, default=14)
    p.add_argument("--aging-but-usable-days", type=int, default=45)
    p.add_argument("--mapping-out", type=Path, required=True)
    p.add_argument("--candidates-out", type=Path, default=None)
    p.add_argument("--report-out", type=Path, default=None)
    args = p.parse_args(argv)

    report = validate_stock_source(
        args.stock_path,
        brand=args.brand,
        supplier=args.supplier,
        authority_type="AVAILABILITY",
        quantity_is_sellable_stock=args.quantity_is_sellable_stock,
        source_date_override=args.source_date,
        freshness=FreshnessPolicy(
            current_enough_days=args.current_enough_days,
            aging_but_usable_days=args.aging_but_usable_days,
        ),
    )
    if not report.source_authority_valid:
        summary = {k: v for k, v in report.to_dict().items() if k != "rows"}
        print(json.dumps({"SOURCE_AUTHORITY_VALID": False, **summary}, ensure_ascii=False, indent=2))
        if args.report_out:
            write_json(args.report_out, report.to_dict())
        # Still write empty mapping outputs for determinism
        write_mapping_csv(args.mapping_out, [])
        if args.candidates_out:
            write_mapping_csv(args.candidates_out, [])
        return 2

    catalog = _load_catalog_csv(args.catalog_csv)
    mapped = map_stock_to_catalog(
        report,
        catalog,
        brand=args.brand,
        allow_exact_model=args.allow_exact_model,
        allow_dasqua_pack_a=not args.no_dasqua_pack_a,
    )
    write_mapping_csv(args.mapping_out, mapped)
    cands = activation_candidates_from_mapping(mapped)
    if args.candidates_out:
        write_mapping_csv(args.candidates_out, cands)
    out = {
        "SOURCE_AUTHORITY_VALID": True,
        "mapped_rows": len(mapped),
        "exact_match": sum(1 for m in mapped if m.match_class == "EXACT_MATCH"),
        "activation_candidates_stock_side": len(cands),
        "ACTIVATION_CANDIDATES_NOTE": "Stock-side only; merge independent price authority before sale-wave",
        "manifest": report.manifest.__dict__ if report.manifest else None,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.report_out:
        write_json(args.report_out, {"validation": report.to_dict(), "mapping_summary": out})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
