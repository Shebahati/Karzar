"""Prompt 71 — add missing Base updated_at columns on wave tables.

Revision ID: r1s2t3u4v5w6
Revises: q0r1s2t3u4v5
Create Date: 2026-09-23

Additive columns only. Aligns ORM Base timestamp convention with schema
for knowledge_wave_products (CI failure) and sibling run ledger tables
that inherit the same Base.updated_at mapping.

No DML. No Fact/Evidence/Product catalog table changes.
Downgrade drops only these columns.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "r1s2t3u4v5w6"
down_revision: str | None = "q0r1s2t3u4v5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_wave_products",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "knowledge_wave_runs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "knowledge_wave_run_items",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("knowledge_wave_run_items", "updated_at")
    op.drop_column("knowledge_wave_runs", "updated_at")
    op.drop_column("knowledge_wave_products", "updated_at")
