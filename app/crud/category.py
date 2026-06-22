# app/crud/category.py
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import Category
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_all_categories(db: AsyncSession) -> List[Category]:
    """Load every category in a single query for in-memory tree assembly."""
    stmt = select(Category).order_by(Category.name.asc(), Category.id.asc())
    result = await db.execute(stmt)
    categories = list(result.scalars().all())
    logger.info("Loaded %s categories for tree building", len(categories))
    return categories
