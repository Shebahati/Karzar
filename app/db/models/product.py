"""Catalog ORM models: categories, brands, products, and product images."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum member values (lowercase strings) instead of Python names."""
    return [member.value for member in enum_cls]


class StockUnitEnum(str, enum.Enum):
    PIECE = "piece"
    KG = "kg"
    METER = "meter"
    PACK = "pack"


def get_default_specifications() -> dict[str, Any]:
    """Factory for the JSONB specifications column default structure."""
    return {
        "technical_specs": {
            "range": "",
            "accuracy": "",
            "resolution": "",
            "material": "",
            "standard": "",
            "battery_type": "",
        },
        "features": {
            "waterproof": False,
            "data_output": False,
            "auto_power_off": False,
            "buttons": [],
            "certification": "",
        },
        "dimensions": {"L_mm": 0.0, "a_mm": 0.0, "b_mm": 0.0, "c_mm": 0.0, "d_mm": 0.0},
        "optional_accessories": [],
    }


class Category(Base):
    """Self-referential category tree node."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint(
            "parent_id",
            "name",
            name="uq_categories_parent_name",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_categories_parent_id", "parent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    spec_template_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    subcategories: Mapped[List["Category"]] = relationship("Category", back_populates="parent")
    parent: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="subcategories", remote_side=[id]
    )
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")

    def __str__(self) -> str:
        return self.name


class Brand(Base):
    __tablename__ = "brands"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(50))
    products: Mapped[List["Product"]] = relationship("Product", back_populates="brand")

    def __str__(self) -> str:
        return self.name


class Product(Base):
    """Core product entity with monetary fields stored as Numeric/Decimal."""

    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_brand_id", "brand_id"),
        Index("ix_products_active_list", "is_active", "deleted_at"),
        Index(
            "uq_products_sku_active",
            "sku",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_products_specifications_gin",
            "specifications",
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.id"))

    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    stock_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.0"), server_default="0"
    )
    stock_unit: Mapped[StockUnitEnum] = mapped_column(
        Enum(StockUnitEnum, values_callable=_enum_values, name="stockunitenum", native_enum=True),
        default=StockUnitEnum.PIECE,
        server_default="piece",
    )

    warranty_text: Mapped[Optional[str]] = mapped_column(String(255))
    weight_grams: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    is_original: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    tax_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.0"), server_default="0"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    pdf_catalog_url: Mapped[Optional[str]] = mapped_column(String(500))
    specifications: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=get_default_specifications
    )

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    brand: Mapped[Optional["Brand"]] = relationship("Brand", back_populates="products")
    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage", back_populates="product", cascade="all, delete-orphan"
    )


class ProductImage(Base):
    __tablename__ = "product_images"
    __table_args__ = (
        Index(
            "uq_product_images_one_primary",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary IS TRUE"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    product: Mapped["Product"] = relationship("Product", back_populates="images")
