"""Category database access for tree assembly and admin CRUD."""

from collections import defaultdict

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.product import Category, Product

logger = get_logger(__name__)


def collect_category_subtree_ids(
    categories: list[Category],
    category_id: int,
) -> list[int]:
    """Return category_id and all descendant ids for PLP subtree filtering."""
    children_by_parent: dict[int, list[int]] = defaultdict(list)
    known_ids = {category.id for category in categories}
    if category_id not in known_ids:
        return []

    for category in categories:
        if category.parent_id is not None:
            children_by_parent[category.parent_id].append(category.id)

    subtree_ids = [category_id]
    stack = [category_id]
    while stack:
        current = stack.pop()
        for child_id in children_by_parent.get(current, []):
            subtree_ids.append(child_id)
            stack.append(child_id)
    return subtree_ids


async def get_all_categories(db: AsyncSession) -> list[Category]:
    """Load every category row in one query for in-memory tree building."""
    stmt = select(Category).order_by(Category.name.asc(), Category.id.asc())
    result = await db.execute(stmt)
    categories = list(result.scalars().all())
    logger.info("Loaded %s categories for tree building", len(categories))
    return categories


async def get_category_by_id(db: AsyncSession, category_id: int) -> Category | None:
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def get_category_by_parent_and_name(
    db: AsyncSession,
    *,
    name: str,
    parent_id: int | None,
) -> Category | None:
    stmt = select(Category).where(Category.name == name)
    if parent_id is None:
        stmt = stmt.where(Category.parent_id.is_(None))
    else:
        stmt = stmt.where(Category.parent_id == parent_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_category_subtree_ids(db: AsyncSession, category_id: int) -> list[int]:
    categories = await get_all_categories(db)
    return collect_category_subtree_ids(categories, category_id)


async def count_subcategories(db: AsyncSession, category_id: int) -> int:
    result = await db.scalar(
        select(func.count()).select_from(Category).where(Category.parent_id == category_id)
    )
    return int(result or 0)


async def create_category(
    db: AsyncSession,
    *,
    name: str,
    parent_id: int | None,
    spec_template_key: str | None = None,
) -> Category:
    category = Category(
        name=name,
        parent_id=parent_id,
        spec_template_key=spec_template_key,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession,
    category: Category,
    *,
    name: str | None = None,
    parent_id: int | None = None,
    unset_parent: bool = False,
) -> Category:
    if name is not None:
        category.name = name
    if unset_parent:
        category.parent_id = None
    elif parent_id is not None:
        category.parent_id = parent_id
    await db.flush()
    await db.refresh(category)
    return category


async def reassign_products_category(
    db: AsyncSession,
    from_category_id: int,
    to_category_id: int | None,
) -> int:
    """Move products from one category to another (or uncategorized). Returns affected row count."""
    stmt = (
        update(Product)
        .where(Product.category_id == from_category_id, Product.deleted_at.is_(None))
        .values(category_id=to_category_id)
    )
    result = await db.execute(stmt)
    return int(result.rowcount or 0)


async def delete_category_row(db: AsyncSession, category: Category) -> None:
    await db.delete(category)
    await db.flush()
