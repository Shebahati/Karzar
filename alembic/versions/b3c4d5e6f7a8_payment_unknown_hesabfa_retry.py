"""Payment UNKNOWN status + Hesabfa invoice retry columns.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-25 23:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PAYMENT_STATUSES = ("unpaid", "paid", "failed", "refunded", "unknown")
_TX_STATUSES = ("initiated", "verified", "failed", "refunded", "unknown")


def upgrade() -> None:
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_payment_status_lifecycle")
    payments = ", ".join(f"'{s}'" for s in _PAYMENT_STATUSES)
    op.execute(
        f"""
        ALTER TABLE orders
        ADD CONSTRAINT ck_orders_payment_status_lifecycle
        CHECK (payment_status IN ({payments}))
        """
    )

    op.execute(
        "ALTER TABLE payment_transactions DROP CONSTRAINT IF EXISTS ck_payment_transactions_status_lifecycle"
    )
    txs = ", ".join(f"'{s}'" for s in _TX_STATUSES)
    op.execute(
        f"""
        ALTER TABLE payment_transactions
        ADD CONSTRAINT ck_payment_transactions_status_lifecycle
        CHECK (status IN ({txs}))
        """
    )

    op.add_column(
        "hesabfa_invoice_records",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "hesabfa_invoice_records",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_hesabfa_invoice_records_next_attempt",
        "hesabfa_invoice_records",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_hesabfa_invoice_records_next_attempt", table_name="hesabfa_invoice_records")
    op.drop_column("hesabfa_invoice_records", "next_attempt_at")
    op.drop_column("hesabfa_invoice_records", "attempt_count")

    op.execute(
        "ALTER TABLE payment_transactions DROP CONSTRAINT IF EXISTS ck_payment_transactions_status_lifecycle"
    )
    op.execute(
        """
        ALTER TABLE payment_transactions
        ADD CONSTRAINT ck_payment_transactions_status_lifecycle
        CHECK (status IN ('initiated', 'verified', 'failed', 'refunded'))
        """
    )
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_payment_status_lifecycle")
    op.execute(
        """
        ALTER TABLE orders
        ADD CONSTRAINT ck_orders_payment_status_lifecycle
        CHECK (payment_status IN ('unpaid', 'paid', 'failed', 'refunded'))
        """
    )
