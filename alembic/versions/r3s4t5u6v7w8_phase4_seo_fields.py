"""Phase 4 SEO fields for catalog entities

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-07-13 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r3s4t5u6v7w8"
down_revision: Union[str, None] = "q2r3s4t5u6v7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_slugs(table: str, prefix: str) -> None:
    conn = op.get_bind()
    if table == "products":
        rows = conn.execute(sa.text("SELECT id, sku FROM products")).fetchall()
    else:
        rows = conn.execute(sa.text(f"SELECT id, name FROM {table}")).fetchall()

    used: set[str] = set()
    for row in rows:
        row_id = row[0]
        if table == "products":
            sku = (row[1] or "").strip().lower()
            base = sku or f"{prefix}-{row_id}"
        else:
            name = (row[1] or "").strip().lower().replace(" ", "-")
            base = name or f"{prefix}-{row_id}"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used.add(candidate)
        max_len = 255 if table == "products" else 200
        conn.execute(
            sa.text(f"UPDATE {table} SET slug = :slug WHERE id = :id"),
            {"slug": candidate[:max_len], "id": row_id},
        )


def upgrade() -> None:
    for table, length in (("categories", 200), ("brands", 200), ("products", 255)):
        op.add_column(table, sa.Column("slug", sa.String(length=length), nullable=True))
        op.add_column(table, sa.Column("meta_title", sa.String(length=255), nullable=True))
        op.add_column(table, sa.Column("meta_description", sa.String(length=500), nullable=True))

    _backfill_slugs("categories", "category")
    _backfill_slugs("brands", "brand")
    _backfill_slugs("products", "product")

    for table in ("categories", "brands", "products"):
        op.alter_column(table, "slug", nullable=False)
        op.create_index(op.f(f"ix_{table}_slug"), table, ["slug"], unique=True)


def downgrade() -> None:
    for table in ("products", "brands", "categories"):
        op.drop_index(op.f(f"ix_{table}_slug"), table_name=table)
        op.drop_column(table, "meta_description")
        op.drop_column(table, "meta_title")
        op.drop_column(table, "slug")
