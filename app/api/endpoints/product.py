"""Product CRUD, search, stock management, and statistics endpoints."""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_service import ProductService
from app.db.database import get_db
from app.api.deps import get_current_super_admin, get_current_super_admin_with_step_up
from app.db.models.user import User
from app.schemas.common import build_pagination_meta
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductListResponse,
    ProductDetailResponse,
    StockStatusResponse,
)
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.utils.jsonb_filters import merge_spec_filters
from app.utils.product_presenter import to_product_detail, to_product_summary

logger = get_logger(__name__)

router = APIRouter()


async def _product_detail_after_write(db: AsyncSession, product_id: int) -> ProductDetailResponse:
    """Re-fetch a product with relationships after a write operation."""
    details = await ProductService.get_product_details(db=db, product_id=product_id)
    if not details:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )
    return to_product_detail(details["product"])


@router.post(
    "/",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_new_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        product = await ProductService.create_product_with_validation(db=db, product_data=product_in)
        return await _product_detail_after_write(db, product.id)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Business validation error: {str(e)}")
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=str(e),
            details=[{"field": "sku", "message": str(e)}],
        ) from e
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error creating product",
        ) from e


@router.get(
    "/",
    response_model=ProductListResponse,
    summary="List all products",
)
async def read_products(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    brand_id: Optional[int] = Query(None, description="Filter by brand ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name, SKU, and brand"),
    min_price: Optional[Decimal] = Query(None, description="Minimum price filter"),
    max_price: Optional[Decimal] = Query(None, description="Maximum price filter"),
    filters: Optional[str] = Query(
        None,
        description='JSON object for specification filters, e.g. {"technical_specs.range":"0-150mm"}',
    ),
):
    try:
        spec_filters = merge_spec_filters(filters_json=filters, request=request)
        products, total = await ProductService.search_products(
            db=db,
            skip=skip,
            limit=limit,
            category_id=category_id,
            brand_id=brand_id,
            is_active=is_active,
            search=search,
            min_price=min_price,
            max_price=max_price,
            spec_filters=spec_filters or None,
        )

        return {
            "data": [to_product_summary(product) for product in products],
            "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(e),
            details=[{"field": "filters", "message": str(e)}],
        ) from e
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving products",
        ) from e


@router.get(
    "/sku/{sku}",
    response_model=ProductDetailResponse,
    summary="Get product by SKU",
)
async def read_product_by_sku(
    sku: str = Path(..., min_length=1, max_length=50, description="Product SKU"),
    db: AsyncSession = Depends(get_db),
):
    from app.crud import product as crud_product

    try:
        product = await crud_product.get_product_by_sku(db=db, sku=sku.strip().upper())
        if not product:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with SKU '{sku}' not found",
            )
        return to_product_detail(product)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product by SKU: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving product",
        ) from e


@router.get(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get product by ID",
)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    try:
        details = await ProductService.get_product_details(db=db, product_id=product_id)
        if not details:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
        return to_product_detail(details["product"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving product",
        ) from e


@router.put(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Update product",
)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        product = await ProductService.update_product_with_validation(
            db=db, product_id=product_id, update_data=product_in
        )
        if not product:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
        return await _product_detail_after_write(db, product_id)
    except HTTPException:
        raise
    except ValueError as e:
        message = str(e)
        if "SKU" in message and "already exists" in message:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message=message,
                details=[{"field": "sku", "message": message}],
            ) from e
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message=message,
        ) from e
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error updating product",
        ) from e


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product (soft delete)",
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_with_step_up),
):
    try:
        deleted = await ProductService.delete_product(db=db, product_id=product_id)
        if not deleted:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error deleting product",
        ) from e


@router.post(
    "/{product_id}/restore",
    response_model=ProductDetailResponse,
    summary="Restore deleted product",
)
async def restore_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_with_step_up),
):
    try:
        product = await ProductService.restore_product(db=db, product_id=product_id)
        if not product:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found or is not deleted",
            )
        return await _product_detail_after_write(db, product_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error restoring product",
        ) from e


@router.get(
    "/{product_id}/stock",
    response_model=StockStatusResponse,
    summary="Get product stock status",
    tags=["Stock Management"],
)
async def get_stock(product_id: int, db: AsyncSession = Depends(get_db)):
    from app.crud import product as crud_product

    try:
        stock_status = await crud_product.get_stock_status(db=db, product_id=product_id)
        if not stock_status:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
        return stock_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stock status: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving stock status",
        ) from e


@router.post(
    "/{product_id}/stock/adjust",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Adjust product stock",
    tags=["Stock Management"],
)
async def adjust_stock(
    product_id: int,
    quantity_delta: Decimal = Query(..., description="Quantity to add or subtract"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        product = await ProductService.adjust_stock_with_validation(
            db=db,
            product_id=product_id,
            quantity_delta=quantity_delta,
            reason="API Adjustment",
        )
        if not product:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
        return await _product_detail_after_write(db, product_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error adjusting stock: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error adjusting stock",
        ) from e
