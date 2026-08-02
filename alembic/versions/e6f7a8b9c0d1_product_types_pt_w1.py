"""PT-W1 Product Type core + nullable products.product_type_id (ADR-015 Hybrid).

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-02 16:00:00.000000

Scope: create product_types; add nullable indexed FK products.product_type_id
with restrictive (NO ACTION / omit ON DELETE) behavior. No seed, no backfill,
no JSONB rewrite, no taxonomy bridge.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("name_fa", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
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
        sa.CheckConstraint(
            "status IN ('draft','active','retired')",
            name="ck_product_types_status",
        ),
    )
    op.create_index("ix_product_types_code", "product_types", ["code"], unique=True)
    op.create_index("ix_product_types_slug", "product_types", ["slug"], unique=True)
    op.create_index("ix_product_types_status", "product_types", ["status"])

    # Nullable ADD COLUMN is metadata-only on modern Postgres for plain NULL default.
    op.add_column(
        "products",
        sa.Column("product_type_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_products_product_type_id",
        "products",
        ["product_type_id"],
    )
    # Omit ondelete → PostgreSQL NO ACTION / RESTRICT semantics (matches category_id / brand_id).
    op.create_foreign_key(
        "fk_products_product_type_id_product_types",
        "products",
        "product_types",
        ["product_type_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_products_product_type_id_product_types",
        "products",
        type_="foreignkey",
    )
    op.drop_index("ix_products_product_type_id", table_name="products")
    op.drop_column("products", "product_type_id")

    op.drop_index("ix_product_types_status", table_name="product_types")
    op.drop_index("ix_product_types_slug", table_name="product_types")
    op.drop_index("ix_product_types_code", table_name="product_types")
    op.drop_table("product_types")
