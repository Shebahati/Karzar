"""Add products.is_available; migrate from stock_quantity.

Revision ID: x9y0z1a2b3c4
Revises: w8x9y0z1a2b3
Create Date: 2026-07-25 14:40:00.000000

Site no longer stores sellable warehouse counts. Availability is a boolean;
warehouse quantities live only in Hesabfa.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "x9y0z1a2b3c4"
down_revision = "w8x9y0z1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    # Historical: treat prior positive stock as available, zero/negative as not.
    op.execute(
        sa.text(
            "UPDATE products SET is_available = (COALESCE(stock_quantity, 0) > 0)"
        )
    )


def downgrade() -> None:
    op.drop_column("products", "is_available")
