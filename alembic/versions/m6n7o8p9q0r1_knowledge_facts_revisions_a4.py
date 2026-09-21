"""Prompt 12 / Master KB A4 — knowledge_facts + knowledge_fact_revisions.

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0 (environment_identity marker from #362)
Create Date: 2026-09-21 16:00:00.000000

Facts store values; Property Dictionary owns meaning; PT Definition owns
applicability. No Evidence tables, no JSONB dual-write, no Product assignment.

Note: originally drafted as l5m6n7o8p9q0; renumbered after #362 claimed that
revision id for environment_identity so the linear Alembic chain stays unique.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m6n7o8p9q0r1"
down_revision: str | None = "l5m6n7o8p9q0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_facts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("definition_id", sa.String(length=64), nullable=False),
        sa.Column("product_type_definition_id", sa.Integer(), nullable=True),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("qualifier", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="asserted",
        ),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorder", sa.String(length=128), nullable=False),
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
            ["entity_id"],
            ["products.id"],
            name="fk_knowledge_facts_entity_id_products",
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["knowledge_property_definitions.definition_id"],
            name="fk_knowledge_facts_definition_id",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_definition_id"],
            ["product_type_definitions.id"],
            name="fk_knowledge_facts_product_type_definition_id",
        ),
        sa.CheckConstraint(
            "status IN ('asserted','published','disputed','deprecated')",
            name="ck_knowledge_facts_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_knowledge_facts_confidence",
        ),
        sa.CheckConstraint(
            "char_length(trim(source_id)) > 0",
            name="ck_knowledge_facts_source_id_nonempty",
        ),
        sa.UniqueConstraint(
            "entity_id",
            "definition_id",
            name="uq_knowledge_facts_entity_definition",
        ),
    )
    op.create_index("ix_knowledge_facts_entity_id", "knowledge_facts", ["entity_id"])
    op.create_index(
        "ix_knowledge_facts_definition_id", "knowledge_facts", ["definition_id"]
    )
    op.create_index("ix_knowledge_facts_status", "knowledge_facts", ["status"])
    op.create_index(
        "ix_knowledge_facts_entity_status",
        "knowledge_facts",
        ["entity_id", "status"],
    )
    op.create_index(
        "ix_knowledge_facts_definition_status",
        "knowledge_facts",
        ["definition_id", "status"],
    )

    op.create_table(
        "knowledge_fact_revisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fact_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("qualifier", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("product_type_definition_id", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorder", sa.String(length=128), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
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
            ["fact_id"],
            ["knowledge_facts.id"],
            name="fk_knowledge_fact_revisions_fact_id",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_definition_id"],
            ["product_type_definitions.id"],
            name="fk_knowledge_fact_revisions_ptd_id",
        ),
        sa.CheckConstraint(
            "status IN ('asserted','published','disputed','deprecated')",
            name="ck_knowledge_fact_revisions_status",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_knowledge_fact_revisions_revision_positive",
        ),
        sa.UniqueConstraint(
            "fact_id",
            "revision_number",
            name="uq_knowledge_fact_revisions_fact_revision",
        ),
    )
    op.create_index(
        "ix_knowledge_fact_revisions_fact_id",
        "knowledge_fact_revisions",
        ["fact_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_fact_revisions_fact_id",
        table_name="knowledge_fact_revisions",
    )
    op.drop_table("knowledge_fact_revisions")
    op.drop_index(
        "ix_knowledge_facts_definition_status",
        table_name="knowledge_facts",
    )
    op.drop_index("ix_knowledge_facts_entity_status", table_name="knowledge_facts")
    op.drop_index("ix_knowledge_facts_status", table_name="knowledge_facts")
    op.drop_index("ix_knowledge_facts_definition_id", table_name="knowledge_facts")
    op.drop_index("ix_knowledge_facts_entity_id", table_name="knowledge_facts")
    op.drop_table("knowledge_facts")
