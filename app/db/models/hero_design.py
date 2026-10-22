"""Hero Studio revision store (PR1 foundation)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base

HERO_PROFILE_REBORN_5_V1 = "reborn-5@v1"


class HeroDesignRevision(Base):
    __tablename__ = "hero_design_revisions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','published','superseded','rolled_back')",
            name="ck_hero_design_revisions_status",
        ),
        Index("ix_hero_design_revisions_created_at", "created_at"),
        Index("ix_hero_design_revisions_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    schema_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    profile: Mapped[str] = mapped_column(
        String(64), nullable=False, default=HERO_PROFILE_REBORN_5_V1
    )
    pack_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    pack_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_revision_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("hero_design_revisions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    publish_comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class HeroDesignPublished(Base):
    __tablename__ = "hero_design_published"
    __table_args__ = (CheckConstraint("id = 1", name="ck_hero_design_published_singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hero_design_revisions.id"), nullable=False
    )
    etag: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)


class HeroDesignDraft(Base):
    __tablename__ = "hero_design_drafts"
    __table_args__ = (CheckConstraint("id = 1", name="ck_hero_design_drafts_singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    base_revision_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("hero_design_revisions.id"), nullable=True
    )
    draft_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
