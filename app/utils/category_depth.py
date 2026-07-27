"""Compute depth, leaf status, and breadcrumbs for flat category lists."""

from collections import defaultdict
from typing import TypedDict

from app.db.models.product import Category

# Tree may be at most 3 layers. Products attach to leaf categories at depth 2 or 3
# (not L1 roots). Some merchandising branches (e.g. metrology after L2→L1 promote)
# are intentionally only two layers deep.
MAX_CATEGORY_DEPTH = 3
MIN_PRODUCT_CATEGORY_DEPTH = 2


class CategoryMeta(TypedDict):
    depth: int
    is_leaf: bool
    breadcrumb: list[str]
    ancestor_ids: list[int]


def build_category_metadata(categories: list[Category]) -> dict[int, CategoryMeta]:
    """Return per-category depth (1-based), leaf flag, breadcrumb names, and ancestor ids."""
    by_id = {category.id: category for category in categories}
    child_count: dict[int, int] = defaultdict(int)

    for category in categories:
        if category.parent_id is not None:
            child_count[category.parent_id] += 1

    metadata: dict[int, CategoryMeta] = {}

    for category in categories:
        chain: list[Category] = []
        current: Category | None = category
        while current is not None:
            chain.append(current)
            current = by_id.get(current.parent_id) if current.parent_id is not None else None

        ancestor_ids = [node.id for node in reversed(chain[:-1])]
        metadata[category.id] = CategoryMeta(
            depth=len(chain),
            is_leaf=child_count[category.id] == 0,
            breadcrumb=[node.name for node in reversed(chain)],
            ancestor_ids=ancestor_ids,
        )

    return metadata


def is_selectable_product_category(meta: CategoryMeta) -> bool:
    """Leaf categories at depth 2 or 3 may carry products (not L1 roots)."""
    return (
        meta["is_leaf"]
        and MIN_PRODUCT_CATEGORY_DEPTH <= meta["depth"] <= MAX_CATEGORY_DEPTH
    )
