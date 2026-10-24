"""Brand-scoped bulk base_price adjustment operations (admin Feature D)."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base
from app.db.models.product import _enum_values


class BrandPriceAdjustmentMode(str, enum.Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class BrandPriceAdjustmentDirection(str, enum.Enum):
    INCREASE = "increase"
    DECREASE = "decrease"


class BrandPriceOperationStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    APPLIED = "applied"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BrandPriceLineStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    SKIPPED = "skipped"
    CONFLICT = "conflict"


class BrandPriceOperation(Base):
    __tablename__ = "brand_price_operations"
    __table_args__ = (
        Index("ix_brand_price_operations_brand_id", "brand_id"),
        Index("ix_brand_price_operations_status", "status"),
        Index("ix_brand_price_operations_actor_user_id", "actor_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    status: Mapped[BrandPriceOperationStatus] = mapped_column(
        Enum(
            BrandPriceOperationStatus,
            values_callable=_enum_values,
            name="brandpriceoperationstatus",
            native_enum=True,
        ),
        nullable=False,
    )
    adjustment_mode: Mapped[BrandPriceAdjustmentMode] = mapped_column(
        Enum(
            BrandPriceAdjustmentMode,
            values_callable=_enum_values,
            name="brandpriceadjustmentmode",
            native_enum=True,
        ),
        nullable=False,
    )
    adjustment_direction: Mapped[BrandPriceAdjustmentDirection] = mapped_column(
        Enum(
            BrandPriceAdjustmentDirection,
            values_callable=_enum_values,
            name="brandpriceadjustmentdirection",
            native_enum=True,
        ),
        nullable=False,
    )
    adjustment_amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    catalog_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    apply_error: Mapped[str | None] = mapped_column(Text)
    audit_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    lines: Mapped[list["BrandPriceOperationLine"]] = relationship(
        "BrandPriceOperationLine",
        back_populates="operation",
        cascade="all, delete-orphan",
    )


class BrandPriceOperationLine(Base):
    __tablename__ = "brand_price_operation_lines"
    __table_args__ = (
        UniqueConstraint("operation_id", "product_id", name="uq_brand_price_op_lines_op_product"),
        Index("ix_brand_price_operation_lines_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("brand_price_operations.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    sku_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    old_base_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    new_base_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    original_price_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    line_status: Mapped[BrandPriceLineStatus] = mapped_column(
        Enum(
            BrandPriceLineStatus,
            values_callable=_enum_values,
            name="brandpricelinestatus",
            native_enum=True,
        ),
        nullable=False,
    )
    conflict_reason: Mapped[str | None] = mapped_column(String(128))

    operation: Mapped[BrandPriceOperation] = relationship(
        "BrandPriceOperation", back_populates="lines"
    )
