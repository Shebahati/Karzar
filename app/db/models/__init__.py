"""ORM model registry — import here to register all tables with Base.metadata."""

from app.db.models.base import Base
from app.db.models.commerce import (
    Order,
    OrderItem,
    OrderMode,
    OrderStatus,
    OrderStatusEvent,
    PaymentStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
)
from app.db.models.content import (
    Article,
    ContactSubmission,
    HeroSlide,
    MegamenuNavGroup,
    OtpCode,
    OtpPurpose,
    ProductComment,
)
from app.db.models.hesabfa import (
    HesabfaContactMapping,
    HesabfaInvoiceRecord,
    HesabfaItemMapping,
)
from app.db.models.knowledge import (
    KnowledgeEdge,
    KnowledgePropertyAlias,
    KnowledgePropertyDefinition,
    KnowledgeUnit,
)
from app.db.models.platform import (
    AdminAuditLog,
    Cart,
    CartItem,
    CartLane,
    IdempotencyKey,
    ProductChangeLog,
    RefreshToken,
    StepUpTokenUse,
)
from app.db.models.product import (
    Brand,
    Category,
    Product,
    ProductImage,
    StockMovement,
    StockMovementType,
    StockUnitEnum,
)
from app.db.models.product_type import ProductType, ProductTypeStatus
from app.db.models.user import User, UserRole

__all__ = [
    "Base",
    "Category",
    "Brand",
    "Product",
    "ProductType",
    "ProductTypeStatus",
    "ProductImage",
    "ProductComment",
    "StockUnitEnum",
    "StockMovement",
    "StockMovementType",
    "User",
    "UserRole",
    "Article",
    "KnowledgeEdge",
    "KnowledgeUnit",
    "KnowledgePropertyDefinition",
    "KnowledgePropertyAlias",
    "HeroSlide",
    "MegamenuNavGroup",
    "ContactSubmission",
    "OtpCode",
    "OtpPurpose",
    "Order",
    "OrderItem",
    "OrderStatusEvent",
    "OrderMode",
    "OrderStatus",
    "PaymentStatus",
    "PaymentTransaction",
    "PaymentTransactionStatus",
    "HesabfaItemMapping",
    "HesabfaContactMapping",
    "HesabfaInvoiceRecord",
    "Cart",
    "CartItem",
    "CartLane",
    "RefreshToken",
    "AdminAuditLog",
    "ProductChangeLog",
    "IdempotencyKey",
    "StepUpTokenUse",
]
