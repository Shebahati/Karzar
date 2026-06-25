"""Category tree and flat-list endpoints for frontend navigation and admin forms."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.db.database import get_db
from app.schemas.category import CategoryListResponse, CategoryTreeListResponse
from app.services.category_service import CategoryService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=CategoryListResponse,
    summary="List all categories with metadata",
    tags=["Categories"],
)
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Return a flat category list with depth, breadcrumb, and selectability metadata."""
    try:
        categories = await CategoryService.get_flat_categories(db)
        return {"data": categories}
    except ValueError as exc:
        logger.error("Category metadata build failed: %s", exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Invalid category hierarchy",
        ) from exc
    except Exception as exc:
        logger.error("Error fetching categories: %s", exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving categories",
        ) from exc


@router.get(
    "/tree",
    response_model=CategoryTreeListResponse,
    summary="Get Category Tree for Mega-Menu",
    tags=["Categories"],
)
async def get_category_tree(db: AsyncSession = Depends(get_db)):
    """Return the full category hierarchy as a nested tree of arbitrary depth."""
    try:
        tree = await CategoryService.get_category_tree(db)
        return {"data": tree}
    except ValueError as exc:
        logger.error("Category tree build failed: %s", exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Invalid category hierarchy",
        ) from exc
    except Exception as exc:
        logger.error("Error fetching category tree: %s", exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving categories",
        ) from exc
