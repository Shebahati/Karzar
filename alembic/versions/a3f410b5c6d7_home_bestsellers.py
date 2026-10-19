"""Create durable ordered homepage bestseller selection (empty until owner publishes).

Revision ID: a3f410b5c6d7
Revises: c1d2e3f4a5b6 + u6v7w8x9y0z1 (existing parallel Alembic heads)
"""
from collections.abc import Sequence
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "a3f410b5c6d7"
down_revision: tuple[str, str] = ("c1d2e3f4a5b6", "u6v7w8x9y0z1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "home_bestseller_selection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_ids", postgresql.JSONB(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_home_bestseller_singleton"),
        sa.CheckConstraint("revision > 0", name="ck_home_bestseller_revision"),
    )
    # No automatic seeding: never silently label newest products as bestsellers.


def downgrade() -> None:
    op.drop_table("home_bestseller_selection")
