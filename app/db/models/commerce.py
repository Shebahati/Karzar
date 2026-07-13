"""Storefront commerce models: orders, line items, and status history."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

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


class PaymentTransactionStatus(str, enum.Enum):
    INITIATED = "initiated"
    VERIFIED = "verified"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentTransaction(Base):
    """Append-only payment gateway audit ledger."""

    __tablename__ = "payment_transactions"
    __table_args__ = (
        Index("ix_payment_transactions_order_id", "order_id"),
        Index("ix_payment_transactions_authority", "authority"),
        Index("ix_payment_transactions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    gateway: Mapped[str] = mapped_column(String(32), nullable=False)
    authority: Mapped[str | None] = mapped_column(String(64))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))

    order: Mapped["Order"] = relationship("Order", back_populates="payment_transactions")


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
    estimated_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    customer_full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(15), nullable=False)
    customer_is_guest: Mapped[bool] = mapped_column(default=True, server_default="true")
    company_name: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
    admin_note: Mapped[str | None] = mapped_column(Text)
    shipping: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    postal_tracking_code: Mapped[str | None] = mapped_column(String(64))
    delivery_eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invoice: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    invoice_number: Mapped[str | None] = mapped_column(String(32))
    invoice_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    payment_authority: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    payment_ref_id: Mapped[str | None] = mapped_column(String(64))
    payment_refund_id: Mapped[str | None] = mapped_column(String(64))

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    status_events: Mapped[list["OrderStatusEvent"]] = relationship(
        "OrderStatusEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusEvent.created_at",
    )
    payment_transactions: Mapped[list["PaymentTransaction"]] = relationship(
        "PaymentTransaction",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="PaymentTransaction.created_at",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    order: Mapped["Order"] = relationship("Order", back_populates="items")


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"
    __table_args__ = (Index("ix_order_status_events_order_id", "order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(20), nullable=False, default="system", server_default="system")

    order: Mapped["Order"] = relationship("Order", back_populates="status_events")
