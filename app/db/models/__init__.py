"""ORM model registry — import here to register all tables with Base.metadata."""

from app.db.models.base import Base
from app.db.models.product import Brand, Category, Product, ProductImage, StockUnitEnum
from app.db.models.user import User, UserRole

__all__ = [
    "Base",
    "Category",
    "Brand",
    "Product",
    "ProductImage",
    "StockUnitEnum",
    "User",
    "UserRole",
]
