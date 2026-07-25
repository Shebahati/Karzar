#!/usr/bin/env python3
"""Zero leftover products.stock_quantity from older Hesabfa→site pulls.

Preserves ``is_available``. Site must not store warehouse counts.

Usage (API container / venv with DATABASE_URL):

  python scripts/clear_hesabfa_pulled_stock.py --dry-run
  python scripts/clear_hesabfa_pulled_stock.py
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count rows that would be cleared without updating",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="Postgres URL (default: DATABASE_URL env)",
    )
    args = parser.parse_args()
    if not args.database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM products
                WHERE deleted_at IS NULL
                  AND COALESCE(stock_quantity, 0) <> 0
                """
            )
            pending = int(cur.fetchone()[0])
            print(f"products with non-zero stock_quantity: {pending}")
            if args.dry_run or pending == 0:
                return 0
            cur.execute(
                """
                UPDATE products
                SET stock_quantity = 0,
                    updated_at = NOW()
                WHERE deleted_at IS NULL
                  AND COALESCE(stock_quantity, 0) <> 0
                """
            )
            print(f"cleared stock_quantity on {cur.rowcount} products (is_available unchanged)")
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
