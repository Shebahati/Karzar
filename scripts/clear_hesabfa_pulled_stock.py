#!/usr/bin/env python3
"""Zero leftover products.stock_quantity from older Hesabfa→site pulls.

Preserves ``is_available``. Site must not store warehouse counts.

Uses ``asyncpg`` (already in the API image). Accepts plain ``postgresql://``
or SQLAlchemy-style ``postgresql+asyncpg://`` URLs.

Usage (API container / venv with DATABASE_URL):

  python scripts/clear_hesabfa_pulled_stock.py --dry-run
  python scripts/clear_hesabfa_pulled_stock.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg


def _normalize_dsn(url: str) -> str:
    """Strip SQLAlchemy driver suffixes so asyncpg can connect."""
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix) :]
    return url


async def _run(database_url: str, dry_run: bool) -> int:
    conn = await asyncpg.connect(_normalize_dsn(database_url))
    try:
        pending = int(
            await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM products
                WHERE deleted_at IS NULL
                  AND COALESCE(stock_quantity, 0) <> 0
                """
            )
        )
        print(f"products with non-zero stock_quantity: {pending}")
        if dry_run or pending == 0:
            return 0
        status = await conn.execute(
            """
            UPDATE products
            SET stock_quantity = 0,
                updated_at = NOW()
            WHERE deleted_at IS NULL
              AND COALESCE(stock_quantity, 0) <> 0
            """
        )
        # asyncpg returns e.g. "UPDATE 4183"
        cleared = int(status.split()[-1]) if status.split()[-1].isdigit() else pending
        print(f"cleared stock_quantity on {cleared} products (is_available unchanged)")
        return 0
    finally:
        await conn.close()


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
    return asyncio.run(_run(args.database_url, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
