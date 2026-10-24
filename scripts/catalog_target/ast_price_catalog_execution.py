"""AST APPLY execution: SQLAlchemy transaction, journal state machine, post-commit verify."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from catalog_target.ast_price_catalog_apply import (
    ApplyAbort,
    ApplyResult,
    CreatePlanRow,
    StaleGuardResult,
    UpdatePlanRow,
    create_products_ast_batch,
    parse_price,
    verify_update_stale_guard,
    write_journal,
)
from catalog_target.ast_price_catalog_execution_store import (
    assert_no_blocking_unknown_batches,
    ensure_execution_store,
    assert_update_product_ids_not_committed,
    insert_prepared_batch,
    mark_batch_committed,
    mark_batch_verified,
)


def async_sqlalchemy_database_url(url: str) -> str:
    raw = (url or "").strip()
    if raw.startswith("postgresql+asyncpg://") or raw.startswith("postgres+asyncpg://"):
        return raw
    if raw.startswith("postgresql://"):
        return "postgresql+asyncpg://" + raw[len("postgresql://") :]
    if raw.startswith("postgres://"):
        return "postgresql+asyncpg://" + raw[len("postgres://") :]
    return raw

ApplyCohort = Literal["update", "create", "both"]


class ExecutionState(StrEnum):
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"
    VERIFIED = "VERIFIED"
    VERIFY_FAILED = "VERIFY_FAILED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass
class PostCommitVerifyReport:
    ok: bool
    mismatches: list[dict[str, str]]


def _journal_paths(journal_dir: Path, batch_id: str) -> dict[str, Path]:
    base = journal_dir / f"AST_APPLY_{batch_id}"
    return {
        "prepared": base.with_suffix(".prepared.json"),
        "committed": base.with_suffix(".json"),
        "recovery": base.with_suffix(".recovery.json"),
    }


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    write_journal(path, payload)


async def _fetch_live_updates(session: AsyncSession, update_rows: list[UpdatePlanRow]) -> dict[int, dict[str, str]]:
    if not update_rows:
        return {}
    ids = [r.product_id for r in update_rows]
    result = await session.execute(
        text(
            "SELECT id, sku, base_price::text FROM products WHERE id = ANY(:ids) AND deleted_at IS NULL FOR UPDATE"
        ),
        {"ids": ids},
    )
    live: dict[int, dict[str, str]] = {}
    for row in result.fetchall():
        live[int(row[0])] = {"sku": row[1], "base_price": row[2]}
    return live


async def _apply_updates_async(
    session: AsyncSession,
    update_rows: list[UpdatePlanRow],
) -> list[dict[str, Any]]:
    sql = text(
        """
        UPDATE products
        SET base_price = :new_price, updated_at = NOW()
        WHERE id = :pid AND sku = :sku AND deleted_at IS NULL
          AND base_price IS NOT DISTINCT FROM :expected_price
        """
    )
    journal: list[dict[str, Any]] = []
    for row in update_rows:
        result = await session.execute(
            sql,
            {
                "new_price": row.proposed_price,
                "pid": row.product_id,
                "sku": row.sku,
                "expected_price": row.expected_current_price,
            },
        )
        if result.rowcount != 1:
            raise ApplyAbort(f"update_rowcount_mismatch:product_id={row.product_id}:rowcount={result.rowcount}")
        journal.append(
            {
                "product_id": row.product_id,
                "sku": row.sku,
                "before_base_price": str(row.expected_current_price or ""),
                "after_base_price": str(row.proposed_price or ""),
            }
        )
    return journal


def _create_journal_row(row: CreatePlanRow, product_id: int) -> dict[str, Any]:
    return {
        "product_id": product_id,
        "sku": row.sku,
        "brand_id": row.brand_id,
        "category_id": row.category_id,
        "base_price": str(row.base_price or ""),
        "is_available": False,
        "name": row.name,
    }


async def verify_committed_cohort(
    database_url: str,
    *,
    update_journal: list[dict[str, Any]],
    create_journal: list[dict[str, Any]],
    create_plan: list[CreatePlanRow],
) -> PostCommitVerifyReport:
    engine = create_async_engine(async_sqlalchemy_database_url(database_url), pool_pre_ping=True)
    mismatches: list[dict[str, str]] = []
    plan_by_sku = {r.sku: r for r in create_plan}
    try:
        async with engine.connect() as conn:
            if update_journal:
                ids = [int(r["product_id"]) for r in update_journal]
                res = await conn.execute(
                    text(
                        "SELECT id, sku, base_price::text FROM products WHERE id = ANY(:ids) AND deleted_at IS NULL"
                    ),
                    {"ids": ids},
                )
                live = {int(r[0]): {"sku": r[1], "base_price": r[2]} for r in res.fetchall()}
                for entry in update_journal:
                    pid = int(entry["product_id"])
                    row = live.get(pid)
                    if row is None:
                        mismatches.append({"scope": "update", "product_id": str(pid), "reason": "missing"})
                        continue
                    if row["sku"] != entry["sku"]:
                        mismatches.append({"scope": "update", "product_id": str(pid), "reason": "sku_mismatch"})
                        continue
                    if parse_price(row["base_price"]) != parse_price(str(entry["after_base_price"])):
                        mismatches.append({"scope": "update", "product_id": str(pid), "reason": "price_mismatch"})

            if create_journal:
                ids = [int(r["product_id"]) for r in create_journal]
                res = await conn.execute(
                    text(
                        """
                        SELECT id, sku, brand_id, category_id, base_price::text, is_available
                        FROM products WHERE id = ANY(:ids) AND deleted_at IS NULL
                        """
                    ),
                    {"ids": ids},
                )
                live = {
                    int(r[0]): {
                        "sku": r[1],
                        "brand_id": int(r[2]),
                        "category_id": int(r[3]),
                        "base_price": r[4],
                        "is_available": bool(r[5]),
                    }
                    for r in res.fetchall()
                }
                seen_sku: set[str] = set()
                for entry in create_journal:
                    pid = int(entry["product_id"])
                    sku = entry["sku"]
                    if sku in seen_sku:
                        mismatches.append({"scope": "create", "sku": sku, "reason": "duplicate_create_sku"})
                    seen_sku.add(sku)
                    row = live.get(pid)
                    plan = plan_by_sku.get(sku)
                    if row is None:
                        mismatches.append({"scope": "create", "product_id": str(pid), "reason": "missing"})
                        continue
                    if plan is None:
                        mismatches.append({"scope": "create", "sku": sku, "reason": "unplanned_sku"})
                        continue
                    if row["sku"] != sku:
                        mismatches.append({"scope": "create", "product_id": str(pid), "reason": "sku_mismatch"})
                    if row["brand_id"] != plan.brand_id:
                        mismatches.append({"scope": "create", "product_id": str(pid), "reason": "brand_mismatch"})
                    if row["category_id"] != plan.category_id:
                        mismatches.append({"scope": "create", "product_id": str(pid), "reason": "category_mismatch"})
                    if row["is_available"] is not False:
                        mismatches.append({"scope": "create", "product_id": str(pid), "reason": "is_available_not_false"})
                    if parse_price(row["base_price"]) != parse_price(str(plan.base_price or "")):
                        mismatches.append({"scope": "create", "product_id": str(pid), "reason": "price_mismatch"})
    finally:
        await engine.dispose()
    return PostCommitVerifyReport(ok=not mismatches, mismatches=mismatches)


async def execute_ast_apply_async(
    database_url: str,
    update_rows: list[UpdatePlanRow],
    create_rows: list[CreatePlanRow],
    *,
    cohort: ApplyCohort,
    dry_run: bool,
    batch_id: str,
    journal_dir: Path,
    metadata: dict[str, Any],
) -> ApplyResult:
    scoped_updates = update_rows if cohort in {"update", "both"} else []
    scoped_creates = create_rows if cohort in {"create", "both"} else []

    paths = _journal_paths(journal_dir, batch_id)
    journal_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        payload = {
            "batch_id": batch_id,
            "execution_state": ExecutionState.PREPARED,
            "committed": False,
            "verified": False,
            "cohort": cohort,
            "metadata": metadata,
            "updates_planned": len(scoped_updates),
            "creates_planned": len(scoped_creates),
        }
        _write_state(paths["committed"], payload)
        return ApplyResult(
            mode="dry_run",
            committed=False,
            updates_written=0,
            creates_written=0,
            batch_id=batch_id,
            journal_path=str(paths["committed"]),
            production_apply_executed=False,
        )

    engine = create_async_engine(async_sqlalchemy_database_url(database_url), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    guard: StaleGuardResult | None = None
    update_journal: list[dict[str, Any]] = []
    create_journal: list[dict[str, Any]] = []

    planned_updates = [
        {
            "product_id": r.product_id,
            "sku": r.sku,
            "expected_current_price": str(r.expected_current_price or ""),
            "proposed_price": str(r.proposed_price or ""),
        }
        for r in scoped_updates
    ]
    planned_creates = [
        {
            "sku": r.sku,
            "brand_id": r.brand_id,
            "category_id": r.category_id,
            "base_price": str(r.base_price or ""),
            "name": r.name,
        }
        for r in scoped_creates
    ]
    prepared_payload: dict[str, Any] = {
        "batch_id": batch_id,
        "execution_state": ExecutionState.PREPARED,
        "committed": False,
        "verified": False,
        "cohort": cohort,
        "metadata": metadata,
        "updates_planned": len(scoped_updates),
        "creates_planned": len(scoped_creates),
        "planned_updates": planned_updates,
        "planned_creates": planned_creates,
    }
    _write_state(paths["prepared"], prepared_payload)

    try:
        async with session_factory() as session:
            async with session.begin():
                await ensure_execution_store(session)
                await assert_no_blocking_unknown_batches(session)
                master_sha = str(metadata.get("master_update_manifest_sha256") or "")
                if scoped_updates and master_sha:
                    await assert_update_product_ids_not_committed(
                        session,
                        product_ids=[r.product_id for r in scoped_updates],
                        master_update_manifest_sha256=master_sha,
                    )
                await insert_prepared_batch(
                    session,
                    batch_id=batch_id,
                    cohort=cohort,
                    updates=planned_updates,
                    creates=planned_creates,
                    metadata=metadata,
                )
                if scoped_updates:
                    live = await _fetch_live_updates(session, scoped_updates)
                    guard = verify_update_stale_guard(scoped_updates, live)
                    if not guard.ok:
                        raise ApplyAbort("BLOCKED_STALE_GUARD")
                    update_journal = await _apply_updates_async(session, scoped_updates)
                if scoped_creates:
                    created_ids = await create_products_ast_batch(session, scoped_creates)
                    create_journal = [
                        _create_journal_row(row, pid)
                        for row, pid in zip(scoped_creates, created_ids, strict=True)
                    ]
                await mark_batch_committed(
                    session,
                    batch_id=batch_id,
                    update_journal=update_journal,
                    create_journal=create_journal,
                )
    except ApplyAbort:
        failed = {**prepared_payload, "execution_state": ExecutionState.FAILED, "committed": False}
        _write_state(paths["recovery"], failed)
        await engine.dispose()
        raise
    except Exception:
        unknown = {**prepared_payload, "execution_state": ExecutionState.UNKNOWN, "committed": False}
        _write_state(paths["recovery"], unknown)
        await engine.dispose()
        raise

    committed_payload: dict[str, Any] = {
        **prepared_payload,
        "execution_state": ExecutionState.COMMITTED,
        "committed": True,
        "verified": False,
        "updates": update_journal,
        "creates": create_journal,
        "stale_guard": guard.__dict__ if guard else None,
    }
    _write_state(paths["committed"], committed_payload)

    verify = await verify_committed_cohort(
        database_url,
        update_journal=update_journal,
        create_journal=create_journal,
        create_plan=scoped_creates,
    )
    if not verify.ok:
        verify_failed = {
            **committed_payload,
            "execution_state": ExecutionState.VERIFY_FAILED,
            "verified": False,
            "verify_mismatches": verify.mismatches,
            "recovery_note": "Database commit succeeded; do not claim rollback. Use recovery procedure.",
        }
        _write_state(paths["recovery"], verify_failed)
        await engine.dispose()
        return ApplyResult(
            mode="apply",
            committed=True,
            updates_written=len(update_journal),
            creates_written=len(create_journal),
            batch_id=batch_id,
            stale_guard=guard,
            journal_path=str(paths["recovery"]),
            aborted_reason="POST_COMMIT_VERIFY_FAILED",
            production_apply_executed=False,
        )

    verified_payload = {
        **committed_payload,
        "execution_state": ExecutionState.VERIFIED,
        "verified": True,
    }
    _write_state(paths["committed"], verified_payload)
    async with session_factory() as session:
        async with session.begin():
            await ensure_execution_store(session)
            await mark_batch_verified(session, batch_id=batch_id)
    await engine.dispose()
    return ApplyResult(
        mode="apply",
        committed=True,
        updates_written=len(update_journal),
        creates_written=len(create_journal),
        batch_id=batch_id,
        stale_guard=guard,
        journal_path=str(paths["committed"]),
        production_apply_executed=True,
    )
