"""Prompt 13 / Master KB A5 — Evidence artifacts/links + taxonomy + classification.

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1 (Prompt 12 Facts)
Create Date: 2026-09-22 12:00:00.000000

Empty overlay tables only. No seed, no backfill, no Product/Fact/Category UPDATE.
Does not add PRODUCT_CLASSIFIED_AS to the frozen KB-001 KnowledgeEdge registry.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n7o8p9q0r1s2"
down_revision: str | None = "m6n7o8p9q0r1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_evidence_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("artifact_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("document_version", sa.String(length=64), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorder", sa.String(length=128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "artifact_id",
            name="uq_knowledge_evidence_artifacts_artifact_id",
        ),
        sa.CheckConstraint(
            "kind IN ("
            "'oem_catalogue','datasheet','standard','certificate',"
            "'lab_report','manual','other'"
            ")",
            name="ck_knowledge_evidence_artifacts_kind",
        ),
        sa.CheckConstraint(
            "checksum_sha256 IS NULL OR checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_knowledge_evidence_artifacts_sha256",
        ),
        sa.CheckConstraint(
            "source_url IS NOT NULL OR source_ref IS NOT NULL OR checksum_sha256 IS NOT NULL",
            name="ck_knowledge_evidence_artifacts_provenance",
        ),
    )
    op.create_index(
        "ix_knowledge_evidence_artifacts_kind",
        "knowledge_evidence_artifacts",
        ["kind"],
    )
    op.create_index(
        "ix_knowledge_evidence_artifacts_checksum",
        "knowledge_evidence_artifacts",
        ["checksum_sha256"],
    )

    op.create_table(
        "knowledge_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("artifact_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("fact_id", sa.Integer(), nullable=True),
        sa.Column("edge_id", sa.Integer(), nullable=True),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column(
            "locator",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("locator_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorder", sa.String(length=128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["knowledge_evidence_artifacts.id"],
            name="fk_knowledge_evidence_links_artifact_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fact_id"],
            ["knowledge_facts.id"],
            name="fk_knowledge_evidence_links_fact_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["edge_id"],
            ["knowledge_edges.id"],
            name="fk_knowledge_evidence_links_edge_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "target_type IN ('fact','edge')",
            name="ck_knowledge_evidence_links_target_type",
        ),
        sa.CheckConstraint(
            "relation_type IN ('FACT_SUPPORTED_BY','EDGE_SUPPORTED_BY')",
            name="ck_knowledge_evidence_links_relation_type",
        ),
        sa.CheckConstraint(
            "("
            "target_type = 'fact' AND fact_id IS NOT NULL AND edge_id IS NULL "
            "AND relation_type = 'FACT_SUPPORTED_BY'"
            ") OR ("
            "target_type = 'edge' AND edge_id IS NOT NULL AND fact_id IS NULL "
            "AND relation_type = 'EDGE_SUPPORTED_BY'"
            ")",
            name="ck_knowledge_evidence_links_target_shape",
        ),
    )
    # Partial unique indexes avoid NULL-distinct issues on the unused target FK.
    op.create_index(
        "uq_knowledge_evidence_links_fact",
        "knowledge_evidence_links",
        ["artifact_id", "fact_id", "relation_type", "locator_fingerprint"],
        unique=True,
        postgresql_where=sa.text("target_type = 'fact'"),
    )
    op.create_index(
        "uq_knowledge_evidence_links_edge",
        "knowledge_evidence_links",
        ["artifact_id", "edge_id", "relation_type", "locator_fingerprint"],
        unique=True,
        postgresql_where=sa.text("target_type = 'edge'"),
    )
    op.create_index(
        "ix_knowledge_evidence_links_fact_id",
        "knowledge_evidence_links",
        ["fact_id"],
    )
    op.create_index(
        "ix_knowledge_evidence_links_edge_id",
        "knowledge_evidence_links",
        ["edge_id"],
    )
    op.create_index(
        "ix_knowledge_evidence_links_artifact_id",
        "knowledge_evidence_links",
        ["artifact_id"],
    )

    op.create_table(
        "knowledge_taxonomy_nodes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("node_type", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name_fa", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "synonyms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("seo_meta_title", sa.String(length=255), nullable=True),
        sa.Column("seo_meta_description", sa.Text(), nullable=True),
        # Spec Template FK deferred — no Specification Template runtime table.
        sa.Column("commerce_category_id", sa.Integer(), nullable=True),
        # Optional bridge to Product Type identity (ADR-015 Hybrid); not a second Type catalogue.
        sa.Column("product_type_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("steward", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["knowledge_taxonomy_nodes.id"],
            name="fk_knowledge_taxonomy_nodes_parent_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["commerce_category_id"],
            ["categories.id"],
            name="fk_knowledge_taxonomy_nodes_commerce_category_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"],
            ["product_types.id"],
            name="fk_knowledge_taxonomy_nodes_product_type_id",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "dimension IN ("
            "'domain','family','application','industry','technical','commerce_category'"
            ")",
            name="ck_knowledge_taxonomy_nodes_dimension",
        ),
        sa.CheckConstraint(
            "status IN ('draft','active','deprecated')",
            name="ck_knowledge_taxonomy_nodes_status",
        ),
        # parent ≠ self enforced in service (CHECK on id is awkward at INSERT).
        sa.UniqueConstraint(
            "node_id",
            name="uq_knowledge_taxonomy_nodes_node_id",
        ),
        sa.UniqueConstraint(
            "dimension",
            "slug",
            name="uq_knowledge_taxonomy_nodes_dimension_slug",
        ),
    )
    op.create_index(
        "ix_knowledge_taxonomy_nodes_dimension_status",
        "knowledge_taxonomy_nodes",
        ["dimension", "status"],
    )
    op.create_index(
        "ix_knowledge_taxonomy_nodes_parent_id",
        "knowledge_taxonomy_nodes",
        ["parent_id"],
    )

    op.create_table(
        "knowledge_classification_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("taxonomy_node_id", sa.Integer(), nullable=False),
        sa.Column("assignment_role", sa.String(length=32), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorder", sa.String(length=128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_knowledge_classification_assignments_product_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_node_id"],
            ["knowledge_taxonomy_nodes.id"],
            name="fk_knowledge_classification_assignments_node_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "assignment_role IN ("
            "'application','industry','technical',"
            "'secondary_domain','product_type_bridge'"
            ")",
            name="ck_knowledge_classification_assignments_role",
        ),
        sa.UniqueConstraint(
            "product_id",
            "taxonomy_node_id",
            "assignment_role",
            name="uq_knowledge_classification_assignments_identity",
        ),
    )
    op.create_index(
        "ix_knowledge_classification_assignments_product_id",
        "knowledge_classification_assignments",
        ["product_id"],
    )
    op.create_index(
        "ix_knowledge_classification_assignments_node_id",
        "knowledge_classification_assignments",
        ["taxonomy_node_id"],
    )


def downgrade() -> None:
    op.drop_table("knowledge_classification_assignments")
    op.drop_table("knowledge_taxonomy_nodes")
    op.drop_table("knowledge_evidence_links")
    op.drop_table("knowledge_evidence_artifacts")
