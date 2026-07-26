"""Add megamenu_nav_groups and seed from current nav-groups.ts matchers.

Revision ID: y0z1a2b3c4d5
Revises: x9y0z1a2b3c4
Create Date: 2026-07-25 16:00:00.000000
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "y0z1a2b3c4d5"
down_revision: str | None = "x9y0z1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "megamenu_nav_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("highlight", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "root_category_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_megamenu_nav_groups_slug"),
    )
    op.create_index("ix_megamenu_nav_groups_slug", "megamenu_nav_groups", ["slug"])

    # Seed from locked IA (same matchers as Storefront nav-groups.ts).
    from app.services.nav_groups_seed import (
        DEFAULT_NAV_GROUP_SEEDS,
        resolve_root_ids_for_matchers,
    )

    conn = op.get_bind()
    roots_rows = conn.execute(
        sa.text("SELECT id, name, slug FROM categories WHERE parent_id IS NULL ORDER BY id")
    ).fetchall()
    roots = [(int(r[0]), str(r[1]), str(r[2] or "")) for r in roots_rows]
    assigned: set[int] = set()

    for seed in DEFAULT_NAV_GROUP_SEEDS:
        root_ids = resolve_root_ids_for_matchers(
            roots,
            list(seed["matchers"]),
            assigned=assigned,
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO megamenu_nav_groups
                    (slug, label, sort_order, is_enabled, highlight, root_category_ids)
                VALUES
                    (:slug, :label, :sort_order, true, :highlight, CAST(:root_ids AS jsonb))
                """
            ),
            {
                "slug": seed["slug"],
                "label": seed["label"],
                "sort_order": seed["sort_order"],
                "highlight": bool(seed["highlight"]),
                "root_ids": json.dumps(root_ids),
            },
        )


def downgrade() -> None:
    op.drop_index("ix_megamenu_nav_groups_slug", table_name="megamenu_nav_groups")
    op.drop_table("megamenu_nav_groups")
