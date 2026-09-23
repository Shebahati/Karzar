"""Prompt 65 / Wave Registry PR2 — extend wave status CHECK to include Sealed.

Revision ID: p9q0r1s2t3u4
Revises: o8p9q0r1s2t3
Create Date: 2026-09-23

Additive CHECK replacement only. No data backfill. No other table changes.
Downgrade restores PR1 Draft|Reviewed CHECK (fails if any Sealed rows exist).
"""

from __future__ import annotations

from alembic import op

revision: str = "p9q0r1s2t3u4"
down_revision: str | None = "o8p9q0r1s2t3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_knowledge_waves_status_pr1",
        "knowledge_waves",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_waves_status_pr2",
        "knowledge_waves",
        "status IN ('Draft', 'Reviewed', 'Sealed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_knowledge_waves_status_pr2",
        "knowledge_waves",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_waves_status_pr1",
        "knowledge_waves",
        "status IN ('Draft', 'Reviewed')",
    )
