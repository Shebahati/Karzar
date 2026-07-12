"""User account ORM model and role enumeration."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.db.models.product import _enum_values


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    B2B_CUSTOMER = "b2b_customer"
    B2C_CUSTOMER = "b2c_customer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=_enum_values, name="userrole", native_enum=True),
        default=UserRole.B2C_CUSTOMER,
        server_default="b2c_customer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    company_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
