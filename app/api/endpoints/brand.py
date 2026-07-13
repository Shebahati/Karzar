"""Brand CRUD endpoints for admin panel and storefront filters."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin, get_current_super_admin_with_step_up
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.crud import brand as crud_brand
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.brand import BrandCreate, BrandListResponse, BrandResponse, BrandUpdate
from app.services.brand_service import BrandService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=BrandListResponse,
    summary="List all brands",
    tags=["Brands"],
)
async def list_brands(db: AsyncSession = Depends(get_db)):
    """Return all brands ordered by name (used by admin product forms)."""
    try:
        brands = await BrandService.list_brands(db)
        return {"data": brands}
    except Exception as exc:
        logger.error("Error listing brands: %s", exc)
        raise api_error(
            500,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving brands",
        ) from exc


@router.get(
    "/slug/{slug}",
    response_model=BrandResponse,
    summary="Get brand by slug",
    tags=["Brands"],
)
async def get_brand_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    brand = await crud_brand.get_brand_by_slug(db, slug.strip())
    if brand is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Brand '{slug}' not found",
        )
    return BrandResponse(
        id=brand.id,
        name=brand.name,
        slug=brand.slug,
        country=brand.country,
        product_count=await crud_brand.count_products_for_brand(db, brand.id),
    )


@router.post(
    "/",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a brand",
    tags=["Brands"],
)
async def create_brand(
    payload: BrandCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    try:
        return await BrandService.create_brand(db, payload)
    except HTTPException:
        raise
    except ValueError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Error creating brand: %s", exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error creating brand",
        ) from exc


@router.put(
    "/{brand_id}",
    response_model=BrandResponse,
    summary="Update a brand",
    tags=["Brands"],
)
async def update_brand(
    brand_id: int,
    payload: BrandUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    try:
        return await BrandService.update_brand(db, brand_id, payload)
    except HTTPException:
        raise
    except ValueError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Error updating brand %s: %s", brand_id, exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error updating brand",
        ) from exc


@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a brand",
    tags=["Brands"],
)
async def delete_brand(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin_with_step_up),
):
    try:
        return await BrandService.delete_brand(db, brand_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting brand %s: %s", brand_id, exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error deleting brand",
        ) from exc
