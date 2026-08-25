"""SEP payment gateway: verifying status, RefNum uniqueness, retry fields.

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
Create Date: 2026-08-25 17:30:00.000000

- Unique partial index on orders.payment_ref_id (non-null) for double-spend defense
- Widen payment_authority / payment_status / ledger status for SEP tokens and new states
- Add verify-retry columns on orders
- Add sanitized provider audit columns on payment_transactions

Does not delete or rewrite existing payment_ref_id duplicates; upgrade fails with a
clear message if non-null duplicates exist so ops can remediate manually.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "g8h9i0j1k2l3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

_REF_UNIQUE_INDEX = "uq_orders_payment_ref_id_not_null"
_VERIFY_NEXT_INDEX = "ix_orders_payment_next_verify_at"


def upgrade() -> None:
    conn = op.get_bind()
    dupes = conn.execute(
        sa.text(
            """
            SELECT payment_ref_id, COUNT(*) AS cnt
            FROM orders
            WHERE payment_ref_id IS NOT NULL
            GROUP BY payment_ref_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if dupes:
        sample = ", ".join(f"{row[0]!r}×{row[1]}" for row in dupes[:5])
        raise RuntimeError(
            "Cannot create unique partial index on orders.payment_ref_id: "
            f"duplicate non-null values exist ({sample}). "
            "Remediate duplicates manually, then re-run this migration."
        )

    op.alter_column(
        "orders",
        "payment_authority",
        existing_type=sa.String(length=64),
        type_=sa.String(length=256),
        existing_nullable=True,
    )
    op.alter_column(
        "orders",
        "payment_status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
    )

    op.add_column(
        "orders",
        sa.Column("payment_callback_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("payment_verify_deadline", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "payment_verify_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column("payment_next_verify_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("payment_last_error", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("payment_authority_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("payment_provider_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_index(
        _VERIFY_NEXT_INDEX,
        "orders",
        ["payment_next_verify_at"],
        unique=False,
    )
    op.execute(
        sa.text(
            f"""
            CREATE UNIQUE INDEX {_REF_UNIQUE_INDEX}
            ON orders (payment_ref_id)
            WHERE payment_ref_id IS NOT NULL
            """
        )
    )

    op.alter_column(
        "payment_transactions",
        "authority",
        existing_type=sa.String(length=64),
        type_=sa.String(length=256),
        existing_nullable=True,
    )
    op.alter_column(
        "payment_transactions",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.add_column(
        "payment_transactions",
        sa.Column("provider_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("result_code", sa.Integer(), nullable=True),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("trace_no", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("rrn", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("merchant_reference", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_transactions", "merchant_reference")
    op.drop_column("payment_transactions", "rrn")
    op.drop_column("payment_transactions", "trace_no")
    op.drop_column("payment_transactions", "result_code")
    op.drop_column("payment_transactions", "provider_data")
    op.alter_column(
        "payment_transactions",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.alter_column(
        "payment_transactions",
        "authority",
        existing_type=sa.String(length=256),
        type_=sa.String(length=64),
        existing_nullable=True,
    )

    op.execute(sa.text(f"DROP INDEX IF EXISTS {_REF_UNIQUE_INDEX}"))
    op.drop_index(_VERIFY_NEXT_INDEX, table_name="orders")

    op.drop_column("orders", "payment_provider_data")
    op.drop_column("orders", "payment_authority_expires_at")
    op.drop_column("orders", "payment_last_error")
    op.drop_column("orders", "payment_next_verify_at")
    op.drop_column("orders", "payment_verify_attempts")
    op.drop_column("orders", "payment_verify_deadline")
    op.drop_column("orders", "payment_callback_received_at")

    op.alter_column(
        "orders",
        "payment_status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.alter_column(
        "orders",
        "payment_authority",
        existing_type=sa.String(length=256),
        type_=sa.String(length=64),
        existing_nullable=True,
    )
