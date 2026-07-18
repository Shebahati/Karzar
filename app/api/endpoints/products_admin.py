"""Product admin write/stock endpoints."""

from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_super_admin,
    get_current_super_admin_with_step_up,
)
from app.api.endpoints.product_common import _product_detail_after_write
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.crud import product as crud_product
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.common import build_pagination_meta
from app.schemas.product import (
    BulkStockAdjustRequest,
    BulkStockAdjustResponse,
    ProductChangeLogEntry,
    ProductChangeLogListResponse,
    ProductCreate,
    ProductDetailResponse,
    ProductUpdate,
    StockStatusResponse,
)
from app.services.product_service import ProductService

logger = get_logger(__name__)

router = APIRouter()


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
        deleted = await ProductService.delete_product(
            db=db,
            product_id=product_id,
            actor_user_id=current_user.id,
        )
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
async def get_stock(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
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
            actor_user_id=current_user.id,
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


@router.post(
    "/bulk/stock-adjust",
    response_model=BulkStockAdjustResponse,
    summary="Bulk stock adjustment (admin)",
    tags=["Stock Management"],
)
async def bulk_adjust_stock(
    payload: BulkStockAdjustRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    items = [
        {
            "product_id": item.product_id,
            "quantity_delta": item.quantity_delta,
            "reason": item.reason,
        }
        for item in payload.items
    ]
    updated_ids = await ProductService.bulk_adjust_stock(
        db, items, actor_user_id=current_user.id
    )
    return BulkStockAdjustResponse(updated_product_ids=updated_ids)


@router.get(
    "/{product_id}/change-log",
    response_model=ProductChangeLogListResponse,
    summary="Product price/stock change history (admin)",
)
async def list_product_change_log(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    from app.crud import platform as crud_platform

    product = await crud_product.get_product_by_id(db, product_id)
    if not product:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )
    rows, total = await crud_platform.list_product_change_logs(
        db, product_id, skip=skip, limit=limit
    )
    return {
        "data": [ProductChangeLogEntry.model_validate(row, from_attributes=True) for row in rows],
        "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
    }
