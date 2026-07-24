"""Category endpoints for tree navigation, admin CRUD, and product entry templates."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin, get_current_super_admin_with_step_up
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryDeleteResponse,
    CategoryFlatResponse,
    CategoryListResponse,
    CategorySpecFilterOptionsResponse,
    CategorySpecLabelsResponse,
    CategorySpecTemplateResponse,
    CategoryTreeResponse,
    CategoryUpdate,
)
from app.services.category_service import CategoryService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=CategoryListResponse,
    summary="List all categories (flat, with depth metadata)",
    tags=["Categories"],
)
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Return every category with depth, leaf flag, and breadcrumb for admin filtering."""
    try:
        data = await CategoryService.get_flat_categories(db)
        return {"data": data}
    except Exception as exc:
        logger.error("Error listing categories: %s", exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving categories",
        ) from exc


@router.get(
    "/slug/{slug}",
    response_model=CategoryFlatResponse,
    summary="Get category by slug",
    tags=["Categories"],
)
async def get_category_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    categories = await CategoryService.get_flat_categories(db)
    normalized = slug.strip()
    for category in categories:
        if category.slug == normalized:
            return category
    raise api_error(
        status.HTTP_404_NOT_FOUND,
        error_code=ErrorCode.NOT_FOUND,
        message=f"Category '{slug}' not found",
    )


@router.post(
    "/",
    response_model=CategoryFlatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    tags=["Categories"],
)
async def create_category(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    try:
        return await CategoryService.create_category(db, payload)
    except HTTPException:
        raise
    except ValueError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Error creating category: %s", exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error creating category",
        ) from exc


@router.put(
    "/{category_id}",
    response_model=CategoryFlatResponse,
    summary="Update a category",
    tags=["Categories"],
)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    try:
        return await CategoryService.update_category(db, category_id, payload)
    except HTTPException:
        raise
    except ValueError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Error updating category %s: %s", category_id, exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error updating category",
        ) from exc


@router.delete(
    "/{category_id}",
    response_model=CategoryDeleteResponse,
    summary="Delete a category with product reassignment",
    tags=["Categories"],
)
async def delete_category(
    category_id: int,
    target_category_id: int | None = Query(
        None,
        description="Selectable depth-3 leaf to receive products when the category is non-empty",
    ),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin_with_step_up),
):
    """Delete a leaf category; products must move to another selectable leaf (requires step-up PIN)."""
    try:
        return await CategoryService.delete_category_with_reassignment(
            db, category_id, target_category_id=target_category_id
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting category %s: %s", category_id, exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error deleting category",
        ) from exc


@router.get(
    "/tree",
    response_model=list[CategoryTreeResponse],
    summary="Get Category Tree for Mega-Menu",
    tags=["Categories"],
)
async def get_category_tree(db: AsyncSession = Depends(get_db)):
    """Return the category hierarchy as a nested tree (max 3 product-assignable layers)."""
    try:
        tree = await CategoryService.get_category_tree(db)
        return tree
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


@router.get(
    "/spec-labels",
    response_model=CategorySpecLabelsResponse,
    summary="Public feature key to Persian label map (storefront)",
    tags=["Categories"],
)
async def get_storefront_spec_labels():
    """Cacheable mapping for storefront specification labels."""
    return CategoryService.get_storefront_spec_labels()


@router.get(
    "/{category_id}/spec-filter-options",
    response_model=CategorySpecFilterOptionsResponse,
    summary="Available technical specification filter values for a category",
    tags=["Categories"],
)
async def get_category_spec_filter_options(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.get_spec_filter_options(db, category_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving specification filter options",
        ) from exc


@router.get(
    "/{category_id}/spec-templates",
    response_model=CategorySpecTemplateResponse,
    summary="Get specification template for an assignable leaf category",
    tags=["Categories"],
)
async def get_category_spec_template(category_id: int, db: AsyncSession = Depends(get_db)):
    """Return the 3-part JSONB template (tech specs, features, dimensions) for product entry."""
    try:
        return await CategoryService.get_spec_template(db, category_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving specification template",
        ) from exc
