"""Category database access for tree assembly and admin CRUD."""

from typing import List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.product import Category, Product

logger = get_logger(__name__)


async def get_all_categories(db: AsyncSession) -> List[Category]:
    """Load every category row in one query for in-memory tree building."""
    stmt = select(Category).order_by(Category.name.asc(), Category.id.asc())
    result = await db.execute(stmt)
    categories = list(result.scalars().all())
    logger.info("Loaded %s categories for tree building", len(categories))
    return categories


async def get_category_by_id(db: AsyncSession, category_id: int) -> Optional[Category]:
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def count_subcategories(db: AsyncSession, category_id: int) -> int:
    result = await db.scalar(
        select(func.count()).select_from(Category).where(Category.parent_id == category_id)
    )
    return int(result or 0)


async def create_category(db: AsyncSession, *, name: str, parent_id: Optional[int]) -> Category:
    category = Category(name=name, parent_id=parent_id)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession,
    category: Category,
    *,
    name: Optional[str] = None,
    parent_id: Optional[int] = None,
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
    to_category_id: Optional[int],
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
