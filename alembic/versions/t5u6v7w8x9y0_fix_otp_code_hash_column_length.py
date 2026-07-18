"""Fix otp_codes.code length for SHA-256 hashes.

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-07-18 12:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t5u6v7w8x9y0"
down_revision: Union[str, None] = "s4t5u6v7w8x9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "otp_codes",
        "code",
        existing_type=sa.String(length=12),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "otp_codes",
        "code",
        existing_type=sa.String(length=64),
        type_=sa.String(length=12),
        existing_nullable=False,
    )
