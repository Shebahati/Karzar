"""Prompt 64 / Wave Registry PR1 — additive Knowledge Wave tables.

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
Create Date: 2026-09-23

Empty overlay tables only. No seed, no backfill, no UPDATE on existing tables.
Downgrade drops only these four tables.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "o8p9q0r1s2t3"
down_revision: str | None = "n7o8p9q0r1s2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_waves",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("wave_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("product_type_id", sa.Integer(), nullable=False),
        sa.Column("definition_id", sa.Integer(), nullable=False),
        sa.Column(
            "policy_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
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
            name="fk_knowledge_waves_product_type_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["product_type_definitions.id"],
            name="fk_knowledge_waves_definition_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_knowledge_waves_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_knowledge_waves_reviewed_by",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("wave_id", name="uq_knowledge_waves_wave_id"),
        sa.UniqueConstraint(
            "manifest_sha256",
            name="uq_knowledge_waves_manifest_sha256",
        ),
        sa.CheckConstraint(
            "status IN ('Draft', 'Reviewed')",
            name="ck_knowledge_waves_status_pr1",
        ),
        sa.CheckConstraint(
            "manifest_sha256 IS NULL OR manifest_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_knowledge_waves_manifest_sha256",
        ),
    )
    op.create_index("ix_knowledge_waves_status", "knowledge_waves", ["status"])
    op.create_index(
        "ix_knowledge_waves_product_type_id",
        "knowledge_waves",
        ["product_type_id"],
    )
    op.create_index(
        "ix_knowledge_waves_definition_id",
        "knowledge_waves",
        ["definition_id"],
    )

    op.create_table(
        "knowledge_wave_products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("wave_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_snapshot", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["wave_id"],
            ["knowledge_waves.id"],
            name="fk_knowledge_wave_products_wave_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_knowledge_wave_products_product_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "wave_id",
            "product_id",
            name="uq_knowledge_wave_products_wave_product",
        ),
        sa.UniqueConstraint(
            "wave_id",
            "sku_snapshot",
            name="uq_knowledge_wave_products_wave_sku",
        ),
    )
    op.create_index(
        "ix_knowledge_wave_products_product_id",
        "knowledge_wave_products",
        ["product_id"],
    )

    op.create_table(
        "knowledge_wave_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("wave_id", sa.Integer(), nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["wave_id"],
            ["knowledge_waves.id"],
            name="fk_knowledge_wave_runs_wave_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_knowledge_wave_runs_created_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "run_type IN ("
            "'validate','dry_run','assert','evidence_validate','publish'"
            ")",
            name="ck_knowledge_wave_runs_run_type",
        ),
        sa.CheckConstraint(
            "status IN ('running','succeeded','failed','aborted')",
            name="ck_knowledge_wave_runs_status",
        ),
    )
    op.create_index(
        "ix_knowledge_wave_runs_wave_id",
        "knowledge_wave_runs",
        ["wave_id"],
    )

    op.create_table(
        "knowledge_wave_run_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("sku_snapshot", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["knowledge_wave_runs.id"],
            name="fk_knowledge_wave_run_items_run_id",
            ondelete="CASCADE",
        ),
        # No Fact FK / Evidence FK (Prompt 64).
        sa.CheckConstraint(
            "status IN ('pending','ok','failed','skipped')",
            name="ck_knowledge_wave_run_items_status",
        ),
    )
    op.create_index(
        "ix_knowledge_wave_run_items_run_id",
        "knowledge_wave_run_items",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_wave_run_items_run_id",
        table_name="knowledge_wave_run_items",
    )
    op.drop_table("knowledge_wave_run_items")
    op.drop_index("ix_knowledge_wave_runs_wave_id", table_name="knowledge_wave_runs")
    op.drop_table("knowledge_wave_runs")
    op.drop_index(
        "ix_knowledge_wave_products_product_id",
        table_name="knowledge_wave_products",
    )
    op.drop_table("knowledge_wave_products")
    op.drop_index("ix_knowledge_waves_definition_id", table_name="knowledge_waves")
    op.drop_index("ix_knowledge_waves_product_type_id", table_name="knowledge_waves")
    op.drop_index("ix_knowledge_waves_status", table_name="knowledge_waves")
    op.drop_table("knowledge_waves")
