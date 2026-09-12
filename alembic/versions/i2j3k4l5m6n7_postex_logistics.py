"""Add package logistics fields, shipping quotes, and first-class shipments.

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2026-09-10 06:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i2j3k4l5m6n7"
down_revision: str | None = "h1i2j3k4l5m6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Package dims: NULL = unknown. Zero is invalid (package_builder rejects ≤0).
    op.add_column(
        "products",
        sa.Column("package_length_cm", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("package_width_cm", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("package_height_cm", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    # Hazard + class: NULL = UNKNOWN / not reviewed. Do not fabricate false/parcel.
    op.add_column(
        "products",
        sa.Column("shipping_is_fragile", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("shipping_is_liquid", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("shipping_class", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        "ck_products_package_length_positive",
        "products",
        "package_length_cm IS NULL OR package_length_cm > 0",
    )
    op.create_check_constraint(
        "ck_products_package_width_positive",
        "products",
        "package_width_cm IS NULL OR package_width_cm > 0",
    )
    op.create_check_constraint(
        "ck_products_package_height_positive",
        "products",
        "package_height_cm IS NULL OR package_height_cm > 0",
    )
    # NULL passes CHECK in PostgreSQL; only non-null values must be parcel|freight_only.
    op.create_check_constraint(
        "ck_products_shipping_class",
        "products",
        "shipping_class IS NULL OR shipping_class IN ('parcel', 'freight_only')",
    )

    op.add_column("orders", sa.Column("shipping_provider", sa.String(length=32), nullable=True))
    op.add_column("orders", sa.Column("shipping_quote_id", sa.Integer(), nullable=True))
    op.add_column(
        "orders",
        sa.Column("shipping_customer_cost", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "shipping_provider_quoted_cost", sa.Numeric(precision=15, scale=2), nullable=True
        ),
    )
    op.add_column("orders", sa.Column("shipping_carrier_code", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("shipping_service_code", sa.String(length=64), nullable=True))

    op.create_table(
        "shipping_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("destination_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("cart_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("destination_location_code", sa.Integer(), nullable=False),
        sa.Column("carrier_code", sa.String(length=64), nullable=False),
        sa.Column("service_code", sa.String(length=64), nullable=False),
        sa.Column("service_name", sa.String(length=255), nullable=False),
        sa.Column("provider_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("provider_currency", sa.String(length=8), nullable=False),
        sa.Column("provider_amount_toman", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("customer_amount_toman", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("pickup_amount_toman", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("package_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_provider_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("consumed_order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("token", name="uq_shipping_quotes_token"),
    )
    op.create_index("ix_shipping_quotes_user_id", "shipping_quotes", ["user_id"])
    op.create_index("ix_shipping_quotes_group_id", "shipping_quotes", ["group_id"])
    op.create_index("ix_shipping_quotes_expires_at", "shipping_quotes", ["expires_at"])

    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column(
            "order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("quote_id", sa.Integer(), sa.ForeignKey("shipping_quotes.id"), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("carrier_code", sa.String(length=64), nullable=True),
        sa.Column("service_code", sa.String(length=64), nullable=True),
        sa.Column("service_name", sa.String(length=255), nullable=True),
        sa.Column("provider_parcel_no", sa.String(length=64), nullable=True),
        sa.Column("tracking_code", sa.String(length=64), nullable=True),
        sa.Column("package_length_cm", sa.Integer(), nullable=True),
        sa.Column("package_width_cm", sa.Integer(), nullable=True),
        sa.Column("package_height_cm", sa.Integer(), nullable=True),
        sa.Column("package_weight_grams", sa.Integer(), nullable=True),
        sa.Column("declared_value_irr", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("provider_quoted_cost", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("provider_actual_cost", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("customer_shipping_cost", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("ready_to_accept", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("booking_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("booking_next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_tracking_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.String(length=500), nullable=True),
        sa.Column("provider_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("public_id", name="uq_shipments_public_id"),
    )
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"])
    op.create_index("ix_shipments_status", "shipments", ["status"])
    op.create_index(
        "ix_shipments_booking_next_attempt_at", "shipments", ["booking_next_attempt_at"]
    )
    op.create_index("ix_shipments_tracking_sync_at", "shipments", ["last_tracking_sync_at"])
    op.create_index(
        "uq_shipments_provider_parcel_no",
        "shipments",
        ["provider", "provider_parcel_no"],
        unique=True,
        postgresql_where=sa.text("provider_parcel_no IS NOT NULL"),
    )
    op.create_index(
        "uq_shipments_provider_tracking_code",
        "shipments",
        ["provider", "tracking_code"],
        unique=True,
        postgresql_where=sa.text("tracking_code IS NOT NULL"),
    )

    op.create_table(
        "shipment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "shipment_id",
            sa.Integer(),
            sa.ForeignKey("shipments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_status", sa.String(length=128), nullable=True),
        sa.Column("provider_code", sa.String(length=64), nullable=True),
        sa.Column("provider_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("shipment_id", "dedupe_key", name="uq_shipment_events_dedupe"),
    )
    op.create_index("ix_shipment_events_shipment_id", "shipment_events", ["shipment_id"])


def downgrade() -> None:
    """Destructive if quote/shipment rows exist.

    Operational rollback is POSTEX_ENABLED=false — do not treat Alembic downgrade
    as a safe production rollback after logistics data exists.
    """
    op.drop_table("shipment_events")
    op.drop_index("uq_shipments_provider_tracking_code", table_name="shipments")
    op.drop_index("uq_shipments_provider_parcel_no", table_name="shipments")
    op.drop_table("shipments")
    op.drop_table("shipping_quotes")
    op.drop_column("orders", "shipping_service_code")
    op.drop_column("orders", "shipping_carrier_code")
    op.drop_column("orders", "shipping_provider_quoted_cost")
    op.drop_column("orders", "shipping_customer_cost")
    op.drop_column("orders", "shipping_quote_id")
    op.drop_column("orders", "shipping_provider")
    # Destructive if quote/shipment rows exist. Operational rollback is POSTEX_ENABLED=false;
    # do not treat Alembic downgrade as a safe production rollback after logistics data exists.
    op.drop_constraint("ck_products_shipping_class", "products", type_="check")
    op.drop_constraint("ck_products_package_height_positive", "products", type_="check")
    op.drop_constraint("ck_products_package_width_positive", "products", type_="check")
    op.drop_constraint("ck_products_package_length_positive", "products", type_="check")
    op.drop_column("products", "shipping_class")
    op.drop_column("products", "shipping_is_liquid")
    op.drop_column("products", "shipping_is_fragile")
    op.drop_column("products", "package_height_cm")
    op.drop_column("products", "package_width_cm")
    op.drop_column("products", "package_length_cm")
