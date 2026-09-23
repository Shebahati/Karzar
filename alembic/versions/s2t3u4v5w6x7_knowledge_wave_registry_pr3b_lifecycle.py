"""Prompt 101 / Wave Registry PR3-B.1 — lifecycle status vocabulary.

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
Create Date: 2026-09-23

Additive CHECK replacement only. Extends knowledge_waves.status for
EvidenceValidated / Publishing / Published / Superseded / Archived so
PR3-B.2 (evidence validate) and PR3-B.3 (publish) can land without
another schema change.

No DML. No Fact/Evidence/Product/JSONB table changes.
Downgrade restores PR3-A CHECK and refuses if any row uses new statuses.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "s2t3u4v5w6x7"
down_revision: str | None = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None

_PR3A_STATUSES = (
    "Draft",
    "Reviewed",
    "Sealed",
    "Executing",
    "Asserted",
    "Failed",
    "Aborted",
)

_PR3B_STATUSES = (
    *_PR3A_STATUSES,
    "EvidenceValidated",
    "Publishing",
    "Published",
    "Superseded",
    "Archived",
)

_NEW_ONLY = (
    "EvidenceValidated",
    "Publishing",
    "Published",
    "Superseded",
    "Archived",
)


def _status_in_clause(statuses: tuple[str, ...]) -> str:
    inner = ", ".join(f"'{s}'" for s in statuses)
    return f"status IN ({inner})"


def upgrade() -> None:
    op.drop_constraint(
        "ck_knowledge_waves_status_pr3",
        "knowledge_waves",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_waves_status_pr3b",
        "knowledge_waves",
        _status_in_clause(_PR3B_STATUSES),
    )


def downgrade() -> None:
    bind = op.get_bind()
    new_list = ", ".join(f"'{s}'" for s in _NEW_ONLY)
    row = bind.execute(
        text(
            f"SELECT count(*) FROM knowledge_waves WHERE status IN ({new_list})"
        )
    ).scalar()
    if row and int(row) > 0:
        raise RuntimeError(
            "Refuse downgrade: knowledge_waves rows use PR3-B statuses "
            f"({', '.join(_NEW_ONLY)}). Archive or migrate those rows first."
        )

    op.drop_constraint(
        "ck_knowledge_waves_status_pr3b",
        "knowledge_waves",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_waves_status_pr3",
        "knowledge_waves",
        _status_in_clause(_PR3A_STATUSES),
    )
