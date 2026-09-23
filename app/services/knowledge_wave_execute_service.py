"""Knowledge Wave Registry PR3-A — execute / resume orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge_wave import (
    KnowledgeWave,
    KnowledgeWaveRun,
    KnowledgeWaveRunItem,
)
from app.db.models.product_type import ProductType, ProductTypeDefinition
from app.db.models.user import User
from app.services import knowledge_batch_assert_service as batch_service
from app.services.audit_service import record_audit
from app.services.knowledge_wave_service import (
    WAVE_STATUS_ASSERTED,
    WAVE_STATUS_DRAFT,
    WAVE_STATUS_EXECUTING,
    WAVE_STATUS_FAILED,
    WAVE_STATUS_REVIEWED,
    WAVE_STATUS_SEALED,
    build_canonical_manifest_payload,
    compute_manifest_sha256,
)

RUN_TYPE_ASSERT = "assert"
RUN_CREATED = "created"
RUN_RUNNING = "running"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"
RUN_ABORTED = "aborted"

ITEM_PENDING = "pending"
ITEM_RUNNING = "running"
ITEM_SUCCESS = "success"
ITEM_FAILED = "failed"
ITEM_SKIPPED = "skipped"


def resolve_wave_policy(wave: KnowledgeWave) -> dict[str, Any]:
    """Frozen policy view from sealed wave columns + policy_json."""
    policy = wave.policy_json if isinstance(wave.policy_json, dict) else {}
    pins = policy.get("environment_pins") or {}
    rules = policy.get("validation_rules") or {}
    allowlist = sorted(
        (
            {"product_id": int(p.product_id), "sku_snapshot": str(p.sku_snapshot)}
            for p in wave.products
        ),
        key=lambda row: (row["product_id"], row["sku_snapshot"]),
    )
    return {
        "wave_id": wave.wave_id,
        "wave_pk": wave.id,
        "manifest_sha256": wave.manifest_sha256,
        "brand": wave.brand,
        "product_type_id": wave.product_type_id,
        "definition_id": wave.definition_id,
        "environment_pins": {
            "plane": str(pins.get("plane") or "live"),
            "alembic": str(pins.get("alembic") or batch_service.REQUIRED_ALEMBIC),
            "freeze_required": bool(pins.get("freeze_required", True)),
        },
        "validation_rules": {
            "resume_existing_facts": bool(rules.get("resume_existing_facts", True)),
            "resume_existing_assignment": bool(
                rules.get("resume_existing_assignment", True)
            ),
            "resume_from_failed": bool(rules.get("resume_from_failed", True)),
            "allow_partial_execute": bool(rules.get("allow_partial_execute", False)),
        },
        "allowlist": allowlist,
    }


async def _get_wave_by_wave_id(db: AsyncSession, wave_id: str) -> KnowledgeWave:
    wid = (wave_id or "").strip()
    wave = (
        await db.execute(
            select(KnowledgeWave)
            .options(selectinload(KnowledgeWave.products))
            .where(KnowledgeWave.wave_id == wid)
        )
    ).scalar_one_or_none()
    if wave is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Wave not found",
            details=[{"field": "wave_id", "message": "not found"}],
        )
    return wave


async def _get_run_or_404(db: AsyncSession, run_id: int) -> KnowledgeWaveRun:
    run = (
        await db.execute(
            select(KnowledgeWaveRun)
            .options(selectinload(KnowledgeWaveRun.items))
            .where(KnowledgeWaveRun.id == run_id)
        )
    ).scalar_one_or_none()
    if run is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Wave run not found",
            details=[{"field": "run_id", "message": "not found"}],
        )
    return run


async def _verify_manifest_sha(db: AsyncSession, wave: KnowledgeWave) -> None:
    if not wave.manifest_sha256:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Wave has no manifest_sha256",
            details=[{"field": "manifest_sha256", "message": "missing"}],
        )
    pt = await db.get(ProductType, wave.product_type_id)
    definition = await db.get(ProductTypeDefinition, wave.definition_id)
    if pt is None or definition is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Wave product_type/definition missing",
            details=[{"field": "definition_id", "message": "unresolvable"}],
        )
    payload = build_canonical_manifest_payload(
        wave_id=wave.wave_id,
        brand=wave.brand,
        product_type=pt,
        definition=definition,
        policy_json=wave.policy_json if isinstance(wave.policy_json, dict) else {},
        products=list(wave.products),
    )
    digest = compute_manifest_sha256(payload)
    if digest != wave.manifest_sha256:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="manifest_sha256 drift vs canonical payload",
            details=[{"field": "manifest_sha256", "message": "mismatch"}],
        )


async def _assert_no_running_run(db: AsyncSession, wave_pk: int) -> None:
    existing = (
        await db.execute(
            select(KnowledgeWaveRun.id).where(
                KnowledgeWaveRun.wave_id == wave_pk,
                KnowledgeWaveRun.status == RUN_RUNNING,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Wave already has a running assert run",
            details=[{"field": "run_id", "message": str(existing)}],
        )


def _progress(items: list[KnowledgeWaveRunItem]) -> dict[str, int]:
    counts = {
        "total": len(items),
        "pending": 0,
        "running": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }
    for item in items:
        key = item.status if item.status in counts else None
        if key:
            counts[key] += 1
    return counts


def _unit_map(
    sku_units: list[dict[str, Any]],
) -> dict[tuple[int, str], dict[str, Any]]:
    out: dict[tuple[int, str], dict[str, Any]] = {}
    for unit in sku_units:
        key = (int(unit["product_id"]), str(unit["sku"]).strip())
        out[key] = unit
    return out


def _validate_units_against_allowlist(
    *,
    policy: dict[str, Any],
    sku_units: list[dict[str, Any]],
) -> None:
    allow = {
        (int(row["product_id"]), str(row["sku_snapshot"]))
        for row in policy["allowlist"]
    }
    if not allow:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Wave allowlist is empty",
            details=[{"field": "products", "message": "empty"}],
        )
    unit_keys = set()
    for unit in sku_units:
        key = (int(unit["product_id"]), str(unit["sku"]).strip())
        if key not in allow:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="SKU unit not in sealed allowlist",
                details=[
                    {
                        "field": "sku_units",
                        "message": f"product_id={key[0]} sku={key[1]}",
                    }
                ],
            )
        unit_keys.add(key)
    if not policy["validation_rules"]["allow_partial_execute"] and unit_keys != allow:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="sku_units must cover full sealed allowlist",
            details=[{"field": "sku_units", "message": "partial execute forbidden"}],
        )


async def execute_run_item(
    db: AsyncSession,
    *,
    wave: KnowledgeWave,
    run: KnowledgeWaveRun,
    item: KnowledgeWaveRunItem,
    sku_unit: dict[str, Any],
    policy: dict[str, Any],
    actor: User,
    change_reason: str,
) -> dict[str, Any]:
    """Execute one allowlist SKU via kb-batch-assert (no commit)."""
    now = datetime.now(UTC)
    item.status = ITEM_RUNNING
    item.started_at = now
    item.error_message = None
    await db.flush()

    result = await batch_service.execute_kb_batch_assert(
        db,
        product_id=int(sku_unit["product_id"]),
        manifest_sha256=str(wave.manifest_sha256 or ""),
        sku=str(sku_unit["sku"]),
        product_type_id=int(policy["product_type_id"]),
        definition_id=int(policy["definition_id"]),
        facts=list(sku_unit.get("facts") or []),
        evidence_links=list(sku_unit.get("evidence_links") or []),
        change_reason=change_reason,
        actor=actor,
        wave_context=policy,
    )
    resumed = bool(result.get("resumed"))
    item.status = ITEM_SKIPPED if resumed else ITEM_SUCCESS
    item.resumed = resumed
    item.result_json = {
        "fact_ids": [f["id"] for f in result.get("facts") or []],
        "evidence_link_ids": [e["id"] for e in result.get("evidence_links") or []],
        "specifications_fingerprint": result.get("specifications_fingerprint"),
        "resumed": resumed,
    }
    item.finished_at = datetime.now(UTC)
    await db.flush()

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.item.success",
        entity_type="knowledge_wave_run_item",
        entity_id=item.id,
        details={
            "run_id": run.id,
            "product_id": item.product_id,
            "sku": item.sku_snapshot,
            "resumed": resumed,
            "fact_ids": item.result_json.get("fact_ids"),
        },
    )
    return result


async def _finalize_success(
    db: AsyncSession,
    *,
    wave: KnowledgeWave,
    run: KnowledgeWaveRun,
    actor: User,
) -> None:
    run.status = RUN_COMPLETED
    run.finished_at = datetime.now(UTC)
    run.stop_reason = None
    wave.status = WAVE_STATUS_ASSERTED
    await db.flush()
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.run.complete",
        entity_type="knowledge_wave_run",
        entity_id=run.id,
        details={
            "wave_id": wave.wave_id,
            "wave_run_id": run.id,
            "progress": _progress(list(run.items)),
            "manifest_sha256": wave.manifest_sha256,
        },
    )


async def _finalize_failure(
    db: AsyncSession,
    *,
    wave: KnowledgeWave,
    run: KnowledgeWaveRun,
    actor: User,
    stop_reason: str,
    failed_item: KnowledgeWaveRunItem | None = None,
) -> None:
    run.status = RUN_FAILED
    run.finished_at = datetime.now(UTC)
    run.stop_reason = stop_reason
    wave.status = WAVE_STATUS_FAILED
    await db.flush()
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.run.fail",
        entity_type="knowledge_wave_run",
        entity_id=run.id,
        details={
            "wave_id": wave.wave_id,
            "wave_run_id": run.id,
            "stop_reason": stop_reason,
            "failed_product_id": failed_item.product_id if failed_item else None,
            "progress": _progress(list(run.items)),
        },
    )


def _serialize_execute_result(
    *,
    wave: KnowledgeWave,
    run: KnowledgeWaveRun,
) -> dict[str, Any]:
    items = sorted(run.items, key=lambda i: (i.product_id or 0, i.id))
    return {
        "wave_run_id": run.id,
        "wave_id": wave.wave_id,
        "wave_pk": wave.id,
        "wave_status": wave.status,
        "status": run.status,
        "manifest_sha256": wave.manifest_sha256,
        "created_items": [
            {
                "run_item_id": i.id,
                "product_id": i.product_id,
                "sku_snapshot": i.sku_snapshot,
                "status": i.status,
            }
            for i in items
        ],
        "progress": _progress(items),
        "stop_reason": run.stop_reason,
    }


async def execute_wave(
    db: AsyncSession,
    *,
    wave_id: str,
    sku_units: list[dict[str, Any]],
    change_reason: str,
    actor: User,
    stop_on_first_failure: bool = True,
) -> dict[str, Any]:
    """Sealed → Executing → Asserted|Failed via kb-batch-assert per SKU."""
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )
    if not sku_units:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="sku_units is required",
            details=[{"field": "sku_units", "message": "required"}],
        )

    wave = await _get_wave_by_wave_id(db, wave_id)
    if wave.status in (WAVE_STATUS_DRAFT, WAVE_STATUS_REVIEWED):
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only Sealed waves may execute",
            details=[{"field": "status", "message": wave.status}],
        )
    if wave.status != WAVE_STATUS_SEALED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only Sealed waves may execute (use resume for Failed)",
            details=[{"field": "status", "message": wave.status}],
        )

    await _verify_manifest_sha(db, wave)
    policy = resolve_wave_policy(wave)
    # Environment pins — same sentinels as kb-batch-assert wave path
    await batch_service.assert_environment_gates(db, pins=policy["environment_pins"])
    await _assert_no_running_run(db, wave.id)
    _validate_units_against_allowlist(policy=policy, sku_units=sku_units)

    units = _unit_map(sku_units)
    now = datetime.now(UTC)
    run = KnowledgeWaveRun(
        wave_id=wave.id,
        run_type=RUN_TYPE_ASSERT,
        status=RUN_CREATED,
        created_by=actor.id,
        manifest_sha256_snapshot=wave.manifest_sha256,
        request_snapshot_json={"sku_units": sku_units, "change_reason": reason},
        started_at=None,
        finished_at=None,
        stop_reason=None,
    )
    db.add(run)
    await db.flush()

    # Snapshot ledger from sealed wave_products (immutable execution set)
    for row in sorted(wave.products, key=lambda p: (p.product_id, p.sku_snapshot)):
        db.add(
            KnowledgeWaveRunItem(
                run_id=run.id,
                product_id=row.product_id,
                sku_snapshot=row.sku_snapshot,
                status=ITEM_PENDING,
                resumed=False,
            )
        )
    await db.flush()

    wave.status = WAVE_STATUS_EXECUTING
    run.status = RUN_RUNNING
    run.started_at = now
    await db.flush()

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.execute",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "wave_pk": wave.id,
            "wave_run_id": run.id,
            "manifest_sha256": wave.manifest_sha256,
            "sku_count": len(wave.products),
            "change_reason": reason,
        },
    )
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.run.start",
        entity_type="knowledge_wave_run",
        entity_id=run.id,
        details={
            "wave_run_id": run.id,
            "wave_id": wave.wave_id,
            "run_type": RUN_TYPE_ASSERT,
        },
    )
    await db.commit()

    # Reload after commit for SKU loop
    run_id = run.id
    run = await _get_run_or_404(db, run_id)
    wave = await _get_wave_by_wave_id(db, wave_id)
    policy = resolve_wave_policy(wave)
    items = sorted(run.items, key=lambda i: (i.product_id or 0, i.id))

    for item in items:
        item_id = item.id
        key = (int(item.product_id or 0), str(item.sku_snapshot or ""))
        sku_unit = units.get(key)
        if sku_unit is None:
            continue
        try:
            await execute_run_item(
                db,
                wave=wave,
                run=run,
                item=item,
                sku_unit=sku_unit,
                policy=policy,
                actor=actor,
                change_reason=reason,
            )
            await db.commit()
        except Exception as exc:  # noqa: BLE001 — SKU failure → ledger + stop
            await db.rollback()
            run = await _get_run_or_404(db, run_id)
            wave = await _get_wave_by_wave_id(db, wave_id)
            failed = next(i for i in run.items if i.id == item_id)
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict):
                err_msg = str(detail.get("message") or detail)[:2000]
            else:
                err_msg = str(detail or exc)[:2000]
            failed.status = ITEM_FAILED
            failed.error_message = err_msg
            failed.finished_at = datetime.now(UTC)
            await record_audit(
                db,
                actor_user_id=actor.id,
                action="wave.item.fail",
                entity_type="knowledge_wave_run_item",
                entity_id=failed.id,
                details={
                    "run_id": run.id,
                    "product_id": failed.product_id,
                    "sku": failed.sku_snapshot,
                    "error_message": failed.error_message,
                },
            )
            if stop_on_first_failure:
                await _finalize_failure(
                    db,
                    wave=wave,
                    run=run,
                    actor=actor,
                    stop_reason=failed.error_message or "sku failed",
                    failed_item=failed,
                )
                await db.commit()
                run = await _get_run_or_404(db, run_id)
                wave = await _get_wave_by_wave_id(db, wave_id)
                return _serialize_execute_result(wave=wave, run=run)
            await db.commit()

    run = await _get_run_or_404(db, run_id)
    wave = await _get_wave_by_wave_id(db, wave_id)
    if any(i.status == ITEM_FAILED for i in run.items):
        await _finalize_failure(
            db,
            wave=wave,
            run=run,
            actor=actor,
            stop_reason="one or more SKUs failed",
        )
    else:
        await _finalize_success(db, wave=wave, run=run, actor=actor)
    await db.commit()
    run = await _get_run_or_404(db, run_id)
    wave = await _get_wave_by_wave_id(db, wave_id)
    return _serialize_execute_result(wave=wave, run=run)


async def get_wave_run(db: AsyncSession, run_id: int) -> dict[str, Any]:
    run = await _get_run_or_404(db, run_id)
    wave = (
        await db.execute(
            select(KnowledgeWave).where(KnowledgeWave.id == run.wave_id)
        )
    ).scalar_one()
    items = sorted(run.items, key=lambda i: (i.product_id or 0, i.id))
    return {
        "run_id": run.id,
        "run_type": run.run_type,
        "status": run.status,
        "created_by": run.created_by,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "manifest_sha256_snapshot": run.manifest_sha256_snapshot,
        "stop_reason": run.stop_reason,
        "wave": {
            "id": wave.id,
            "wave_id": wave.wave_id,
            "status": wave.status,
            "manifest_sha256": wave.manifest_sha256,
            "brand": wave.brand,
            "product_type_id": wave.product_type_id,
            "definition_id": wave.definition_id,
        },
        "progress": _progress(items),
        "items": [
            {
                "run_item_id": i.id,
                "product_id": i.product_id,
                "sku_snapshot": i.sku_snapshot,
                "status": i.status,
                "resumed": bool(i.resumed),
                "error_message": i.error_message,
                "result": i.result_json,
                "started_at": i.started_at,
                "finished_at": i.finished_at,
            }
            for i in items
        ],
    }


async def resume_wave_run(
    db: AsyncSession,
    *,
    run_id: int,
    change_reason: str,
    actor: User,
    sku_units: list[dict[str, Any]] | None = None,
    stop_on_first_failure: bool = True,
) -> dict[str, Any]:
    """Resume from a failed run: new run_id, skip prior successes, no Fact dupes."""
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )

    source = await _get_run_or_404(db, run_id)
    if source.status != RUN_FAILED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only failed runs may be resumed",
            details=[{"field": "status", "message": source.status}],
        )

    wave = await _get_wave_by_wave_id(
        db,
        (
            await db.execute(
                select(KnowledgeWave.wave_id).where(KnowledgeWave.id == source.wave_id)
            )
        ).scalar_one(),
    )
    # Reload with products
    wave = await _get_wave_by_wave_id(db, wave.wave_id)

    policy = resolve_wave_policy(wave)
    if wave.status not in (WAVE_STATUS_FAILED, WAVE_STATUS_SEALED):
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Wave must be Failed or Sealed to resume",
            details=[{"field": "status", "message": wave.status}],
        )
    if not policy["validation_rules"]["resume_from_failed"] and wave.status == WAVE_STATUS_FAILED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="resume_from_failed is disabled by wave policy",
            details=[{"field": "validation_rules.resume_from_failed", "message": "false"}],
        )

    await _verify_manifest_sha(db, wave)
    if source.manifest_sha256_snapshot != wave.manifest_sha256:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Source run manifest snapshot does not match wave",
            details=[{"field": "manifest_sha256", "message": "changed"}],
        )
    await batch_service.assert_environment_gates(db, pins=policy["environment_pins"])
    await _assert_no_running_run(db, wave.id)

    if sku_units is None:
        snap = source.request_snapshot_json or {}
        sku_units = list(snap.get("sku_units") or [])
    if not sku_units:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="sku_units required when source run has no request snapshot",
            details=[{"field": "sku_units", "message": "required"}],
        )
    _validate_units_against_allowlist(policy=policy, sku_units=sku_units)

    # Prior successes for this wave+manifest across assert runs
    prior_success_products: set[int] = set()
    prior_runs = (
        await db.execute(
            select(KnowledgeWaveRun)
            .options(selectinload(KnowledgeWaveRun.items))
            .where(
                KnowledgeWaveRun.wave_id == wave.id,
                KnowledgeWaveRun.run_type == RUN_TYPE_ASSERT,
                KnowledgeWaveRun.manifest_sha256_snapshot == wave.manifest_sha256,
            )
        )
    ).scalars().all()
    for pr in prior_runs:
        for it in pr.items:
            if it.status in (ITEM_SUCCESS, ITEM_SKIPPED) and it.product_id is not None:
                prior_success_products.add(int(it.product_id))

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.run.resume",
        entity_type="knowledge_wave_run",
        entity_id=source.id,
        details={
            "source_run_id": source.id,
            "wave_id": wave.wave_id,
            "change_reason": reason,
        },
    )

    # Force Sealed-equivalent execute path: temporarily set Failed→Sealed surface
    # by calling internal loop. Reuse execute_wave mechanics via Sealed status.
    if wave.status == WAVE_STATUS_FAILED:
        wave.status = WAVE_STATUS_SEALED
        await db.flush()
        await db.commit()

    # execute_wave requires Sealed — call it
    return await execute_wave(
        db,
        wave_id=wave.wave_id,
        sku_units=sku_units,
        change_reason=reason,
        actor=actor,
        stop_on_first_failure=stop_on_first_failure,
    )
