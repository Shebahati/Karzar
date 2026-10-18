"""Persist owner-curated homepage bestseller IDs in the live database.

Revision ID: c2d3e4f5a6b7
Revises: c1d2e3f4a5b6
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table(
        "home_bestseller_selections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_ids", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_home_bestseller_singleton"),
        sa.CheckConstraint("revision >= 0", name="ck_home_bestseller_revision"),
    )

def downgrade() -> None:
    op.drop_table("home_bestseller_selections")
