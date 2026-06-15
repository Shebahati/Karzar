# app/api/endpoints/product.py
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    """
    Create a new product.
    
    - **sku**: Unique product identifier (max 50 chars)
    - **name**: Product name (max 255 chars)
    - **category_slug**: Product category
    - **brand**: Product brand (max 100 chars)
    - **base_price**: Product price (must be >= 0)
    - **stock_quantity**: Available stock (must be >= 0)
    - **specifications**: Product specifications (technical, features, dimensions)
    """
    try:
        # Check if SKU already exists
        existing = await crud_product.get_product_by_sku(db, product_in.sku)
        if existing:
            logger.warning(f"Attempted to create product with duplicate SKU: {product_in.sku}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product with SKU '{product_in.sku}' already exists",
            )
        
        product = await crud_product.create_product(db=db, product_in=product_in)
        return product
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
):
    """
    List all products with optional filtering and pagination.
    
    Query Parameters:
    - **skip**: Number of items to skip (default: 0)
    - **limit**: Number of items to return (default: 100, max: 1000)
    - **category_slug**: Filter by category
    - **brand**: Filter by brand
    - **is_active**: Filter by active status
    - **search**: Search term for name, SKU, or brand
    """
    try:
        products, total = await crud_product.get_products(
            db=db,
            skip=skip,
            limit=limit,
            category_slug=category_slug,
            brand=brand,
            is_active=is_active,
            search=search,
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
        product = await crud_product.get_product_by_id(db=db, product_id=product_id)
        if not product:
            logger.warning(f"Product not found: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving product",
        )


@router.get(
    "/sku/{sku}",
    response_model=ProductResponse,
    summary="Get product by SKU",
    tags=["Products"],
)
async def read_product_by_sku(
    sku: str, db: AsyncSession = Depends(get_db)
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
    """
    Update a product completely.
    
    Only fields that are provided will be updated.
    """
    try:
        product = await crud_product.update_product(
            db=db, product_id=product_id, product_in=product_in
        )
        if not product:
            logger.warning(f"Product not found for update: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return product
    except HTTPException:
        raise
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
    """
    Delete a product using soft delete.
    
    The product is marked as deleted but not removed from database.
    Use the restore endpoint to restore it.
    """
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
    summary="Adjust product stock",
    tags=["Stock Management"],
)
async def adjust_stock(
    product_id: UUID,
    quantity_delta: int = Query(..., description="Quantity to add (positive) or subtract (negative)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Adjust product stock by adding or subtracting quantity.
    
    - **quantity_delta**: Positive number to add stock, negative to subtract
    """
    try:
        product = await crud_product.update_stock(
            db=db, product_id=product_id, quantity_delta=quantity_delta
        )
        if not product:
            logger.warning(f"Product not found for stock adjustment: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found",
            )
        return product
    except HTTPException:
        raise
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
