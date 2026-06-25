"""Category business logic delegating to the CRUD and tree-builder layers."""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud import category as crud_category
from app.schemas.category import CategoryFlatResponse, CategoryTreeResponse
from app.utils.category_depth import build_category_metadata, is_selectable_product_category
from app.utils.category_tree import build_category_tree

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

    @staticmethod
    async def get_flat_categories(db: AsyncSession) -> List[CategoryFlatResponse]:
        categories = await crud_category.get_all_categories(db)
        metadata = build_category_metadata(categories)

        return [
            CategoryFlatResponse(
                id=category.id,
                name=category.name,
                parent_id=category.parent_id,
                depth=meta.depth,
                is_leaf=meta.is_leaf,
                is_selectable=is_selectable_product_category(meta),
                breadcrumb=meta.breadcrumb,
                ancestor_ids=meta.ancestor_ids,
            )
            for category in categories
            for meta in [metadata[category.id]]
        ]
