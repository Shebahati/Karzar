"""Add Hesabfa category mapping columns (local metadata only while sync disabled).

Revision ID: h1i2j3k4l5m6
Revises: g8h9i0j1k2l3
Create Date: 2026-09-01 09:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h1i2j3k4l5m6"
down_revision: Union[str, None] = "g8h9i0j1k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("hesabfa_category_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("hesabfa_category_override_code", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "hesabfa_category_override_code")
    op.drop_column("categories", "hesabfa_category_code")
