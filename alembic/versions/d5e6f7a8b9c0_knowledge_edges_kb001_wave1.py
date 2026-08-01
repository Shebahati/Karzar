"""KB-001 wave-1 knowledge_edges overlay table (ADR-013).

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-01 11:00:00.000000

Board Day-2 freeze: PRODUCT_BELONGS_TO_CATEGORY, PRODUCT_BRANDED_AS,
ARTICLE_EXPLAINS_PRODUCT only. No Facts / dual-write schema.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_edges",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("edge_type", sa.String(length=64), nullable=False),
        sa.Column("from_node_type", sa.String(length=32), nullable=False),
        sa.Column("from_node_id", sa.Integer(), nullable=False),
        sa.Column("to_node_type", sa.String(length=32), nullable=False),
        sa.Column("to_node_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorder", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.CheckConstraint(
            "edge_type IN ("
            "'PRODUCT_BELONGS_TO_CATEGORY',"
            "'PRODUCT_BRANDED_AS',"
            "'ARTICLE_EXPLAINS_PRODUCT'"
            ")",
            name="ck_knowledge_edges_edge_type_kb001",
        ),
        sa.CheckConstraint(
            "status IN ('asserted','published','rejected','deprecated')",
            name="ck_knowledge_edges_status",
        ),
        sa.CheckConstraint(
            "from_node_type IN ('product','category','brand','article')",
            name="ck_knowledge_edges_from_node_type",
        ),
        sa.CheckConstraint(
            "to_node_type IN ('product','category','brand','article')",
            name="ck_knowledge_edges_to_node_type",
        ),
        sa.UniqueConstraint(
            "edge_type",
            "from_node_type",
            "from_node_id",
            "to_node_type",
            "to_node_id",
            name="uq_knowledge_edges_identity",
        ),
    )
    op.create_index("ix_knowledge_edges_edge_type", "knowledge_edges", ["edge_type"])
    op.create_index(
        "ix_knowledge_edges_from",
        "knowledge_edges",
        ["from_node_type", "from_node_id", "edge_type"],
    )
    op.create_index(
        "ix_knowledge_edges_to",
        "knowledge_edges",
        ["to_node_type", "to_node_id", "edge_type"],
    )
    op.create_index(
        "ix_knowledge_edges_type_status",
        "knowledge_edges",
        ["edge_type", "status"],
    )
    op.create_index(
        "ix_knowledge_edges_active_from",
        "knowledge_edges",
        ["from_node_type", "from_node_id", "edge_type"],
        postgresql_where=sa.text("status IN ('asserted','published')"),
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_edges_active_from", table_name="knowledge_edges")
    op.drop_index("ix_knowledge_edges_type_status", table_name="knowledge_edges")
    op.drop_index("ix_knowledge_edges_to", table_name="knowledge_edges")
    op.drop_index("ix_knowledge_edges_from", table_name="knowledge_edges")
    op.drop_index("ix_knowledge_edges_edge_type", table_name="knowledge_edges")
    op.drop_table("knowledge_edges")
