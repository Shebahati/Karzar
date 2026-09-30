"""Phase 2A — add nullable products.manufacturer_code (no backfill).

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-09-30

Adds first-class OEM/manufacturer identity column on products.

Hard rules for this revision:
- nullable only (existing rows stay NULL)
- no DML / no backfill / no SKU copy
- no UNIQUE constraint (known brand+code collisions exist)
- non-unique indexes only, for exact/brand+code lookup

Canonical invariant (documented in PHASE-2A-MANUFACTURER-IDENTITY.md):
non-null manufacturer_code means verified canonical OEM identity.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "u4v5w6x7y8z9"
down_revision: str | None = "t3u4v5w6x7y8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("manufacturer_code", sa.String(length=255), nullable=True),
    )
    # Exact OEM lookup (collision detection / Phase 2C readiness). unique=false.
    op.create_index(
        "ix_products_manufacturer_code",
        "products",
        ["manufacturer_code"],
        unique=False,
    )
    # Brand-scoped OEM lookup / collision audit. unique=false.
    op.create_index(
        "ix_products_brand_id_manufacturer_code",
        "products",
        ["brand_id", "manufacturer_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_products_brand_id_manufacturer_code", table_name="products")
    op.drop_index("ix_products_manufacturer_code", table_name="products")
    op.drop_column("products", "manufacturer_code")
