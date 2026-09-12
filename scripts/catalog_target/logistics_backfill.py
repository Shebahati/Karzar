#!/usr/bin/env python3
"""Logistics backfill DESIGN pipeline — validate intake → authority artifact.

READ-ONLY toward production. Never writes Product / price / availability.
Never calls Postex. Never applies Alembic.

Input CSV/XLSX columns (aliases accepted; see catalog_target.logistics):
  sku, weight_grams, length_mm|package_length_cm, width_*, height_*,
  fragile|shipping_is_fragile, liquid|shipping_is_liquid,
  source, source_date [, product_id, shipping_class]

Output:
  validated logistics authority CSV + JSON summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.logistics import (  # noqa: E402
    read_csv_rows,
    summarize,
    validate_file_rows,
    write_authority_csv,
    write_json,
)


def _refuse_apply(flag: bool) -> None:
    if flag:
        raise SystemExit(
            "REFUSED: --apply is not implemented. Logistics APPLY requires a "
            "separate Owner-authorized Category B writer. This script only emits "
            "authority files."
        )


def _load_rows(path: Path) -> list[dict[str, object]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return list(read_csv_rows(path))  # type: ignore[arg-type]
    if suffix in {".xlsx", ".xlsm"}:
        from catalog_target.xlsx import iter_xlsx_rows

        rows = iter_xlsx_rows(path)
        return [{k: v for k, v in row.items() if k != "__source_row"} for row in rows]
    raise SystemExit(f"unsupported input type: {suffix}")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="CSV or XLSX logistics intake")
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory for authority CSV + summary JSON (local / gitignored OK)",
    )
    parser.add_argument(
        "--default-shipping-class",
        default=None,
        choices=["parcel", "freight_only"],
        help="Optional fill for blank shipping_class in intake only (omit to keep UNKNOWN)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="REFUSED — reserved for future Category B writer",
    )
    args = parser.parse_args(argv)
    _refuse_apply(args.apply)

    raw_rows = _load_rows(args.path)
    normalized: list[dict[str, object]] = []
    for row in raw_rows:
        item = dict(row)
        if args.default_shipping_class:
            class_val = str(item.get("shipping_class") or "").strip()
            if not class_val:
                item["shipping_class"] = args.default_shipping_class
        normalized.append(item)

    results = validate_file_rows(normalized)
    summary = summarize(results)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    authority_csv = args.out_dir / "logistics_authority.csv"
    summary_json = args.out_dir / "logistics_authority_summary.json"
    write_authority_csv(authority_csv, results)
    payload = {
        "input": str(args.path),
        "authority_csv": str(authority_csv),
        "summary": summary,
        "rows": [r.to_dict() for r in results],
        "safety": {
            "product_updates": 0,
            "price_updates": 0,
            "availability_updates": 0,
            "postex_api_calls": 0,
            "deploys": 0,
            "merges": 0,
            "apply_implemented": False,
        },
        "next_step": (
            "Owner review of logistics_authority.csv; separate Category B APPLY "
            "CLI required before any products UPDATE"
        ),
    }
    write_json(summary_json, payload)
    print(
        json.dumps(
            {
                "authority_csv": str(authority_csv),
                "summary": summary,
                "apply_implemented": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
