# app/api/endpoints/product.py
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.product_service import ProductService
from app.db.database import get_db
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


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    tags=["Products"],
)
async def create_new_product(
    product_in: ProductCreate, db: AsyncSession = Depends(get_db)
):
    try:
        # کار را مستقیما به سرویس می‌سپاریم
        product = await ProductService.create_product_with_validation(db=db, product_data=product_in)
        return product
    
    except ValueError as e:
        # سرویس در صورت وجود خطای بیزینسی (مثل SKU تکراری) ValueError می‌دهد
        logger.warning(f"Business validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
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
    tags=["Products"],
)
async def read_products(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    category_slug: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name, SKU, and brand"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
):
    try:
        # ارسال تمام درخواست‌ها به لایه Service
        products, total = await ProductService.search_products(
            db=db,
            skip=skip,
            limit=limit,
            category=category_slug,
            brand=brand,
            is_active=is_active,
            search=search,
            min_price=min_price,
            max_price=max_price
        )
        return ProductListResponse(
            total=total, skip=skip, limit=limit, items=products
        )
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
    tags=["Products"],
)
async def read_product_by_sku(
    sku: str = Path(..., min_length=1, max_length=50, description="Product SKU"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific product by SKU."""
    try:
        product = await crud_product.get_product_by_sku(db=db, sku=sku)
        if not product:
            logger.warning(f"Product not found with SKU: {sku}")
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
    tags=["Products"],
)
async def read_product(
    product_id: UUID, db: AsyncSession = Depends(get_db)
):
    """Get a specific product by ID."""
    try:
        # ارسال درخواست گرفتن محصول به لایه Service
        details = await ProductService.get_product_details(db=db, product_id=product_id)
        
        # اگر سرویس دیتایی پیدا نکرد، ارور 404 بده
        if not details:
            logger.warning(f"Product not found: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
            
        # دیتای تایید شده را برگردان
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
    summary="Update product (full)",
    tags=["Products"],
)
async def update_product(
    product_id: UUID,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        product = await ProductService.update_product_with_validation(
            db=db, product_id=product_id, update_data=product_in
        )
        if not product:
            logger.warning(f"Product not found for update: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return product
    except HTTPException:
        raise  # <--- این همان خط مهمی است که جا افتاده بود!
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
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
    tags=["Products"],
)
async def delete_product(
    product_id: UUID, db: AsyncSession = Depends(get_db)
):
    try:
        success = await crud_product.delete_product_soft(db=db, product_id=product_id)
        if not success:
            logger.warning(f"Product not found for deletion: {product_id}")
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
    tags=["Products"],
)
async def restore_product(
    product_id: UUID, db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted product."""
    try:
        product = await crud_product.restore_product(db=db, product_id=product_id)
        if not product:
            logger.warning(f"Product not found for restore: {product_id}")
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
async def get_stock(
    product_id: UUID, db: AsyncSession = Depends(get_db)
):
    """Get stock status for a product."""
    try:
        stock_status = await crud_product.get_stock_status(db=db, product_id=product_id)
        if not stock_status:
            logger.warning(f"Product not found for stock check: {product_id}")
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
    product_id: UUID,
    quantity_delta: int = Query(..., description="Quantity to add or subtract"),
    db: AsyncSession = Depends(get_db),
):
    try:
        product = await ProductService.adjust_stock_with_validation(
            db=db, product_id=product_id, quantity_delta=quantity_delta, reason="API Adjustment"
        )
        if not product:
            logger.warning(f"Product not found for stock adjustment: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return product
    except HTTPException:
        raise  # <--- اینجا هم اضافه شد
    except ValueError as e:
        logger.warning(f"Validation error in stock adjustment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error adjusting stock: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adjusting stock",
        )
