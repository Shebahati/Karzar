"""Add order line product snapshots (name/sku/tax).

Revision ID: z1a2b3c4d5e6
Revises: y0z1a2b3c4d5
Create Date: 2026-07-25 20:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "z1a2b3c4d5e6"
down_revision: str | None = "y0z1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("product_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("product_sku", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column(
            "tax_percent",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.execute(
        """
        UPDATE order_items AS oi
        SET
            product_name = COALESCE(p.name, 'محصول حذف‌شده'),
            product_sku = COALESCE(p.sku, ''),
            tax_percent = COALESCE(p.tax_percent, 0)
        FROM products AS p
        WHERE oi.product_id = p.id
        """
    )
    op.execute(
        """
        UPDATE order_items
        SET product_name = 'محصول حذف‌شده', product_sku = ''
        WHERE product_name IS NULL
        """
    )
    op.alter_column("order_items", "product_name", nullable=False)
    op.alter_column("order_items", "product_sku", nullable=False)


def downgrade() -> None:
    op.drop_column("order_items", "tax_percent")
    op.drop_column("order_items", "product_sku")
    op.drop_column("order_items", "product_name")
