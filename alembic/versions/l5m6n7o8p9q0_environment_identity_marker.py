"""Add environment_identity sentinel table.

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-09-21

Durable non-secret marker so catalog writers can fail closed when a process
claims ``KARZAR_DATA_PLANE=catalog_staging`` but the connected database is the
CR-011 live plane (historically named ``karzar_staging``).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "l5m6n7o8p9q0"
down_revision = "k4l5m6n7o8p9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "environment_identity",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("plane", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "id = 1",
            name="ck_environment_identity_singleton",
        ),
        sa.CheckConstraint(
            "plane IN ('live', 'catalog_staging', 'development')",
            name="ck_environment_identity_plane",
        ),
    )
    # Default marker for existing databases after upgrade: treat as live until
    # an explicit catalog-staging bootstrap overwrites the row. CR-011 live DBs
    # that later receive this migration remain labeled live.
    op.execute(
        sa.text(
            "INSERT INTO environment_identity (id, plane, label, notes) "
            "VALUES (1, 'live', 'legacy-or-unmarked', "
            "'Default after migration; catalog-staging bootstrap must set plane=catalog_staging')"
        )
    )


def downgrade() -> None:
    op.drop_table("environment_identity")
