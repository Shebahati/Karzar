"""Durable AST APPLY execution rows (same DB transaction as mutations)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from catalog_target.sales_wave_apply import ApplyAbort

STATE_PREPARED = "PREPARED"
STATE_COMMITTED = "COMMITTED"
STATE_VERIFIED = "VERIFIED"
STATE_UNKNOWN = "UNKNOWN"

_DDL = """
CREATE TABLE IF NOT EXISTS ast_catalog_execution_batches (
    batch_id TEXT PRIMARY KEY,
    execution_state TEXT NOT NULL,
    cohort TEXT NOT NULL,
    mutation_plan JSONB NOT NULL,
    mutation_result JSONB,
    post_commit_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


async def ensure_execution_store(session: AsyncSession) -> None:
    await session.execute(text(_DDL))


def _plan_payload(
    *,
    batch_id: str,
    cohort: str,
    updates: list[dict[str, Any]],
    creates: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "cohort": cohort,
        "metadata": metadata,
        "planned_updates": updates,
        "planned_creates": creates,
    }


async def insert_prepared_batch(
    session: AsyncSession,
    *,
    batch_id: str,
    cohort: str,
    updates: list[dict[str, Any]],
    creates: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    plan = _plan_payload(
        batch_id=batch_id,
        cohort=cohort,
        updates=updates,
        creates=creates,
        metadata=metadata,
    )
    await session.execute(
        text(
            """
            INSERT INTO ast_catalog_execution_batches
              (batch_id, execution_state, cohort, mutation_plan, mutation_result, post_commit_verified)
            VALUES
              (:batch_id, :state, :cohort, CAST(:plan AS jsonb), NULL, FALSE)
            """
        ),
        {
            "batch_id": batch_id,
            "state": STATE_PREPARED,
            "cohort": cohort,
            "plan": json.dumps(plan),
        },
    )


async def mark_batch_committed(
    session: AsyncSession,
    *,
    batch_id: str,
    update_journal: list[dict[str, Any]],
    create_journal: list[dict[str, Any]],
) -> None:
    result = {
        "updates": update_journal,
        "creates": create_journal,
    }
    await session.execute(
        text(
            """
            UPDATE ast_catalog_execution_batches
            SET execution_state = :state,
                mutation_result = CAST(:result AS jsonb),
                updated_at = NOW()
            WHERE batch_id = :batch_id
            """
        ),
        {
            "batch_id": batch_id,
            "state": STATE_COMMITTED,
            "result": json.dumps(result),
        },
    )


async def mark_batch_verified(session: AsyncSession, *, batch_id: str) -> None:
    await session.execute(
        text(
            """
            UPDATE ast_catalog_execution_batches
            SET execution_state = :state,
                post_commit_verified = TRUE,
                updated_at = NOW()
            WHERE batch_id = :batch_id
            """
        ),
        {"batch_id": batch_id, "state": STATE_VERIFIED},
    )


async def assert_no_blocking_unknown_batches(session: AsyncSession) -> None:
    res = await session.execute(
        text(
            """
            SELECT batch_id, execution_state FROM ast_catalog_execution_batches
            WHERE execution_state IN ('UNKNOWN', 'COMMITTED')
              AND post_commit_verified = FALSE
            LIMIT 5
            """
        )
    )
    rows = res.fetchall()
    if rows:
        ids = ",".join(str(r[0]) for r in rows)
        raise ApplyAbort(f"blocking_unreconciled_execution_batches:{ids}")


async def fetch_batch_state(session: AsyncSession, batch_id: str) -> dict[str, Any] | None:
    res = await session.execute(
        text(
            """
            SELECT execution_state, cohort, mutation_plan, mutation_result, post_commit_verified
            FROM ast_catalog_execution_batches WHERE batch_id = :batch_id
            """
        ),
        {"batch_id": batch_id},
    )
    row = res.fetchone()
    if row is None:
        return None
    return {
        "execution_state": row[0],
        "cohort": row[1],
        "mutation_plan": row[2],
        "mutation_result": row[3],
        "post_commit_verified": row[4],
    }
