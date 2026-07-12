"""P1 contract fields: orders, users, categories, order status history

Revision ID: l8m9n0o1p2q3
Revises: k7l8m9n0o1p2
Create Date: 2026-07-12 12:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l8m9n0o1p2q3"
down_revision: Union[str, None] = "k7l8m9n0o1p2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("icon", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("postal_tracking_code", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("delivery_eta", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "orders",
        sa.Column("invoice", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("category", sa.String(length=50), nullable=True))
    op.add_column(
        "users",
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )

    op.create_table(
        "order_status_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=20), nullable=False, server_default="system"),
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
    op.create_index("ix_order_status_events_order_id", "order_status_events", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_status_events_order_id", table_name="order_status_events")
    op.drop_table("order_status_events")
    op.drop_column("users", "tags")
    op.drop_column("users", "category")
    op.drop_column("users", "note")
    op.drop_column("users", "email")
    op.drop_column("orders", "invoice")
    op.drop_column("orders", "delivery_eta")
    op.drop_column("orders", "postal_tracking_code")
    op.drop_column("categories", "icon")
