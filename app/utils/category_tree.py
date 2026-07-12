"""Build nested category trees from a flat list of ORM rows."""

from collections import defaultdict
from collections.abc import Iterable

from app.db.models.product import Category
from app.schemas.category import CategoryTreeResponse
from app.utils.category_icons import resolve_category_icon


def _sort_categories(categories: Iterable[Category]) -> list[Category]:
    return sorted(categories, key=lambda category: (category.name.casefold(), category.id))


def _build_children_map(
    categories: list[Category],
    known_ids: set[int],
) -> dict[int | None, list[Category]]:
    """Group categories by parent_id; orphan unknown parents become roots."""
    children_by_parent: dict[int | None, list[Category]] = defaultdict(list)

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
    categories: list[Category],
    children_by_parent: dict[int | None, list[Category]],
) -> None:
    """DFS cycle detection using white/gray/black coloring."""
    white, gray, black = 0, 1, 2
    state: dict[int, int] = {category.id: white for category in categories}

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


def build_category_tree(
    categories: list[Category],
    *,
    product_counts: dict[int, int] | None = None,
) -> list[CategoryTreeResponse]:
    """Assemble a nested tree from a single flat query result."""
    if not categories:
        return []

    counts = product_counts or {}
    known_ids = {category.id for category in categories}
    children_by_parent = _build_children_map(categories, known_ids)
    _detect_cycles(categories, children_by_parent)

    def to_node(category: Category) -> CategoryTreeResponse:
        children = children_by_parent.get(category.id, [])
        is_root = category.parent_id is None
        return CategoryTreeResponse(
            id=category.id,
            name=category.name,
            parent_id=category.parent_id,
            icon=resolve_category_icon(category.name, category.icon, is_root=is_root),
            product_count=counts.get(category.id),
            subcategories=[to_node(child) for child in children],
        )

    roots = children_by_parent.get(None, [])
    return [to_node(root) for root in roots]
