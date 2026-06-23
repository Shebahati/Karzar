"""SQLAlchemy declarative base with shared audit timestamp columns."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base model providing timezone-aware created_at / updated_at columns.

    Timestamps are delegated to the database via server_default so inserts and
    updates remain consistent regardless of application server clock skew.
    """

    # Set once at insert time by the database.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Refreshed on every UPDATE via SQLAlchemy onupdate hook.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
