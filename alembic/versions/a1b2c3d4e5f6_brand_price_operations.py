"""Brand bulk price operations (Feature D).

Revision ID: a1b2c3d4e5f6
Revises: a3f410b5c6d7
Create Date: 2026-10-24 18:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "a3f410b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

brandpriceadjustmentmode = postgresql.ENUM(
    "percent",
    "fixed",
    name="brandpriceadjustmentmode",
    create_type=False,
)
brandpriceadjustmentdirection = postgresql.ENUM(
    "increase",
    "decrease",
    name="brandpriceadjustmentdirection",
    create_type=False,
)
brandpriceoperationstatus = postgresql.ENUM(
    "confirmed",
    "applied",
    "failed",
    "cancelled",
    name="brandpriceoperationstatus",
    create_type=False,
)
brandpricelinestatus = postgresql.ENUM(
    "pending",
    "applied",
    "skipped",
    "conflict",
    name="brandpricelinestatus",
    create_type=False,
)


def upgrade() -> None:
    brandpriceadjustmentmode.create(op.get_bind(), checkfirst=True)
    brandpriceadjustmentdirection.create(op.get_bind(), checkfirst=True)
    brandpriceoperationstatus.create(op.get_bind(), checkfirst=True)
    brandpricelinestatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "brand_price_operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("status", brandpriceoperationstatus, nullable=False),
        sa.Column("adjustment_mode", brandpriceadjustmentmode, nullable=False),
        sa.Column("adjustment_direction", brandpriceadjustmentdirection, nullable=False),
        sa.Column("adjustment_amount", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("catalog_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("apply_error", sa.Text(), nullable=True),
        sa.Column("audit_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brand_price_operations_brand_id", "brand_price_operations", ["brand_id"], unique=False)
    op.create_index("ix_brand_price_operations_status", "brand_price_operations", ["status"], unique=False)
    op.create_index("ix_brand_price_operations_actor_user_id", "brand_price_operations", ["actor_user_id"], unique=False)

    op.create_table(
        "brand_price_operation_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_snapshot", sa.String(length=50), nullable=False),
        sa.Column("old_base_price", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("new_base_price", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("original_price_snapshot", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("line_status", brandpricelinestatus, nullable=False),
        sa.Column("conflict_reason", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["operation_id"], ["brand_price_operations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation_id", "product_id", name="uq_brand_price_op_lines_op_product"),
    )
    op.create_index("ix_brand_price_operation_lines_product_id", "brand_price_operation_lines", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_brand_price_operation_lines_product_id", table_name="brand_price_operation_lines")
    op.drop_table("brand_price_operation_lines")
    op.drop_index("ix_brand_price_operations_actor_user_id", table_name="brand_price_operations")
    op.drop_index("ix_brand_price_operations_status", table_name="brand_price_operations")
    op.drop_index("ix_brand_price_operations_brand_id", table_name="brand_price_operations")
    op.drop_table("brand_price_operations")
    brandpricelinestatus.drop(op.get_bind(), checkfirst=True)
    brandpriceoperationstatus.drop(op.get_bind(), checkfirst=True)
    brandpriceadjustmentdirection.drop(op.get_bind(), checkfirst=True)
    brandpriceadjustmentmode.drop(op.get_bind(), checkfirst=True)
