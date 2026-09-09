#!/usr/bin/env python3
"""READ-ONLY supplier stock source validator (default deny). No production mutation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.supplier_stock import (  # noqa: E402
    FreshnessPolicy,
    validate_stock_source,
    write_json,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="CSV or XLSX stock file")
    p.add_argument("--brand", default=None, help="Expected brand key (DASQUA, TERMA, …)")
    p.add_argument("--supplier", default="", help="Supplier name for manifest")
    p.add_argument(
        "--authority-type",
        default="AVAILABILITY",
        choices=["PRICE", "AVAILABILITY", "PRICE_AND_AVAILABILITY"],
    )
    p.add_argument(
        "--quantity-is-sellable-stock",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When true, quantity>0/0 drives AVAILABLE/UNAVAILABLE",
    )
    p.add_argument("--source-date", default=None, help="Override/establish source date (YYYY-MM-DD)")
    p.add_argument("--current-enough-days", type=int, default=14)
    p.add_argument("--aging-but-usable-days", type=int, default=45)
    p.add_argument("--json-out", type=Path, default=None)
    args = p.parse_args(argv)

    report = validate_stock_source(
        args.path,
        brand=args.brand,
        supplier=args.supplier,
        authority_type=args.authority_type,
        quantity_is_sellable_stock=args.quantity_is_sellable_stock,
        source_date_override=args.source_date,
        freshness=FreshnessPolicy(
            current_enough_days=args.current_enough_days,
            aging_but_usable_days=args.aging_but_usable_days,
        ),
    )
    payload = report.to_dict()
    # Drop bulky row bodies from stdout summary unless writing json
    summary = {k: v for k, v in payload.items() if k != "rows"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.json_out:
        write_json(args.json_out, payload)
    return 0 if report.source_authority_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
