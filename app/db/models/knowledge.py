"""Knowledge Graph overlay models (ADR-013).

KB-001: knowledge_edges (Board Day-2 freeze types).
Prompt 11A: Property Dictionary units / definitions / aliases.
Prompt 12 / A4: knowledge_facts + knowledge_fact_revisions.
Prompt 13 / A5: evidence artifacts/links + taxonomy + classification assignments.
No JSONB dual-write in this module.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
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


# --- Prompt 12 / Master KB A4 Facts (Accepted: asserted|published|disputed|deprecated) ---

FACT_STATUSES = ("asserted", "published", "disputed", "deprecated")
PUBLIC_FACT_STATUSES = frozenset({"published"})


class KnowledgeFact(Base):
    """Current Fact value for one Product × Property (ADR-013 / ADR-014).

    entity_id = products.id (PKE join). definition_id = Property Dictionary stable id.
    product_type_definition_id pins the Definition used for validation/publication.
    """

    __tablename__ = "knowledge_facts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('asserted','published','disputed','deprecated')",
            name="ck_knowledge_facts_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_knowledge_facts_confidence",
        ),
        UniqueConstraint(
            "entity_id",
            "definition_id",
            name="uq_knowledge_facts_entity_definition",
        ),
        Index("ix_knowledge_facts_entity_id", "entity_id"),
        Index("ix_knowledge_facts_definition_id", "definition_id"),
        Index("ix_knowledge_facts_status", "status"),
        Index("ix_knowledge_facts_entity_status", "entity_id", "status"),
        Index("ix_knowledge_facts_definition_status", "definition_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
    )
    definition_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_property_definitions.definition_id"),
        nullable=False,
    )
    product_type_definition_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_type_definitions.id"),
        nullable=True,
    )
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    qualifier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="asserted",
        server_default="asserted",
    )
    # Provenance identity/reference for Prompt 12 — not an EvidenceArtifact FK.
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorder: Mapped[str] = mapped_column(String(128), nullable=False)


class KnowledgeFactRevision(Base):
    """Append-only historical snapshot of a Fact after create/mutation/transition."""

    __tablename__ = "knowledge_fact_revisions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('asserted','published','disputed','deprecated')",
            name="ck_knowledge_fact_revisions_status",
        ),
        CheckConstraint(
            "revision_number >= 1",
            name="ck_knowledge_fact_revisions_revision_positive",
        ),
        UniqueConstraint(
            "fact_id",
            "revision_number",
            name="uq_knowledge_fact_revisions_fact_revision",
        ),
        Index("ix_knowledge_fact_revisions_fact_id", "fact_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fact_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_facts.id"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    qualifier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    product_type_definition_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_type_definitions.id"),
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorder: Mapped[str] = mapped_column(String(128), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


# --- Prompt 13 / Master KB A5 Evidence + Taxonomy ---

EVIDENCE_ARTIFACT_KINDS = (
    "oem_catalogue",
    "datasheet",
    "standard",
    "certificate",
    "lab_report",
    "manual",
    "other",
)

EVIDENCE_TARGET_TYPES = ("fact", "edge")
EVIDENCE_RELATION_TYPES = ("FACT_SUPPORTED_BY", "EDGE_SUPPORTED_BY")

TAXONOMY_DIMENSIONS = (
    "domain",
    "family",
    "application",
    "industry",
    "technical",
    "commerce_category",
)

TAXONOMY_STATUSES = ("draft", "active", "deprecated")

TAXONOMY_NODE_TYPES = (
    "industrial_domain",
    "tool_family",
    "knowledge_category",
    "product_subcategory",
    "product_type",
    "application",
    "industry",
    "technical_class",
    "commerce_category",
)

CLASSIFICATION_ASSIGNMENT_ROLES = (
    "application",
    "industry",
    "technical",
    "secondary_domain",
    "product_type_bridge",
)


class KnowledgeEvidenceArtifact(Base):
    """Source document/artifact provenance (Prompt 13). No blob storage."""

    __tablename__ = "knowledge_evidence_artifacts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ("
            "'oem_catalogue','datasheet','standard','certificate',"
            "'lab_report','manual','other'"
            ")",
            name="ck_knowledge_evidence_artifacts_kind",
        ),
        # SHA256 hex format enforced in service + Alembic (Postgres regex).
        CheckConstraint(
            "source_url IS NOT NULL OR source_ref IS NOT NULL OR checksum_sha256 IS NOT NULL",
            name="ck_knowledge_evidence_artifacts_provenance",
        ),
        UniqueConstraint(
            "artifact_id",
            name="uq_knowledge_evidence_artifacts_artifact_id",
        ),
        Index("ix_knowledge_evidence_artifacts_kind", "kind"),
        Index("ix_knowledge_evidence_artifacts_checksum", "checksum_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(1024))
    source_ref: Mapped[str | None] = mapped_column(String(255))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    publisher: Mapped[str | None] = mapped_column(String(255))
    document_version: Mapped[str | None] = mapped_column(String(64))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorder: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class KnowledgeEvidenceLink(Base):
    """Governed Evidence link from an Artifact to a Fact or Edge."""

    __tablename__ = "knowledge_evidence_links"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('fact','edge')",
            name="ck_knowledge_evidence_links_target_type",
        ),
        CheckConstraint(
            "relation_type IN ('FACT_SUPPORTED_BY','EDGE_SUPPORTED_BY')",
            name="ck_knowledge_evidence_links_relation_type",
        ),
        CheckConstraint(
            "("
            "target_type = 'fact' AND fact_id IS NOT NULL AND edge_id IS NULL "
            "AND relation_type = 'FACT_SUPPORTED_BY'"
            ") OR ("
            "target_type = 'edge' AND edge_id IS NOT NULL AND fact_id IS NULL "
            "AND relation_type = 'EDGE_SUPPORTED_BY'"
            ")",
            name="ck_knowledge_evidence_links_target_shape",
        ),
        Index("ix_knowledge_evidence_links_fact_id", "fact_id"),
        Index("ix_knowledge_evidence_links_edge_id", "edge_id"),
        Index("ix_knowledge_evidence_links_artifact_id", "artifact_id"),
        Index(
            "uq_knowledge_evidence_links_fact",
            "artifact_id",
            "fact_id",
            "relation_type",
            "locator_fingerprint",
            unique=True,
            postgresql_where=text("target_type = 'fact'"),
        ),
        Index(
            "uq_knowledge_evidence_links_edge",
            "artifact_id",
            "edge_id",
            "relation_type",
            "locator_fingerprint",
            unique=True,
            postgresql_where=text("target_type = 'edge'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_evidence_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    fact_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("knowledge_facts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    edge_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("knowledge_edges.id", ondelete="RESTRICT"),
        nullable=True,
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    locator_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorder: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class KnowledgeTaxonomyNode(Base):
    """Industrial taxonomy node (Prompt 13). Not a second commerce Category DAG."""

    __tablename__ = "knowledge_taxonomy_nodes"
    __table_args__ = (
        CheckConstraint(
            "dimension IN ("
            "'domain','family','application','industry','technical','commerce_category'"
            ")",
            name="ck_knowledge_taxonomy_nodes_dimension",
        ),
        CheckConstraint(
            "status IN ('draft','active','deprecated')",
            name="ck_knowledge_taxonomy_nodes_status",
        ),
        UniqueConstraint("node_id", name="uq_knowledge_taxonomy_nodes_node_id"),
        UniqueConstraint(
            "dimension",
            "slug",
            name="uq_knowledge_taxonomy_nodes_dimension_slug",
        ),
        Index("ix_knowledge_taxonomy_nodes_dimension_status", "dimension", "status"),
        Index("ix_knowledge_taxonomy_nodes_parent_id", "parent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name_fa: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255))
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("knowledge_taxonomy_nodes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    synonyms: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    seo_meta_title: Mapped[str | None] = mapped_column(String(255))
    seo_meta_description: Mapped[str | None] = mapped_column(Text)
    commerce_category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_type_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    sort_order: Mapped[int | None] = mapped_column(Integer)
    steward: Mapped[str | None] = mapped_column(String(128))


class KnowledgeClassificationAssignment(Base):
    """Secondary multi-dimensional classification of a Product/PKE.

    Primary Product Type identity remains products.product_type_id (ADR-015 Hybrid).
    PRODUCT_CLASSIFIED_AS edge projection is deferred — assignment table is runtime source.
    """

    __tablename__ = "knowledge_classification_assignments"
    __table_args__ = (
        CheckConstraint(
            "assignment_role IN ("
            "'application','industry','technical',"
            "'secondary_domain','product_type_bridge'"
            ")",
            name="ck_knowledge_classification_assignments_role",
        ),
        UniqueConstraint(
            "product_id",
            "taxonomy_node_id",
            "assignment_role",
            name="uq_knowledge_classification_assignments_identity",
        ),
        Index("ix_knowledge_classification_assignments_product_id", "product_id"),
        Index("ix_knowledge_classification_assignments_node_id", "taxonomy_node_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    taxonomy_node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_taxonomy_nodes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignment_role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_ref: Mapped[str | None] = mapped_column(String(255))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorder: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
