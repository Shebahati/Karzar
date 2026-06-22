# app/api/endpoints/category.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models.product import Category
from app.schemas.category import CategoryTreeListResponse
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/tree",
    response_model=CategoryTreeListResponse,
    summary="Get Category Tree for Mega-Menu",
    tags=["Categories"],
)
async def get_category_tree(db: AsyncSession = Depends(get_db)):
    try:
        stmt = (
            select(Category)
            .where(Category.parent_id.is_(None))
            .options(
                selectinload(Category.subcategories).selectinload(Category.subcategories)
            )
        )
        result = await db.execute(stmt)
        categories = result.scalars().all()
        return {"data": categories}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching category tree: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving categories",
        ) from e
