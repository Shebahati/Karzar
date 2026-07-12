"""Storefront commerce models: orders, line items, and status history."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base
from app.db.models.product import _enum_values


class OrderMode(str, enum.Enum):
    PURCHASE = "purchase"
    INQUIRY = "inquiry"


class OrderStatus(str, enum.Enum):
    """Canonical order lifecycle states (stored as text; labelled in the API)."""

    # Purchase flow
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    # Inquiry (B2B quote) flow
    INQUIRY_REVIEW = "inquiry_review"
    INQUIRY_QUOTED = "inquiry_quoted"
    INQUIRY_CLOSED = "inquiry_closed"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracking_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    mode: Mapped[OrderMode] = mapped_column(
        Enum(OrderMode, values_callable=_enum_values, name="ordermode", native_enum=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.UNPAID.value, server_default="unpaid"
    )
    estimated_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    customer_full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(15), nullable=False)
    customer_is_guest: Mapped[bool] = mapped_column(default=True, server_default="true")
    company_name: Mapped[Optional[str]] = mapped_column(String(120))
    note: Mapped[Optional[str]] = mapped_column(Text)
    admin_note: Mapped[Optional[str]] = mapped_column(Text)
    shipping: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    postal_tracking_code: Mapped[Optional[str]] = mapped_column(String(64))
    delivery_eta: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    invoice: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(32))
    invoice_valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    payment_authority: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    payment_ref_id: Mapped[Optional[str]] = mapped_column(String(64))
    payment_refund_id: Mapped[Optional[str]] = mapped_column(String(64))

    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    status_events: Mapped[List["OrderStatusEvent"]] = relationship(
        "OrderStatusEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusEvent.created_at",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    order: Mapped["Order"] = relationship("Order", back_populates="items")


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"
    __table_args__ = (Index("ix_order_status_events_order_id", "order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(20), nullable=False, default="system", server_default="system")

    order: Mapped["Order"] = relationship("Order", back_populates="status_events")
