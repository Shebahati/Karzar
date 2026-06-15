# app/db/models/product.py

from sqlalchemy import String, Numeric, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base

class Product(Base):
    """
    SQLAlchemy 2.0 Declarative Model for Industrial Tools.
    Utilizes PostgreSQL JSONB for dynamic specifications.
    """
    __tablename__ = "products"

    # Core Identifiers
    sku: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    # Financial & Inventory
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Dynamic Attributes (JSONB)
    # This single field will store technical_specs, features, dimensions, and optional_accessories
    specifications: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<Product(sku='{self.sku}', name='{self.name}', brand='{self.brand}')>"