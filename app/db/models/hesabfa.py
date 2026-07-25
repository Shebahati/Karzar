"""ORM models for Hesabfa (حسابفا) entity mappings and invoice audit."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class HesabfaItemMapping(Base):
    """Links a site product to a Hesabfa item (matched by SKU ↔ ProductCode)."""

    __tablename__ = "hesabfa_item_mappings"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_hesabfa_item_product_id"),
        UniqueConstraint("hesabfa_code", name="uq_hesabfa_item_code"),
        Index("ix_hesabfa_item_mappings_sku", "sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    hesabfa_code: Mapped[str] = mapped_column(String(64), nullable=False)
    hesabfa_product_code: Mapped[str | None] = mapped_column(String(64))
    last_stock: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HesabfaContactMapping(Base):
    """One Hesabfa contact per customer (keyed by phone; optional user_id)."""

    __tablename__ = "hesabfa_contact_mappings"
    __table_args__ = (
        UniqueConstraint("customer_phone", name="uq_hesabfa_contact_phone"),
        UniqueConstraint("hesabfa_code", name="uq_hesabfa_contact_code"),
        Index("ix_hesabfa_contact_mappings_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    customer_phone: Mapped[str] = mapped_column(String(15), nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(120))
    hesabfa_code: Mapped[str] = mapped_column(String(64), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HesabfaInvoiceRecord(Base):
    """Idempotent record of sale invoices pushed to Hesabfa after payment verify."""

    __tablename__ = "hesabfa_invoice_records"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_hesabfa_invoice_order_id"),
        Index("ix_hesabfa_invoice_records_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    hesabfa_number: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    payload_tag: Mapped[str | None] = mapped_column(String(64))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
