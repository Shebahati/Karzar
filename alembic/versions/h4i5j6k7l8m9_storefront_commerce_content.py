"""Storefront alignment: product fields, commerce, CMS, OTP, comments.

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-06-25 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "h4i5j6k7l8m9"
down_revision: Union[str, None] = "g3h4i5j6k7l8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "products",
        sa.Column("original_price", sa.Numeric(precision=15, scale=2), nullable=True),
    )

    op.create_table(
        "product_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.String(length=100), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_verified_buyer", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_comments_product_id", "product_comments", ["product_id"])

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("cover_image", sa.String(length=500), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reading_minutes", sa.Integer(), server_default="5", nullable=False),
        sa.Column("author", sa.String(length=100), server_default="تیم فنی کارزار", nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("related_product_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_articles_slug", "articles", ["slug"], unique=True)

    op.create_table(
        "hero_slides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=500), nullable=True),
        sa.Column("cta_label", sa.String(length=100), nullable=True),
        sa.Column("cta_href", sa.String(length=500), nullable=True),
        sa.Column("image", sa.String(length=500), nullable=False),
        sa.Column("accent", sa.String(length=20), server_default="#C22026", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "contact_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_code", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=15), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contact_submissions_ticket_code", "contact_submissions", ["ticket_code"], unique=True)

    otppurpose = postgresql.ENUM("login", name="otppurpose", create_type=False)
    otppurpose.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=15), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("purpose", otppurpose, server_default="login", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_otp_codes_phone", "otp_codes", ["phone"])

    ordermode = postgresql.ENUM("purchase", "inquiry", name="ordermode", create_type=False)
    ordermode.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracking_code", sa.String(length=32), nullable=False),
        sa.Column("mode", ordermode, nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("estimated_total", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("customer_full_name", sa.String(length=100), nullable=False),
        sa.Column("customer_phone", sa.String(length=15), nullable=False),
        sa.Column("customer_is_guest", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("company_name", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("shipping", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_tracking_code", "orders", ["tracking_code"], unique=True)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_tracking_code", table_name="orders")
    op.drop_table("orders")
    op.execute("DROP TYPE IF EXISTS ordermode")

    op.drop_index("ix_otp_codes_phone", table_name="otp_codes")
    op.drop_table("otp_codes")
    op.execute("DROP TYPE IF EXISTS otppurpose")

    op.drop_index("ix_contact_submissions_ticket_code", table_name="contact_submissions")
    op.drop_table("contact_submissions")
    op.drop_table("hero_slides")
    op.drop_index("ix_articles_slug", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_product_comments_product_id", table_name="product_comments")
    op.drop_table("product_comments")

    op.drop_column("products", "original_price")
    op.drop_column("products", "description")
