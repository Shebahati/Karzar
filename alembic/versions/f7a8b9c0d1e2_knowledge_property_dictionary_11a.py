"""PT-W1 follow-on A3 / Prompt 11A — Property Dictionary Units + Definitions + Aliases.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-08-02 17:00:00.000000

Creates empty overlay tables only. No seed INSERT. No Product/Type/JSONB mutation.
Templates / Facts / taxonomy deliberately absent.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_units",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("canonical_code", sa.String(length=32), nullable=False),
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("conversion_table_version", sa.String(length=32), nullable=True),
        sa.Column("label_en", sa.String(length=64), nullable=True),
        sa.Column("label_fa", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("seed_version", sa.String(length=32), nullable=True),
        sa.Column("seed_checksum", sa.String(length=64), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('draft','active','deprecated')",
            name="ck_knowledge_units_status",
        ),
        sa.CheckConstraint(
            "dimension IN ('length','angle','mass','dimensionless','hardness')",
            name="ck_knowledge_units_dimension",
        ),
        sa.UniqueConstraint(
            "dimension",
            "canonical_code",
            name="uq_knowledge_units_dimension_code",
        ),
    )
    op.create_index("ix_knowledge_units_status", "knowledge_units", ["status"])
    op.create_index("ix_knowledge_units_dimension", "knowledge_units", ["dimension"])

    op.create_table(
        "knowledge_property_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("definition_id", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("data_type", sa.String(length=32), nullable=False),
        sa.Column("unit_dimension", sa.String(length=32), nullable=True),
        sa.Column("default_unit", sa.String(length=32), nullable=True),
        sa.Column("label_en", sa.String(length=255), nullable=False),
        sa.Column("label_fa", sa.String(length=255), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_fa", sa.Text(), nullable=True),
        sa.Column(
            "validation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("enum_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("comparable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("filterable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("customer_facing", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("steward", sa.String(length=128), nullable=True),
        sa.Column("supersedes_definition_id", sa.String(length=64), nullable=True),
        sa.Column("seed_version", sa.String(length=32), nullable=True),
        sa.Column("seed_checksum", sa.String(length=64), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('draft','active','deprecated')",
            name="ck_knowledge_property_definitions_status",
        ),
        sa.CheckConstraint(
            "data_type IN ("
            "'boolean','integer','number','quantity','range','enum',"
            "'string','string_array','ref_standard','ref_document'"
            ")",
            name="ck_knowledge_property_definitions_data_type",
        ),
        sa.UniqueConstraint(
            "definition_id",
            name="uq_knowledge_property_definitions_definition_id",
        ),
        sa.UniqueConstraint("key", name="uq_knowledge_property_definitions_key"),
    )
    op.create_index(
        "ix_knowledge_property_definitions_status",
        "knowledge_property_definitions",
        ["status"],
    )
    op.create_index(
        "ix_knowledge_property_definitions_data_type",
        "knowledge_property_definitions",
        ["data_type"],
    )
    op.create_index(
        "ix_knowledge_property_definitions_unit_dimension",
        "knowledge_property_definitions",
        ["unit_dimension"],
    )

    op.create_table(
        "knowledge_property_aliases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("definition_id", sa.String(length=64), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("alias_normalized", sa.String(length=255), nullable=False),
        sa.Column(
            "source_kind",
            sa.String(length=32),
            nullable=False,
            server_default="seed_inline",
        ),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
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
            ["definition_id"],
            ["knowledge_property_definitions.definition_id"],
            name="fk_knowledge_property_aliases_definition_id",
        ),
        sa.CheckConstraint(
            "status IN ('draft','active','deprecated')",
            name="ck_knowledge_property_aliases_status",
        ),
        sa.UniqueConstraint(
            "alias_normalized",
            name="uq_knowledge_property_aliases_normalized",
        ),
    )
    op.create_index(
        "ix_knowledge_property_aliases_definition_id",
        "knowledge_property_aliases",
        ["definition_id"],
    )
    op.create_index(
        "ix_knowledge_property_aliases_status",
        "knowledge_property_aliases",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_property_aliases_status",
        table_name="knowledge_property_aliases",
    )
    op.drop_index(
        "ix_knowledge_property_aliases_definition_id",
        table_name="knowledge_property_aliases",
    )
    op.drop_table("knowledge_property_aliases")

    op.drop_index(
        "ix_knowledge_property_definitions_unit_dimension",
        table_name="knowledge_property_definitions",
    )
    op.drop_index(
        "ix_knowledge_property_definitions_data_type",
        table_name="knowledge_property_definitions",
    )
    op.drop_index(
        "ix_knowledge_property_definitions_status",
        table_name="knowledge_property_definitions",
    )
    op.drop_table("knowledge_property_definitions")

    op.drop_index("ix_knowledge_units_dimension", table_name="knowledge_units")
    op.drop_index("ix_knowledge_units_status", table_name="knowledge_units")
    op.drop_table("knowledge_units")
