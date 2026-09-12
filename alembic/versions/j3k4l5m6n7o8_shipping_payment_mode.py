"""Add shipping payment mode + awaiting_packaging parcel measurement fields.

Revision: j3k4l5m6n7o8
Down revision: i2j3k4l5m6n7

Additive only. Legacy rows keep shipping_payment_mode NULL (not receiver_due).
No catalog / product mutation.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "j3k4l5m6n7o8"
down_revision = "i2j3k4l5m6n7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "shipping_payment_mode",
            sa.String(length=32),
            nullable=True,
            comment="sender_prepaid | receiver_due | NULL=legacy/unspecified",
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "shipping_payment_mode",
            sa.String(length=32),
            nullable=True,
            comment="Snapshot at shipment create; not mutable runtime settings",
        ),
    )
    op.add_column(
        "shipments",
        sa.Column("package_is_fragile", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("package_is_liquid", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("package_measured_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("provider_box_type_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("provider_quoted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_orders_shipping_payment_mode",
        "orders",
        "shipping_payment_mode IS NULL OR shipping_payment_mode IN "
        "('sender_prepaid', 'receiver_due')",
    )
    op.create_check_constraint(
        "ck_shipments_shipping_payment_mode",
        "shipments",
        "shipping_payment_mode IS NULL OR shipping_payment_mode IN "
        "('sender_prepaid', 'receiver_due')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_shipments_shipping_payment_mode", "shipments", type_="check")
    op.drop_constraint("ck_orders_shipping_payment_mode", "orders", type_="check")
    op.drop_column("shipments", "provider_quoted_at")
    op.drop_column("shipments", "provider_box_type_id")
    op.drop_column("shipments", "package_measured_at")
    op.drop_column("shipments", "package_is_liquid")
    op.drop_column("shipments", "package_is_fragile")
    op.drop_column("shipments", "shipping_payment_mode")
    op.drop_column("orders", "shipping_payment_mode")
