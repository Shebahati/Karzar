"""Knowledge Graph overlay models (ADR-013).

KB-001: knowledge_edges (Board Day-2 freeze types).
Prompt 11A: Property Dictionary units / definitions / aliases.
No Facts dual-write in this module.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
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


# --- Prompt 11A Property Dictionary (Master KB §10.2) ---

PROPERTY_DATA_TYPES = (
    "boolean",
    "integer",
    "number",
    "quantity",
    "range",
    "enum",
    "string",
    "string_array",
    "ref_standard",
    "ref_document",
)

DICTIONARY_STATUSES = ("draft", "active", "deprecated")

UNIT_DIMENSIONS = (
    "length",
    "angle",
    "mass",
    "dimensionless",
    "hardness",
)


class KnowledgeUnit(Base):
    """Canonical unit of measure for Property Dictionary (11A)."""

    __tablename__ = "knowledge_units"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','deprecated')",
            name="ck_knowledge_units_status",
        ),
        CheckConstraint(
            "dimension IN ('length','angle','mass','dimensionless','hardness')",
            name="ck_knowledge_units_dimension",
        ),
        UniqueConstraint("dimension", "canonical_code", name="uq_knowledge_units_dimension_code"),
        Index("ix_knowledge_units_status", "status"),
        Index("ix_knowledge_units_dimension", "dimension"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_code: Mapped[str] = mapped_column(String(32), nullable=False)
    aliases: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    conversion_table_version: Mapped[str | None] = mapped_column(String(32))
    label_en: Mapped[str | None] = mapped_column(String(64))
    label_fa: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    seed_version: Mapped[str | None] = mapped_column(String(32))
    seed_checksum: Mapped[str | None] = mapped_column(String(64))


class KnowledgePropertyDefinition(Base):
    """Canonical Property Definition (11A). No Product Type applicability."""

    __tablename__ = "knowledge_property_definitions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','deprecated')",
            name="ck_knowledge_property_definitions_status",
        ),
        CheckConstraint(
            "data_type IN ("
            "'boolean','integer','number','quantity','range','enum',"
            "'string','string_array','ref_standard','ref_document'"
            ")",
            name="ck_knowledge_property_definitions_data_type",
        ),
        UniqueConstraint("definition_id", name="uq_knowledge_property_definitions_definition_id"),
        UniqueConstraint("key", name="uq_knowledge_property_definitions_key"),
        Index("ix_knowledge_property_definitions_status", "status"),
        Index("ix_knowledge_property_definitions_data_type", "data_type"),
        Index("ix_knowledge_property_definitions_unit_dimension", "unit_dimension"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    definition_id: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_dimension: Mapped[str | None] = mapped_column(String(32))
    default_unit: Mapped[str | None] = mapped_column(String(32))
    label_en: Mapped[str] = mapped_column(String(255), nullable=False)
    label_fa: Mapped[str] = mapped_column(String(255), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text)
    description_fa: Mapped[str | None] = mapped_column(Text)
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    enum_values: Mapped[list[Any] | None] = mapped_column(JSONB)
    comparable: Mapped[bool] = mapped_column(nullable=False, default=False)
    filterable: Mapped[bool] = mapped_column(nullable=False, default=False)
    customer_facing: Mapped[bool] = mapped_column(nullable=False, default=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    steward: Mapped[str | None] = mapped_column(String(128))
    supersedes_definition_id: Mapped[str | None] = mapped_column(String(64))
    seed_version: Mapped[str | None] = mapped_column(String(32))
    seed_checksum: Mapped[str | None] = mapped_column(String(64))


class KnowledgePropertyAlias(Base):
    """Non-canonical alias text → one Property Definition (11A)."""

    __tablename__ = "knowledge_property_aliases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','deprecated')",
            name="ck_knowledge_property_aliases_status",
        ),
        UniqueConstraint(
            "alias_normalized",
            name="uq_knowledge_property_aliases_normalized",
        ),
        Index("ix_knowledge_property_aliases_definition_id", "definition_id"),
        Index("ix_knowledge_property_aliases_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    definition_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_property_definitions.definition_id"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="seed_inline")
    language: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
