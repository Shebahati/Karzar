"""Storefront commerce models: orders and line items."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base
from app.db.models.product import _enum_values


class OrderMode(str, enum.Enum):
    PURCHASE = "purchase"
    INQUIRY = "inquiry"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracking_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    mode: Mapped[OrderMode] = mapped_column(
        Enum(OrderMode, values_callable=_enum_values, name="ordermode", native_enum=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    estimated_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    customer_full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(15), nullable=False)
    customer_is_guest: Mapped[bool] = mapped_column(default=True, server_default="true")
    company_name: Mapped[Optional[str]] = mapped_column(String(120))
    note: Mapped[Optional[str]] = mapped_column(Text)
    shipping: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    order: Mapped["Order"] = relationship("Order", back_populates="items")
