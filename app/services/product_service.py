# app/services/product_service.py
from uuid import UUID
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, CategorySlug
from app.crud import product as crud_product
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProductService:
    """Business logic service for product operations."""

    @staticmethod
    async def create_product_with_validation(
        db: AsyncSession, product_data: ProductCreate
    ) -> Product:
        """
        Create a product with business logic validation.
        """
        logger.info(f"Creating product: {product_data.sku}")
        
        # Check duplicate SKU
        existing = await crud_product.get_product_by_sku(db, product_data.sku)
        if existing:
            raise ValueError(f"Product with SKU {product_data.sku} already exists")
        
        # Create product
        product = await crud_product.create_product(db, product_data)
        logger.info(f"Product created successfully: {product.id}")
        return product

    @staticmethod
    async def get_product_details(
        db: AsyncSession, product_id: UUID
    ) -> Optional[dict]:
        """
        Get detailed product information including stock status.
        """
        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None
        
        stock_status = "in_stock" if product.stock_quantity > 0 else "out_of_stock"
        low_stock = product.stock_quantity < 10
        
        return {
            "product": product,
            "stock_status": stock_status,
            "low_stock": low_stock,
            "availability": product.is_active and product.stock_quantity > 0,
        }

    @staticmethod
    async def search_products(
        db: AsyncSession,
        query: str,
        category: Optional[CategorySlug] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Product], int]:
        """
        Search products with advanced filtering.
        """
        logger.info(f"Searching products: query={query}, category={category}")
        
        products, total = await crud_product.get_products(
            db=db,
            skip=skip,
            limit=limit,
            category_slug=category,
            search=query,
        )
        
        # Apply price filtering in memory
        if min_price or max_price:
            filtered = []
            for p in products:
                price = float(p.base_price)
                if min_price and price < min_price:
                    continue
                if max_price and price > max_price:
                    continue
                filtered.append(p)
            products = filtered
        
        return products, total

    @staticmethod
    async def update_product_with_validation(
        db: AsyncSession,
        product_id: UUID,
        update_data: ProductUpdate,
    ) -> Optional[Product]:
        """
        Update a product with business logic validation.
        """
        logger.info(f"Updating product: {product_id}")
        
        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None
        
        # If SKU is being updated, check for duplicates
        if update_data.sku and update_data.sku != product.sku:
            existing = await crud_product.get_product_by_sku(db, update_data.sku)
            if existing:
                raise ValueError(f"Product with SKU {update_data.sku} already exists")
        
        updated_product = await crud_product.update_product(
            db, product_id, update_data
        )
        logger.info(f"Product updated successfully: {product_id}")
        return updated_product

    @staticmethod
    async def adjust_stock_with_validation(
        db: AsyncSession,
        product_id: UUID,
        quantity_delta: int,
        reason: Optional[str] = None,
    ) -> Optional[Product]:
        """
        Adjust product stock with validation.
        
        Args:
            db: Database session
            product_id: Product ID
            quantity_delta: Change in quantity (positive or negative)
            reason: Reason for adjustment (e.g., 'sale', 'restock', 'correction')
        """
        logger.info(
            f"Adjusting stock for product {product_id}: delta={quantity_delta}, reason={reason}"
        )
        
        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None
        
        # Check if adjustment would result in negative stock
        new_quantity = product.stock_quantity + quantity_delta
        if new_quantity < 0:
            raise ValueError(
                f"Cannot adjust stock. Would result in negative quantity ({new_quantity})"
            )
        
        updated_product = await crud_product.update_stock(
            db, product_id, quantity_delta
        )
        return updated_product

    @staticmethod
    async def get_low_stock_products(
        db: AsyncSession, threshold: int = 10
    ) -> List[Product]:
        """
        Get products with stock below threshold.
        """
        logger.info(f"Retrieving low stock products (threshold: {threshold})")
        
        products, _ = await crud_product.get_products(
            db=db,
            skip=0,
            limit=10000,
        )
        
        low_stock = [p for p in products if p.stock_quantity < threshold]
        logger.info(f"Found {len(low_stock)} products with low stock")
        return low_stock

    @staticmethod
    async def get_products_by_brand(
        db: AsyncSession, brand: str, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Product], int]:
        """
        Get all products from a specific brand.
        """
        logger.info(f"Retrieving products for brand: {brand}")
        
        return await crud_product.get_products(
            db=db,
            skip=skip,
            limit=limit,
            brand=brand,
        )

    @staticmethod
    async def get_product_statistics(db: AsyncSession) -> dict:
        """
        Get product statistics.
        """
        products, total = await crud_product.get_products(
            db=db, skip=0, limit=10000
        )
        
        total_value = sum(float(p.base_price) * p.stock_quantity for p in products)
        avg_price = sum(float(p.base_price) for p in products) / len(products) if products else 0
        total_stock = sum(p.stock_quantity for p in products)
        active_products = sum(1 for p in products if p.is_active)
        
        stats = {
            "total_products": total,
            "active_products": active_products,
            "total_stock_value": total_value,
            "average_price": round(avg_price, 2),
            "total_stock_quantity": total_stock,
            "categories": len(set(p.category_slug for p in products)),
            "brands": len(set(p.brand for p in products)),
        }
        
        logger.info(f"Product statistics: {stats}")
        return stats
