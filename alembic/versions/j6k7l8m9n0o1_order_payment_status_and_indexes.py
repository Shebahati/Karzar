"""Add order payment_status, canonical status codes, and order indexes.

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-07-09 15:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j6k7l8m9n0o1"
down_revision: Union[str, None] = "i5j6k7l8m9n0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Map legacy Persian status text to canonical English codes.
_LEGACY_STATUS_MAP = {
    "در انتظار پرداخت": "pending_payment",
    "در حال بررسی استعلام": "inquiry_review",
    "پرداخت شده": "paid",
    "در حال آماده‌سازی": "processing",
    "ارسال شده": "shipped",
    "تحویل داده شده": "delivered",
    "لغو شده": "cancelled",
}


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "payment_status",
            sa.String(length=20),
            nullable=False,
            server_default="unpaid",
        ),
    )

    # Convert any pre-existing Persian status labels to canonical codes.
    for legacy, canonical in _LEGACY_STATUS_MAP.items():
        op.execute(
            sa.text("UPDATE orders SET status = :canonical WHERE status = :legacy").bindparams(
                canonical=canonical, legacy=legacy
            )
        )
    # Mark already-paid legacy orders accordingly.
    op.execute(
        "UPDATE orders SET payment_status = 'paid' "
        "WHERE status IN ('paid', 'processing', 'shipped', 'delivered')"
    )

    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_index("ix_orders_status", "orders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_column("orders", "payment_status")
