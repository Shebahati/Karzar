"""Product Type engineering-classification aggregate (ADR-015 Hybrid / PT-W1).

Wave-1 scope: core identity + lifecycle only. No Definition, membership,
readout, taxonomy bridge, or catalogue seed.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.product import Product


class ProductTypeStatus(str, enum.Enum):
    """Lifecycle for Product Type rows (SPEC-canonical-product-type-model §6.4)."""

    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class ProductType(Base):
    """First-class engineering Product Type (not commerce Category)."""

    __tablename__ = "product_types"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','retired')",
            name="ck_product_types_status",
        ),
        Index("ix_product_types_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    name_fa: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Stored as String + CHECK (KnowledgeEdge / OrderStatus pattern) — not a PG ENUM.
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductTypeStatus.DRAFT.value,
        server_default=ProductTypeStatus.DRAFT.value,
    )

    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="product_type",
        # "all": never null loaded Product FKs on ProductType delete; DB RESTRICT/NO ACTION must fire.
        passive_deletes="all",
    )

    def __str__(self) -> str:
        return self.code
