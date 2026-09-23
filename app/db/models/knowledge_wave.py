"""Knowledge Wave Registry ORM (PR1–PR3-A)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.models.base import Base

_JsonType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class KnowledgeWave(Base):
    """Governed ingestion wave — PR3-A: Draft…Aborted lifecycle."""

    __tablename__ = "knowledge_waves"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'Draft', 'Reviewed', 'Sealed', 'Executing', "
            "'Asserted', 'Failed', 'Aborted'"
            ")",
            name="ck_knowledge_waves_status_pr3",
        ),
        UniqueConstraint("wave_id", name="uq_knowledge_waves_wave_id"),
        UniqueConstraint(
            "manifest_sha256",
            name="uq_knowledge_waves_manifest_sha256",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wave_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Draft")
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("product_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    definition_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("product_type_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_json: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        server_default=text("'{}'"),
    )
    created_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    products: Mapped[list[KnowledgeWaveProduct]] = relationship(
        "KnowledgeWaveProduct",
        back_populates="wave",
        cascade="all, delete-orphan",
    )


class KnowledgeWaveProduct(Base):
    __tablename__ = "knowledge_wave_products"
    __table_args__ = (
        UniqueConstraint(
            "wave_id",
            "product_id",
            name="uq_knowledge_wave_products_wave_product",
        ),
        UniqueConstraint(
            "wave_id",
            "sku_snapshot",
            name="uq_knowledge_wave_products_wave_sku",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wave_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_waves.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sku_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    wave: Mapped[KnowledgeWave] = relationship(
        "KnowledgeWave",
        back_populates="products",
    )


class KnowledgeWaveRun(Base):
    """Assert/publish execution ledger (PR3-A assert orchestration)."""

    __tablename__ = "knowledge_wave_runs"
    __table_args__ = (
        CheckConstraint(
            "run_type IN ("
            "'validate','dry_run','assert','evidence_validate','publish'"
            ")",
            name="ck_knowledge_wave_runs_run_type",
        ),
        CheckConstraint(
            "status IN ('created','running','completed','failed','aborted')",
            name="ck_knowledge_wave_runs_status_pr3",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wave_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_waves.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    manifest_sha256_snapshot: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        _JsonType, nullable=True
    )

    items: Mapped[list[KnowledgeWaveRunItem]] = relationship(
        "KnowledgeWaveRunItem",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class KnowledgeWaveRunItem(Base):
    __tablename__ = "knowledge_wave_run_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','success','failed','skipped')",
            name="ck_knowledge_wave_run_items_status_pr3",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_wave_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sku_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    resumed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    result_json: Mapped[dict[str, Any] | None] = mapped_column(_JsonType, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run: Mapped[KnowledgeWaveRun] = relationship(
        "KnowledgeWaveRun",
        back_populates="items",
    )
