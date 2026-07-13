"""Platform models: carts, refresh tokens, audit logs, idempotency keys."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base
from app.db.models.product import _enum_values


class CartLane(str, enum.Enum):
    PURCHASE = "purchase"
    INQUIRY = "inquiry"


class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = (
        UniqueConstraint("user_id", "lane", name="uq_carts_user_lane"),
        UniqueConstraint("guest_token", "lane", name="uq_carts_guest_lane"),
        Index("ix_carts_user_id", "user_id"),
        Index("ix_carts_guest_token", "guest_token"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    guest_token: Mapped[str | None] = mapped_column(String(64))
    lane: Mapped[CartLane] = mapped_column(
        Enum(CartLane, values_callable=_enum_values, name="cartlane", native_enum=True),
        nullable=False,
    )

    items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        Index("ix_admin_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_admin_audit_logs_actor_user_id", "actor_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ProductChangeLog(Base):
    __tablename__ = "product_change_logs"
    __table_args__ = (Index("ix_product_change_logs_product_id", "product_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(String(255))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StepUpTokenUse(Base):
    __tablename__ = "step_up_token_uses"
    __table_args__ = (Index("ix_step_up_token_uses_expires_at", "expires_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
