"""Dry-run / apply taxonomy migration toward TARGET_TAXONOMY.md.

Usage:
  python scripts/catalog_taxonomy_migrate.py --dry-run
  python scripts/catalog_taxonomy_migrate.py --apply

Writes unresolved rows to work/reports/catalog-taxonomy-unresolved.csv.
Does not delete products or hide ambiguous items.

In Docker, run as the host user if the bind mount is not writable by the
container default user, e.g.:
  docker compose exec -T -u "$(id -u):$(id -g)" app python3 scripts/catalog_taxonomy_migrate.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import category as crud_category
from app.db.database import async_session_maker
from app.db.models.product import Category, Product
from app.utils.slugify import ensure_unique_slug

REPORT_PATH = Path("work/reports/catalog-taxonomy-unresolved.csv")

# Minimal high-confidence alias map (extend iteratively; ambiguous items go to CSV).
CATEGORY_ALIASES: dict[str, str] = {
    "اندازه‌گیری": "اندازه‌گیری",
    "اندازه گیری": "اندازه‌گیری",
    "اینسرت": "اینسرت تراش",
    "ابزار اینسرتی": "هلدر و ابزار اینسرتی تراش",
    "ابزار گیرشی": "سه‌نظام و چهار‌نظام",
    "ابزارگیر": "ابزارگیر فرز CNC",
    "دستگاه‌های صنعتی": "دستگاه‌های صنعتی",
    "مته": "مته HSS",
    "مته‌ها": "مته HSS",
    "قلاویز": "قلاویز دستی",
    "فرز انگشتی": "فرز انگشتی کارباید",
}


async def _find_or_create_category(
    db: AsyncSession,
    *,
    name: str,
    parent_id: int | None,
    cache: dict[tuple[int | None, str], Category],
) -> Category:
    key = (parent_id, name)
    if key in cache:
        return cache[key]
    stmt = select(Category).where(Category.name == name, Category.parent_id == parent_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        cache[key] = existing
        return existing
    slug = await ensure_unique_slug(
        name,
        exists=lambda candidate: db.execute(
            select(Category.id).where(Category.slug == candidate)
        ),
        fallback_prefix=name[:20],
        max_length=200,
    )
    category = Category(name=name, slug=slug, parent_id=parent_id)
    db.add(category)
    await db.flush()
    cache[key] = category
    return category


async def migrate(*, apply: bool) -> int:
    unresolved: list[dict[str, str]] = []
    async with async_session_maker() as db:
        categories = await crud_category.get_all_categories(db)
        by_name = {c.name: c for c in categories}
        cache: dict[tuple[int | None, str], Category] = {}

        products = list((await db.execute(select(Product).where(Product.deleted_at.is_(None)))).scalars())
        for product in products:
            if not product.category_id:
                unresolved.append(
                    {
                        "product_id": str(product.id),
                        "title": product.name,
                        "old_category": "",
                        "proposed_candidates": "",
                        "reason": "missing_category",
                    }
                )
                continue
            old = next((c for c in categories if c.id == product.category_id), None)
            old_name = old.name if old else ""
            target_name = CATEGORY_ALIASES.get(old_name)
            if not target_name:
                unresolved.append(
                    {
                        "product_id": str(product.id),
                        "title": product.name,
                        "old_category": old_name,
                        "proposed_candidates": "",
                        "reason": "no_alias_mapping",
                    }
                )
                continue
            if apply:
                target = await _find_or_create_category(db, name=target_name, parent_id=None, cache=cache)
                product.category_id = target.id

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with REPORT_PATH.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["product_id", "title", "old_category", "proposed_candidates", "reason"],
            )
            writer.writeheader()
            writer.writerows(unresolved)

        if apply:
            await db.commit()
        else:
            await db.rollback()
    return len(unresolved)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    apply = bool(args.apply)
    count = asyncio.run(migrate(apply=apply))
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[{mode}] unresolved={count} report={REPORT_PATH}")


if __name__ == "__main__":
    main()
