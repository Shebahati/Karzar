"""Add category megamenu display flags.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-26
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "megamenu_hidden",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "categories",
        sa.Column(
            "megamenu_as_leaf",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "categories",
        sa.Column("megamenu_bold", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("categories", "megamenu_bold")
    op.drop_column("categories", "megamenu_as_leaf")
    op.drop_column("categories", "megamenu_hidden")
