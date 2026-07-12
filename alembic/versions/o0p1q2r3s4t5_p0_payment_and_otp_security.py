"""P0 payment fields and OTP code hashing

Revision ID: o0p1q2r3s4t5
Revises: m9n0o1p2q3r4
Create Date: 2026-07-12 13:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o0p1q2r3s4t5"
down_revision: Union[str, None] = "m9n0o1p2q3r4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("payment_authority", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("payment_ref_id", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("payment_refund_id", sa.String(length=64), nullable=True))
    op.create_index("ix_orders_payment_authority", "orders", ["payment_authority"], unique=False)

    # Existing OTP rows are invalidated; new codes are stored hashed in `code`.
    op.execute("DELETE FROM otp_codes")


def downgrade() -> None:
    op.drop_index("ix_orders_payment_authority", table_name="orders")
    op.drop_column("orders", "payment_refund_id")
    op.drop_column("orders", "payment_ref_id")
    op.drop_column("orders", "payment_authority")
