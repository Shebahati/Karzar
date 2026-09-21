"""PT-W2 Product Type Definitions + Attribute Memberships.

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-09-21 12:00:00.000000

Creates product_type_definitions and product_type_attribute_memberships.
No Product Type seeds, no assignment backfill, no JSONB mutation, no Facts.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k4l5m6n7o8p9"
down_revision: str | None = "j3k4l5m6n7o8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_type_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_type_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
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
            ["product_type_id"],
            ["product_types.id"],
            name="fk_product_type_definitions_product_type_id",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_product_type_definitions_reviewed_by_user_id",
        ),
        sa.CheckConstraint(
            "status IN ('draft','active','retired')",
            name="ck_product_type_definitions_status",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_product_type_definitions_version_positive",
        ),
        sa.UniqueConstraint(
            "product_type_id",
            "version",
            name="uq_product_type_definitions_type_version",
        ),
    )
    op.create_index(
        "ix_product_type_definitions_product_type_id",
        "product_type_definitions",
        ["product_type_id"],
    )
    op.create_index(
        "ix_product_type_definitions_status",
        "product_type_definitions",
        ["status"],
    )
    # At most one active Definition per Product Type (Postgres).
    op.create_index(
        "uq_product_type_definitions_one_active",
        "product_type_definitions",
        ["product_type_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "product_type_attribute_memberships",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_type_definition_id", sa.Integer(), nullable=False),
        sa.Column("property_definition_id", sa.String(length=64), nullable=False),
        sa.Column("requiredness", sa.String(length=32), nullable=False),
        sa.Column(
            "applicability_condition",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "validation_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("public_visibility_default", sa.Boolean(), nullable=True),
        sa.Column("filterable", sa.Boolean(), nullable=True),
        sa.Column("comparable", sa.Boolean(), nullable=True),
        sa.Column("display_group", sa.String(length=64), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=True),
        sa.Column(
            "evidence_requirement_override",
            sa.String(length=32),
            nullable=True,
        ),
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
            ["product_type_definition_id"],
            ["product_type_definitions.id"],
            name="fk_pt_attr_memberships_definition_id",
        ),
        sa.ForeignKeyConstraint(
            ["property_definition_id"],
            ["knowledge_property_definitions.definition_id"],
            name="fk_pt_attr_memberships_property_definition_id",
        ),
        sa.CheckConstraint(
            "requiredness IN ('required','optional','conditional','forbidden')",
            name="ck_pt_attr_memberships_requiredness",
        ),
        sa.CheckConstraint(
            "evidence_requirement_override IS NULL OR "
            "evidence_requirement_override IN "
            "('required','recommended','not_required')",
            name="ck_pt_attr_memberships_evidence_override",
        ),
        sa.UniqueConstraint(
            "product_type_definition_id",
            "property_definition_id",
            name="uq_pt_attr_memberships_definition_property",
        ),
    )
    op.create_index(
        "ix_pt_attr_memberships_definition_id",
        "product_type_attribute_memberships",
        ["product_type_definition_id"],
    )
    op.create_index(
        "ix_pt_attr_memberships_property_definition_id",
        "product_type_attribute_memberships",
        ["property_definition_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pt_attr_memberships_property_definition_id",
        table_name="product_type_attribute_memberships",
    )
    op.drop_index(
        "ix_pt_attr_memberships_definition_id",
        table_name="product_type_attribute_memberships",
    )
    op.drop_table("product_type_attribute_memberships")

    op.drop_index(
        "uq_product_type_definitions_one_active",
        table_name="product_type_definitions",
    )
    op.drop_index(
        "ix_product_type_definitions_status",
        table_name="product_type_definitions",
    )
    op.drop_index(
        "ix_product_type_definitions_product_type_id",
        table_name="product_type_definitions",
    )
    op.drop_table("product_type_definitions")
