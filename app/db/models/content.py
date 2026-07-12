"""CMS and UGC models: blog articles, hero slides, product comments, contact tickets."""

import enum
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base
from app.db.models.product import Product, _enum_values


class ProductComment(Base):
    __tablename__ = "product_comments"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_product_comments_rating_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified_buyer: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    product: Mapped["Product"] = relationship("Product", back_populates="comments")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image: Mapped[Optional[str]] = mapped_column(String(500))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reading_minutes: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    author: Mapped[str] = mapped_column(String(100), default="تیم فنی کارزار", server_default="تیم فنی کارزار")
    tags: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    related_product_ids: Mapped[List[int]] = mapped_column(JSONB, nullable=False, default=list)
    blocks: Mapped[List[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class HeroSlide(Base):
    __tablename__ = "hero_slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(500))
    cta_label: Mapped[Optional[str]] = mapped_column(String(100))
    cta_href: Mapped[Optional[str]] = mapped_column(String(500))
    image: Mapped[str] = mapped_column(String(500), nullable=False)
    accent: Mapped[str] = mapped_column(String(20), default="#C22026", server_default="#C22026")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class OtpPurpose(str, enum.Enum):
    LOGIN = "login"
    PASSWORD_RESET = "password_reset"


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(15), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(12), nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(
        Enum(OtpPurpose, values_callable=_enum_values, name="otppurpose", native_enum=True),
        default=OtpPurpose.LOGIN,
        server_default="login",
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
