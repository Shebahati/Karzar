"""Widen environment_identity.plane CHECK for application staging.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-10-13

Adds canonical ``staging`` plane value for application-staging sentinels.
No backfill; live row remains ``plane=live``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None

_PLANE_CHECK = "ck_environment_identity_plane"
_OLD_PLANES = ("live", "catalog_staging", "development")
_NEW_PLANES = ("live", "staging", "catalog_staging", "development")


def _plane_in_sql(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.drop_constraint(_PLANE_CHECK, "environment_identity", type_="check")
    op.create_check_constraint(
        _PLANE_CHECK,
        "environment_identity",
        f"plane IN ({_plane_in_sql(_NEW_PLANES)})",
    )


def downgrade() -> None:
    bind = op.get_bind()
    count = bind.execute(
        sa.text("SELECT COUNT(*) FROM environment_identity WHERE plane = 'staging'")
    ).scalar()
    if count and int(count) > 0:
        raise RuntimeError(
            "Cannot downgrade: environment_identity contains plane='staging' rows. "
            "Remove or relabel them manually before downgrading."
        )
    op.drop_constraint(_PLANE_CHECK, "environment_identity", type_="check")
    op.create_check_constraint(
        _PLANE_CHECK,
        "environment_identity",
        f"plane IN ({_plane_in_sql(_OLD_PLANES)})",
    )
