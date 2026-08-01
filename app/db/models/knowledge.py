"""Knowledge Graph overlay models (ADR-013) — wave-1 edge table only.

KB-001 freeze (Board Day-2): PRODUCT_BELONGS_TO_CATEGORY, PRODUCT_BRANDED_AS,
ARTICLE_EXPLAINS_PRODUCT. No Facts dual-write in this module.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base

# Board Day-2 KB-001 freeze — must match SPEC-knowledge-graph-registry §5 + minute.
KB001_EDGE_TYPES = (
    "PRODUCT_BELONGS_TO_CATEGORY",
    "PRODUCT_BRANDED_AS",
    "ARTICLE_EXPLAINS_PRODUCT",
)

EDGE_STATUSES = ("asserted", "published", "rejected", "deprecated")
NODE_TYPES = ("product", "category", "brand", "article")


class KnowledgeEdge(Base):
    """Typed knowledge edge overlay on commerce SoR (ADR-013)."""

    __tablename__ = "knowledge_edges"
    __table_args__ = (
        CheckConstraint(
            "edge_type IN ("
            "'PRODUCT_BELONGS_TO_CATEGORY',"
            "'PRODUCT_BRANDED_AS',"
            "'ARTICLE_EXPLAINS_PRODUCT'"
            ")",
            name="ck_knowledge_edges_edge_type_kb001",
        ),
        CheckConstraint(
            "status IN ('asserted','published','rejected','deprecated')",
            name="ck_knowledge_edges_status",
        ),
        CheckConstraint(
            "from_node_type IN ('product','category','brand','article')",
            name="ck_knowledge_edges_from_node_type",
        ),
        CheckConstraint(
            "to_node_type IN ('product','category','brand','article')",
            name="ck_knowledge_edges_to_node_type",
        ),
        UniqueConstraint(
            "edge_type",
            "from_node_type",
            "from_node_id",
            "to_node_type",
            "to_node_id",
            name="uq_knowledge_edges_identity",
        ),
        Index("ix_knowledge_edges_from", "from_node_type", "from_node_id", "edge_type"),
        Index("ix_knowledge_edges_to", "to_node_type", "to_node_id", "edge_type"),
        Index("ix_knowledge_edges_type_status", "edge_type", "status"),
        Index(
            "ix_knowledge_edges_active_from",
            "from_node_type",
            "from_node_id",
            "edge_type",
            postgresql_where=text("status IN ('asserted','published')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    from_node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    to_node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    to_node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="asserted")
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="projection")
    source_ref: Mapped[str | None] = mapped_column(String(255))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorder: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    notes: Mapped[str | None] = mapped_column(Text)
