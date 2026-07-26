"""Add Hesabfa mapping tables for items, contacts, and invoices.

Revision ID: w8x9y0z1a2b3
Revises: v7w8x9y0z1a2
Create Date: 2026-07-25 13:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w8x9y0z1a2b3"
down_revision: Union[str, None] = "v7w8x9y0z1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hesabfa_item_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column("hesabfa_code", sa.String(length=64), nullable=False),
        sa.Column("hesabfa_product_code", sa.String(length=64), nullable=True),
        sa.Column("last_stock", sa.Numeric(12, 2), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("product_id", name="uq_hesabfa_item_product_id"),
        sa.UniqueConstraint("hesabfa_code", name="uq_hesabfa_item_code"),
    )
    op.create_index("ix_hesabfa_item_mappings_sku", "hesabfa_item_mappings", ["sku"])

    op.create_table(
        "hesabfa_contact_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_phone", sa.String(length=15), nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=True),
        sa.Column("hesabfa_code", sa.String(length=64), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("customer_phone", name="uq_hesabfa_contact_phone"),
        sa.UniqueConstraint("hesabfa_code", name="uq_hesabfa_contact_code"),
    )
    op.create_index("ix_hesabfa_contact_mappings_user_id", "hesabfa_contact_mappings", ["user_id"])

    op.create_table(
        "hesabfa_invoice_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hesabfa_number", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload_tag", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_hesabfa_invoice_order_id"),
    )
    op.create_index("ix_hesabfa_invoice_records_status", "hesabfa_invoice_records", ["status"])


def downgrade() -> None:
    op.drop_index("ix_hesabfa_invoice_records_status", table_name="hesabfa_invoice_records")
    op.drop_table("hesabfa_invoice_records")
    op.drop_index("ix_hesabfa_contact_mappings_user_id", table_name="hesabfa_contact_mappings")
    op.drop_table("hesabfa_contact_mappings")
    op.drop_index("ix_hesabfa_item_mappings_sku", table_name="hesabfa_item_mappings")
    op.drop_table("hesabfa_item_mappings")
