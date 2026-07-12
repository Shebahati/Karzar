"""Aggregate active product counts per category subtree."""

from collections import defaultdict
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.category import collect_category_subtree_ids
from app.db.models.product import Category, Product


async def get_direct_product_counts(db: AsyncSession) -> Dict[int, int]:
    stmt = (
        select(Product.category_id, func.count(Product.id))
        .where(Product.deleted_at.is_(None), Product.is_active.is_(True), Product.category_id.isnot(None))
        .group_by(Product.category_id)
    )
    rows = await db.execute(stmt)
    return {int(category_id): int(count) for category_id, count in rows.all()}


def compute_subtree_product_counts(
    categories: List[Category],
    direct_counts: Dict[int, int],
) -> Dict[int, int]:
    children_by_parent: dict[int, list[int]] = defaultdict(list)
    for category in categories:
        if category.parent_id is not None:
            children_by_parent[category.parent_id].append(category.id)

    memo: dict[int, int] = {}

    def subtree_total(category_id: int) -> int:
        if category_id in memo:
            return memo[category_id]
        total = direct_counts.get(category_id, 0)
        for child_id in children_by_parent.get(category_id, []):
            total += subtree_total(child_id)
        memo[category_id] = total
        return total

    return {category.id: subtree_total(category.id) for category in categories}


async def get_category_product_counts(db: AsyncSession, categories: List[Category]) -> Dict[int, int]:
    direct_counts = await get_direct_product_counts(db)
    return compute_subtree_product_counts(categories, direct_counts)
