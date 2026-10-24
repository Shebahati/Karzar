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

async def ensure_execution_store(session: AsyncSession) -> None:
    res = await session.execute(text("SELECT to_regclass('public.ast_catalog_execution_batches')"))
    if res.scalar() is None:
        raise ApplyAbort("ast_catalog_execution_batches_missing_run_alembic_migration")


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


async def committed_update_product_ids(
    session: AsyncSession,
    *,
    master_update_manifest_sha256: str,
) -> set[int]:
    res = await session.execute(
        text(
            """
            SELECT mutation_result
            FROM ast_catalog_execution_batches
            WHERE execution_state IN ('COMMITTED', 'VERIFIED')
              AND cohort = 'update'
              AND (mutation_plan->'metadata'->>'master_update_manifest_sha256') = :master
            """
        ),
        {"master": master_update_manifest_sha256},
    )
    committed: set[int] = set()
    for (mutation_result,) in res.fetchall():
        if not mutation_result:
            continue
        for entry in mutation_result.get("updates") or []:
            pid = entry.get("product_id")
            if pid is not None:
                committed.add(int(pid))
    return committed


async def assert_prior_canary_stages_verified(
    session: AsyncSession,
    *,
    master_update_manifest_sha256: str,
    update_stage: str,
) -> None:
    order = ("stage1", "stage2", "stage3")
    stage = (update_stage or "").strip().lower()
    if stage not in order:
        return
    idx = order.index(stage)
    for prior in order[:idx]:
        res = await session.execute(
            text(
                """
                SELECT batch_id FROM ast_catalog_execution_batches
                WHERE cohort = 'update'
                  AND execution_state = 'VERIFIED'
                  AND post_commit_verified = TRUE
                  AND (mutation_plan->'metadata'->>'master_update_manifest_sha256') = :master
                  AND (mutation_plan->'metadata'->>'update_stage') = :stage
                LIMIT 1
                """
            ),
            {"master": master_update_manifest_sha256, "stage": prior},
        )
        if res.first() is None:
            raise ApplyAbort(f"prior_canary_stage_not_verified:{prior}")


async def assert_update_product_ids_not_committed(
    session: AsyncSession,
    *,
    product_ids: list[int],
    master_update_manifest_sha256: str,
) -> None:
    if not product_ids or not master_update_manifest_sha256:
        return
    committed = await committed_update_product_ids(
        session, master_update_manifest_sha256=master_update_manifest_sha256
    )
    overlap = sorted(committed.intersection(int(pid) for pid in product_ids))
    if overlap:
        raise ApplyAbort(f"update_product_ids_already_committed:{overlap[:20]}")


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
