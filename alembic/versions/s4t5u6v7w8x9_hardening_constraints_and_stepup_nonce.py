"""Hardening: DB constraints and single-use step-up tokens

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-07-13 13:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s4t5u6v7w8x9"
down_revision: Union[str, None] = "r3s4t5u6v7w8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "step_up_token_uses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index("ix_step_up_token_uses_jti", "step_up_token_uses", ["jti"], unique=True)
    op.create_index("ix_step_up_token_uses_expires_at", "step_up_token_uses", ["expires_at"], unique=False)

    op.create_check_constraint(
        "ck_products_stock_non_negative",
        "products",
        "stock_quantity >= 0",
    )

    op.create_unique_constraint(
        "uq_orders_payment_authority",
        "orders",
        ["payment_authority"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_orders_payment_authority", "orders", type_="unique")
    op.drop_constraint("ck_products_stock_non_negative", "products", type_="check")

    op.drop_index("ix_step_up_token_uses_expires_at", table_name="step_up_token_uses")
    op.drop_index("ix_step_up_token_uses_jti", table_name="step_up_token_uses")
    op.drop_table("step_up_token_uses")
