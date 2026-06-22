# app/api/endpoints/category.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.db.models.product import Category
from app.schemas.category import CategoryTreeResponse
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get(
    "/tree",
    response_model=List[CategoryTreeResponse],
    summary="Get Category Tree for Mega-Menu",
    tags=["Categories"],
)
async def get_category_tree(db: AsyncSession = Depends(get_db)):
    try:
        # فقط دسته‌بندی‌های مادر (parent_id = null) را می‌گیریم
        # و زیردسته‌ها را تا ۲ لایه (برای مگامنو) به صورت اتوماتیک لود می‌کنیم
        stmt = (
            select(Category)
            .where(Category.parent_id.is_(None))
            .options(
                selectinload(Category.subcategories)
                .selectinload(Category.subcategories)
            )
        )
        result = await db.execute(stmt)
        categories = result.scalars().all()
        return categories
        
    except Exception as e:
        logger.error(f"Error fetching category tree: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving categories",
        )