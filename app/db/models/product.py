# app/db/models/product.py

from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Numeric, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base

class Product(Base):
    """
    SQLAlchemy 2.0 Declarative Model for Industrial Tools.
    Utilizes PostgreSQL JSONB for dynamic specifications.
    """
    __tablename__ = "products"

    # Primary Key
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Core Identifiers
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    # Financial & Inventory
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Dynamic Attributes (JSONB)
    # This single field will store technical_specs, features, dimensions, and optional_accessories
    specifications: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<Product(id='{self.id}', sku='{self.sku}', name='{self.name}', brand='{self.brand}')>"