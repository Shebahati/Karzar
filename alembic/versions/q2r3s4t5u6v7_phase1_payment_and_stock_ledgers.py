"""Phase 1 payment and stock audit ledgers

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-07-12 14:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "q2r3s4t5u6v7"
down_revision: Union[str, None] = "p1q2r3s4t5u6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("gateway", sa.String(length=32), nullable=False),
        sa.Column("authority", sa.String(length=64), nullable=True),
        sa.Column("ref_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
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
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_transactions_order_id", "payment_transactions", ["order_id"])
    op.create_index("ix_payment_transactions_authority", "payment_transactions", ["authority"])
    op.create_index("ix_payment_transactions_created_at", "payment_transactions", ["created_at"])

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity_change", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("reference_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_index("ix_stock_movements_reference_id", "stock_movements", ["reference_id"])
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_stock_movements_created_at", table_name="stock_movements")
    op.drop_index("ix_stock_movements_reference_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_product_id", table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index("ix_payment_transactions_created_at", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_authority", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_order_id", table_name="payment_transactions")
    op.drop_table("payment_transactions")
