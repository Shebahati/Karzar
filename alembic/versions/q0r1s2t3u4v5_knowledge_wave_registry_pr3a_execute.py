"""Prompt 68 / Wave Registry PR3-A — status vocabulary + run ledger columns.

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-09-23

Additive CHECK replacements + nullable ledger columns only.
No DML. No Fact/Evidence/Product table changes.
Downgrade restores PR2 CHECKs and drops new columns.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "q0r1s2t3u4v5"
down_revision: str | None = "p9q0r1s2t3u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_knowledge_waves_status_pr2",
        "knowledge_waves",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_waves_status_pr3",
        "knowledge_waves",
        "status IN ("
        "'Draft', 'Reviewed', 'Sealed', 'Executing', 'Asserted', 'Failed', 'Aborted'"
        ")",
    )

    op.drop_constraint(
        "ck_knowledge_wave_runs_status",
        "knowledge_wave_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_wave_runs_status_pr3",
        "knowledge_wave_runs",
        "status IN ('created', 'running', 'completed', 'failed', 'aborted')",
    )

    op.add_column(
        "knowledge_wave_runs",
        sa.Column("manifest_sha256_snapshot", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "knowledge_wave_runs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "knowledge_wave_runs",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "knowledge_wave_runs",
        sa.Column("stop_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "knowledge_wave_runs",
        sa.Column(
            "request_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.drop_constraint(
        "ck_knowledge_wave_run_items_status",
        "knowledge_wave_run_items",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_wave_run_items_status_pr3",
        "knowledge_wave_run_items",
        "status IN ('pending', 'running', 'success', 'failed', 'skipped')",
    )
    op.add_column(
        "knowledge_wave_run_items",
        sa.Column(
            "resumed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "knowledge_wave_run_items",
        sa.Column(
            "result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "knowledge_wave_run_items",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "knowledge_wave_run_items",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_wave_run_items", "finished_at")
    op.drop_column("knowledge_wave_run_items", "started_at")
    op.drop_column("knowledge_wave_run_items", "result_json")
    op.drop_column("knowledge_wave_run_items", "resumed")
    op.drop_constraint(
        "ck_knowledge_wave_run_items_status_pr3",
        "knowledge_wave_run_items",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_wave_run_items_status",
        "knowledge_wave_run_items",
        "status IN ('pending','ok','failed','skipped')",
    )

    op.drop_column("knowledge_wave_runs", "request_snapshot_json")
    op.drop_column("knowledge_wave_runs", "stop_reason")
    op.drop_column("knowledge_wave_runs", "finished_at")
    op.drop_column("knowledge_wave_runs", "started_at")
    op.drop_column("knowledge_wave_runs", "manifest_sha256_snapshot")
    op.drop_constraint(
        "ck_knowledge_wave_runs_status_pr3",
        "knowledge_wave_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_wave_runs_status",
        "knowledge_wave_runs",
        "status IN ('running','succeeded','failed','aborted')",
    )

    op.drop_constraint(
        "ck_knowledge_waves_status_pr3",
        "knowledge_waves",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_waves_status_pr2",
        "knowledge_waves",
        "status IN ('Draft', 'Reviewed', 'Sealed')",
    )
