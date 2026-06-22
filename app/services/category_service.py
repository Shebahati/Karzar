# app/services/category_service.py
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import category as crud_category
from app.schemas.category import CategoryTreeResponse
from app.utils.category_tree import build_category_tree
from app.core.logging import get_logger

logger = get_logger(__name__)


class CategoryService:
    @staticmethod
    async def get_category_tree(db: AsyncSession) -> List[CategoryTreeResponse]:
        categories = await crud_category.get_all_categories(db)
        try:
            return build_category_tree(categories)
        except ValueError as exc:
            logger.error("Invalid category hierarchy: %s", exc)
            raise
