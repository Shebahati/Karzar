"""Category depth, breadcrumb, and product-selection metadata helpers."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from app.db.models.product import Category


@dataclass(frozen=True)
class CategoryMeta:
    depth: int
    is_leaf: bool
    breadcrumb: List[str]
    ancestor_ids: List[int]


def build_category_metadata(categories: List[Category]) -> Dict[int, CategoryMeta]:
    """Compute depth, leaf status, breadcrumb, and ancestor ids for every category."""
    by_id = {category.id: category for category in categories}
    children_by_parent: Dict[int, List[int]] = defaultdict(list)

    for category in categories:
        if category.parent_id is not None and category.parent_id in by_id:
            children_by_parent[category.parent_id].append(category.id)

    is_leaf_map = {
        category.id: len(children_by_parent.get(category.id, [])) == 0 for category in categories
    }

    cache: Dict[int, CategoryMeta] = {}

    def resolve(category_id: int, visiting: Optional[Set[int]] = None) -> CategoryMeta:
        if category_id in cache:
            return cache[category_id]

        visiting = visiting or set()
        if category_id in visiting:
            raise ValueError(f"Category cycle detected at id={category_id}")
        visiting.add(category_id)

        category = by_id[category_id]
        is_leaf = is_leaf_map[category_id]

        if category.parent_id is None or category.parent_id not in by_id:
            meta = CategoryMeta(
                depth=1,
                is_leaf=is_leaf,
                breadcrumb=[category.name],
                ancestor_ids=[],
            )
        else:
            parent_meta = resolve(category.parent_id, visiting)
            meta = CategoryMeta(
                depth=parent_meta.depth + 1,
                is_leaf=is_leaf,
                breadcrumb=[*parent_meta.breadcrumb, category.name],
                ancestor_ids=[*parent_meta.ancestor_ids, category.parent_id],
            )

        cache[category_id] = meta
        return meta

    for category in categories:
        resolve(category.id)

    return cache


def is_selectable_product_category(meta: CategoryMeta) -> bool:
    """Layer-3 leaf categories are valid product assignment targets."""
    return meta.depth == 3 and meta.is_leaf
