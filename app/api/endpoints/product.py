# app/api/endpoints/product.py
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_service import ProductService
from app.db.database import get_db
from app.api.deps import get_current_super_admin
from app.db.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)
from app.crud import product as crud_product
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _stock_status(quantity) -> str:
    return "in_stock" if Decimal(str(quantity)) > Decimal("0.0") else "out_of_stock"


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_new_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        return await ProductService.create_product_with_validation(db=db, product_data=product_in)
    except ValueError as e:
        logger.warning(f"Business validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating product",
        )


@router.get(
    "/",
    response_model=ProductListResponse,
    summary="List all products",
)
async def read_products(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    brand_id: Optional[int] = Query(None, description="Filter by brand ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name, SKU, and brand"),
    min_price: Optional[Decimal] = Query(None, description="Minimum price filter"),
    max_price: Optional[Decimal] = Query(None, description="Maximum price filter"),
):
    try:
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
        )

        items = [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "base_price": p.base_price,
                "stock_status": _stock_status(p.stock_quantity),
            }
            for p in products
        ]

        return {
            "data": items,
            "meta": {
                "total_count": total,
                "skip": skip,
                "limit": limit,
                "has_next": (skip + limit) < total,
            },
        }
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving products",
        )


@router.get(
    "/sku/{sku}",
    response_model=ProductResponse,
    summary="Get product by SKU",
)
async def read_product_by_sku(
    sku: str = Path(..., min_length=1, max_length=50, description="Product SKU"),
    db: AsyncSession = Depends(get_db),
):
    try:
        product = await crud_product.get_product_by_sku(db=db, sku=sku.strip().upper())
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with SKU '{sku}' not found",
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product by SKU: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving product",
        )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    try:
        details = await ProductService.get_product_details(db=db, product_id=product_id)
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return details["product"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving product",
        )


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return product
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating product",
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product (soft delete)",
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        deleted = await ProductService.delete_product(db=db, product_id=product_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting product",
        )


@router.post(
    "/{product_id}/restore",
    response_model=ProductResponse,
    summary="Restore deleted product",
)
async def restore_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        product = await ProductService.restore_product(db=db, product_id=product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found or is not deleted",
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error restoring product",
        )


@router.get(
    "/{product_id}/stock",
    summary="Get product stock status",
    tags=["Stock Management"],
)
async def get_stock(product_id: int, db: AsyncSession = Depends(get_db)):
    try:
        stock_status = await crud_product.get_stock_status(db=db, product_id=product_id)
        if not stock_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return stock_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stock status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving stock status",
        )


@router.post(
    "/{product_id}/stock/adjust",
    response_model=ProductResponse,
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return product
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error adjusting stock: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adjusting stock",
        )
