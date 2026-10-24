"""Order acquisition attribution snapshot columns.

Revision ID: c3d4e5f6a7b8
Revises: z1a2b3c4d5e6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "z1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "acquisition_source",
            sa.String(length=32),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "orders",
        sa.Column("acquisition_first_touch_source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("acquisition_last_non_direct_source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("acquisition_source_subtype", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("acquisition_method", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("acquisition_landing_path", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("acquisition_campaign", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("acquisition_captured_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_orders_acquisition_source", "orders", ["acquisition_source"])


def downgrade() -> None:
    op.drop_index("ix_orders_acquisition_source", table_name="orders")
    op.drop_column("orders", "acquisition_captured_at")
    op.drop_column("orders", "acquisition_campaign")
    op.drop_column("orders", "acquisition_landing_path")
    op.drop_column("orders", "acquisition_method")
    op.drop_column("orders", "acquisition_source_subtype")
    op.drop_column("orders", "acquisition_last_non_direct_source")
    op.drop_column("orders", "acquisition_first_touch_source")
    op.drop_column("orders", "acquisition_source")
