"""Order notification dispatch dedup (#450)

Revision ID: c1d2e3f4a5b6
Revises: u4v5w6x7y8z9
Create Date: 2026-10-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "u4v5w6x7y8z9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_notification_dispatch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="1", nullable=False),
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
        sa.UniqueConstraint(
            "order_id",
            "channel",
            name="uq_order_notification_dispatch_order_channel",
        ),
    )
    op.create_index(
        "ix_order_notification_dispatch_order_id",
        "order_notification_dispatch",
        ["order_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_order_notification_dispatch_order_id",
        table_name="order_notification_dispatch",
    )
    op.drop_table("order_notification_dispatch")
