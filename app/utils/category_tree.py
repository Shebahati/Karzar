from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set

from app.db.models.product import Category
from app.schemas.category import CategoryTreeResponse


def _sort_categories(categories: Iterable[Category]) -> List[Category]:
    return sorted(categories, key=lambda category: (category.name.casefold(), category.id))


def _build_children_map(
    categories: List[Category],
    known_ids: Set[int],
) -> Dict[Optional[int], List[Category]]:
    children_by_parent: Dict[Optional[int], List[Category]] = defaultdict(list)

    for category in categories:
        parent_id = category.parent_id
        if parent_id is None or parent_id not in known_ids:
            children_by_parent[None].append(category)
        else:
            children_by_parent[parent_id].append(category)

    for parent_id in children_by_parent:
        children_by_parent[parent_id] = _sort_categories(children_by_parent[parent_id])

    return children_by_parent


def _detect_cycles(
    categories: List[Category],
    children_by_parent: Dict[Optional[int], List[Category]],
) -> None:
    white, gray, black = 0, 1, 2
    state: Dict[int, int] = {category.id: white for category in categories}

    def visit(category_id: int) -> None:
        if state[category_id] == gray:
            raise ValueError(f"Category cycle detected at id={category_id}")
        if state[category_id] == black:
            return

        state[category_id] = gray
        for child in children_by_parent.get(category_id, []):
            visit(child.id)
        state[category_id] = black

    for category in categories:
        if state[category.id] == white:
            visit(category.id)


def build_category_tree(categories: List[Category]) -> List[CategoryTreeResponse]:
    """Build a nested category tree of arbitrary depth from a flat list.

    Uses one DB round-trip worth of data and assembles the tree in memory so
    depth is not limited by ORM eager-load chains.
    """
    if not categories:
        return []

    known_ids = {category.id for category in categories}
    children_by_parent = _build_children_map(categories, known_ids)
    _detect_cycles(categories, children_by_parent)

    def to_node(category: Category) -> CategoryTreeResponse:
        children = children_by_parent.get(category.id, [])
        return CategoryTreeResponse(
            id=category.id,
            name=category.name,
            parent_id=category.parent_id,
            subcategories=[to_node(child) for child in children],
        )

    roots = children_by_parent.get(None, [])
    return [to_node(root) for root in roots]
