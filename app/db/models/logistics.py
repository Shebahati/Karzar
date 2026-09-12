"""First-class shipments, quote persistence, and append-only shipment events."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.commerce import Order


class ShippingClass(str, enum.Enum):
    PARCEL = "parcel"
    FREIGHT_ONLY = "freight_only"


class ShipmentStatus(str, enum.Enum):
    AWAITING_PACKAGING = "awaiting_packaging"
    PENDING_BOOKING = "pending_booking"
    BOOKING = "booking"
    BOOKED = "booked"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"
    RETURNING = "returning"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    CANCELLATION_PENDING = "cancellation_pending"
    PROVIDER_UNKNOWN = "provider_unknown"
    CREATION_UNCERTAIN = "creation_uncertain"
    ERROR = "error"
    FREIGHT_REQUIRED = "freight_required"


class ShippingQuote(Base):
    """Server-owned quote option. Client amounts are never authority."""

    __tablename__ = "shipping_quotes"
    __table_args__ = (
        Index("ix_shipping_quotes_user_id", "user_id"),
        Index("ix_shipping_quotes_group_id", "group_id"),
        Index("ix_shipping_quotes_expires_at", "expires_at"),
        UniqueConstraint("token", name="uq_shipping_quotes_token"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    group_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="postex")
    destination_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    cart_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    destination_location_code: Mapped[int] = mapped_column(Integer, nullable=False)
    carrier_code: Mapped[str] = mapped_column(String(64), nullable=False)
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    provider_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="IRR")
    provider_amount_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    customer_amount_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    pickup_amount_toman: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    package_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    raw_provider_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    consumed_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        Index("ix_shipments_order_id", "order_id"),
        Index("ix_shipments_status", "status"),
        Index("ix_shipments_booking_next_attempt_at", "booking_next_attempt_at"),
        Index("ix_shipments_tracking_sync_at", "last_tracking_sync_at"),
        Index(
            "uq_shipments_provider_parcel_no",
            "provider",
            "provider_parcel_no",
            unique=True,
            postgresql_where=text("provider_parcel_no IS NOT NULL"),
        ),
        Index(
            "uq_shipments_provider_tracking_code",
            "provider",
            "tracking_code",
            unique=True,
            postgresql_where=text("tracking_code IS NOT NULL"),
        ),
        UniqueConstraint("public_id", name="uq_shipments_public_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False, default=lambda: str(uuid4()))
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("shipping_quotes.id"))
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="postex")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_booking")
    carrier_code: Mapped[str | None] = mapped_column(String(64))
    service_code: Mapped[str | None] = mapped_column(String(64))
    service_name: Mapped[str | None] = mapped_column(String(255))
    provider_parcel_no: Mapped[str | None] = mapped_column(String(64))
    tracking_code: Mapped[str | None] = mapped_column(String(64))
    shipping_payment_mode: Mapped[str | None] = mapped_column(String(32))
    package_length_cm: Mapped[int | None] = mapped_column(Integer)
    package_width_cm: Mapped[int | None] = mapped_column(Integer)
    package_height_cm: Mapped[int | None] = mapped_column(Integer)
    package_weight_grams: Mapped[int | None] = mapped_column(Integer)
    package_is_fragile: Mapped[bool | None] = mapped_column(Boolean)
    package_is_liquid: Mapped[bool | None] = mapped_column(Boolean)
    package_measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_box_type_id: Mapped[int | None] = mapped_column(Integer)
    provider_quoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    declared_value_irr: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    provider_quoted_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    provider_actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    customer_shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ready_to_accept: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    booking_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    booking_next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_tracking_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    provider_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    order: Mapped[Order] = relationship("Order", back_populates="shipments")
    events: Mapped[list[ShipmentEvent]] = relationship(
        "ShipmentEvent",
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="ShipmentEvent.id",
    )


class ShipmentEvent(Base):
    """Append-only provider/domain event log. Never update rows."""

    __tablename__ = "shipment_events"
    __table_args__ = (
        Index("ix_shipment_events_shipment_id", "shipment_id"),
        UniqueConstraint("shipment_id", "dedupe_key", name="uq_shipment_events_dedupe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_status: Mapped[str | None] = mapped_column(String(128))
    provider_code: Mapped[str | None] = mapped_column(String(64))
    provider_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    shipment: Mapped[Shipment] = relationship("Shipment", back_populates="events")
