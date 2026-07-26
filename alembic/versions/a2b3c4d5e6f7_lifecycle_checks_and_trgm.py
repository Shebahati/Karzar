"""Lifecycle CHECKs + pg_trgm search indexes.

Revision ID: a2b3c4d5e6f7
Revises: z1a2b3c4d5e6
Create Date: 2026-07-25 21:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "z1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ORDER_STATUSES = (
    "pending_payment",
    "paid",
    "processing",
    "shipped",
    "delivered",
    "cancelled",
    "inquiry_review",
    "inquiry_quoted",
    "inquiry_closed",
)
_PAYMENT_STATUSES = ("unpaid", "paid", "failed", "refunded")
_TX_STATUSES = ("initiated", "verified", "failed", "refunded")
_EVENT_ACTORS = ("system", "admin", "customer", "gateway")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    statuses = ", ".join(f"'{s}'" for s in _ORDER_STATUSES)
    payments = ", ".join(f"'{s}'" for s in _PAYMENT_STATUSES)
    txs = ", ".join(f"'{s}'" for s in _TX_STATUSES)
    actors = ", ".join(f"'{s}'" for s in _EVENT_ACTORS)

    op.execute(
        f"""
        ALTER TABLE orders
        ADD CONSTRAINT ck_orders_status_lifecycle
        CHECK (status IN ({statuses}))
        """
    )
    op.execute(
        f"""
        ALTER TABLE orders
        ADD CONSTRAINT ck_orders_payment_status_lifecycle
        CHECK (payment_status IN ({payments}))
        """
    )
    op.execute(
        f"""
        ALTER TABLE payment_transactions
        ADD CONSTRAINT ck_payment_transactions_status_lifecycle
        CHECK (status IN ({txs}))
        """
    )
    op.execute(
        f"""
        ALTER TABLE order_status_events
        ADD CONSTRAINT ck_order_status_events_status_lifecycle
        CHECK (status IN ({statuses}))
        """
    )
    op.execute(
        f"""
        ALTER TABLE order_status_events
        ADD CONSTRAINT ck_order_status_events_actor
        CHECK (actor IN ({actors}))
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_name_trgm
        ON products USING gin (name gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_sku_trgm
        ON products USING gin (sku gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_brands_name_trgm
        ON brands USING gin (name gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_brands_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_products_sku_trgm")
    op.execute("DROP INDEX IF EXISTS ix_products_name_trgm")
    op.execute("ALTER TABLE order_status_events DROP CONSTRAINT IF EXISTS ck_order_status_events_actor")
    op.execute(
        "ALTER TABLE order_status_events DROP CONSTRAINT IF EXISTS ck_order_status_events_status_lifecycle"
    )
    op.execute(
        "ALTER TABLE payment_transactions DROP CONSTRAINT IF EXISTS ck_payment_transactions_status_lifecycle"
    )
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_payment_status_lifecycle")
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_status_lifecycle")
