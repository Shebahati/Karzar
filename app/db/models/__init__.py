"""ORM model registry — import here to register all tables with Base.metadata."""

from app.db.models.base import Base
from app.db.models.commerce import Order, OrderItem, OrderMode, OrderStatus, PaymentStatus
from app.db.models.content import (
    Article,
    ContactSubmission,
    HeroSlide,
    OtpCode,
    OtpPurpose,
    ProductComment,
)
from app.db.models.product import Brand, Category, Product, ProductImage, StockUnitEnum
from app.db.models.user import User, UserRole

__all__ = [
    "Base",
    "Category",
    "Brand",
    "Product",
    "ProductImage",
    "ProductComment",
    "StockUnitEnum",
    "User",
    "UserRole",
    "Article",
    "HeroSlide",
    "ContactSubmission",
    "OtpCode",
    "OtpPurpose",
    "Order",
    "OrderItem",
    "OrderMode",
    "OrderStatus",
    "PaymentStatus",
]
