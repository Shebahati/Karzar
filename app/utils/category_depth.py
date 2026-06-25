"""Compute depth, leaf status, and breadcrumbs for flat category lists."""

from collections import defaultdict
from typing import Dict, List, Optional, TypedDict

from app.db.models.product import Category


class CategoryMeta(TypedDict):
    depth: int
    is_leaf: bool
    breadcrumb: List[str]
    ancestor_ids: List[int]


def build_category_metadata(categories: List[Category]) -> Dict[int, CategoryMeta]:
    """Return per-category depth (1-based), leaf flag, breadcrumb names, and ancestor ids."""
    by_id = {category.id: category for category in categories}
    child_count: dict[int, int] = defaultdict(int)

    for category in categories:
        if category.parent_id is not None:
            child_count[category.parent_id] += 1

    metadata: Dict[int, CategoryMeta] = {}

    for category in categories:
        chain: List[Category] = []
        current: Optional[Category] = category
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
    """Leaf categories below the root (depth >= 2).

    Supports both three-level mega-menu branches and shorter two-level branches
    where product types sit directly under a root category.
    """
    return meta["is_leaf"] and meta["depth"] >= 2
