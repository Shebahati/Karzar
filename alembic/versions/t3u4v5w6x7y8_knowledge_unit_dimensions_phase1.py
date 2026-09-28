"""Prompt 150 — expand Knowledge Unit dimension registry.

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-09-27

Additive CHECK replacement only. Extends knowledge_units.dimension so the
generic Property Dictionary can later register Units for force, velocity,
rotational_speed, time, temperature, and voltage.

No DML. No Unit/Property/PT/Fact rows. No catalog changes.
Downgrade restores the prior five-dimension CHECK and refuses if any row
uses one of the six new dimensions.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "t3u4v5w6x7y8"
down_revision: str | None = "s2t3u4v5w6x7"
branch_labels = None
depends_on = None

_OLD_DIMENSIONS = (
    "length",
    "angle",
    "mass",
    "dimensionless",
    "hardness",
)

_NEW_DIMENSIONS = (
    *_OLD_DIMENSIONS,
    "force",
    "velocity",
    "rotational_speed",
    "time",
    "temperature",
    "voltage",
)

_NEW_ONLY = (
    "force",
    "velocity",
    "rotational_speed",
    "time",
    "temperature",
    "voltage",
)


def _dimension_in_clause(dimensions: tuple[str, ...]) -> str:
    inner = ", ".join(f"'{d}'" for d in dimensions)
    return f"dimension IN ({inner})"


def upgrade() -> None:
    op.drop_constraint(
        "ck_knowledge_units_dimension",
        "knowledge_units",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_units_dimension",
        "knowledge_units",
        _dimension_in_clause(_NEW_DIMENSIONS),
    )


def downgrade() -> None:
    bind = op.get_bind()
    new_list = ", ".join(f"'{d}'" for d in _NEW_ONLY)
    row = bind.execute(
        text(
            "SELECT count(*) FROM knowledge_units "
            f"WHERE dimension IN ({new_list})"
        )
    ).scalar()
    if row and int(row) > 0:
        raise RuntimeError(
            "Refuse downgrade: knowledge_units rows use expanded dimensions "
            f"({', '.join(_NEW_ONLY)}). Remove or reclassify those rows first."
        )

    op.drop_constraint(
        "ck_knowledge_units_dimension",
        "knowledge_units",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_units_dimension",
        "knowledge_units",
        _dimension_in_clause(_OLD_DIMENSIONS),
    )
