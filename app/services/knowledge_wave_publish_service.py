"""PR3-B.3 — Wave publish orchestration (EvidenceValidated → Publishing → Published).

Orchestrates the existing canonical ``knowledge_fact_service.publish_fact``
over the sealed Wave Fact scope. Already-published Facts are safely skipped
(no duplicate revisions). Does not mutate Evidence, Product JSONB, or the
sealed manifest/policy.

Scale: synchronous HTTP loop over the sealed Wave product allowlist only
(not the full catalog), with one commit per product — same boundary as
Wave execute. Suitable for the 12-SKU pilot and small Waves (~50). Larger
Waves (500–5000) should reuse this ledger/service boundary behind a future
background worker; this PR does not add workers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge import KnowledgeFact
from app.db.models.knowledge_wave import (
    KnowledgeWave,
    KnowledgeWaveRun,
    KnowledgeWaveRunItem,
)
from app.db.models.product_type import ProductType, ProductTypeDefinition
from app.db.models.user import User
from app.services import knowledge_batch_assert_service as batch_service
from app.services import knowledge_fact_service as fact_service
from app.services.audit_service import record_audit
from app.services.knowledge_wave_execute_service import resolve_wave_policy
from app.services.knowledge_wave_lifecycle import (
    WAVE_STATUS_EVIDENCE_VALIDATED,
    WAVE_STATUS_FAILED,
    WAVE_STATUS_PUBLISHED,
    WAVE_STATUS_PUBLISHING,
    assert_transition,
)
from app.services.knowledge_wave_service import (
    build_canonical_manifest_payload,
    compute_manifest_sha256,
)

RUN_TYPE_PUBLISH = "publish"
RUN_CREATED = "created"
RUN_RUNNING = "running"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"

ITEM_PENDING = "pending"
ITEM_RUNNING = "running"
ITEM_SUCCESS = "success"
ITEM_FAILED = "failed"
ITEM_SKIPPED = "skipped"

FACT_PUBLISHED = "published"
FACT_ASSERTED = "asserted"
OUTCOME_SKIPPED = "skipped_already_published"
OUTCOME_PUBLISHED = "published"
OUTCOME_FAILED = "failed"


def _conflict(message: str, *, field: str) -> None:
    raise api_error(
        status.HTTP_409_CONFLICT,
        error_code=ErrorCode.CONFLICT,
        message=message,
        details=[{"field": field, "message": message}],
    )


async def _get_wave(db: AsyncSession, wave_id: str) -> KnowledgeWave:
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


async def _verify_manifest_sha(db: AsyncSession, wave: KnowledgeWave) -> str:
    if not wave.manifest_sha256:
        _conflict("manifest_sha256 missing", field="manifest_sha256")
    pt = await db.get(ProductType, wave.product_type_id)
    definition = await db.get(ProductTypeDefinition, wave.definition_id)
    if pt is None or definition is None:
        _conflict("product_type/definition unresolvable", field="definition_id")
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
        _conflict("manifest_sha256 drift vs canonical payload", field="manifest_sha256")
    return digest


async def _assert_no_running_publish(db: AsyncSession, wave_pk: int) -> None:
    running = (
        await db.execute(
            select(KnowledgeWaveRun).where(
                KnowledgeWaveRun.wave_id == wave_pk,
                KnowledgeWaveRun.run_type == RUN_TYPE_PUBLISH,
                KnowledgeWaveRun.status == RUN_RUNNING,
            )
        )
    ).scalar_one_or_none()
    if running is not None:
        _conflict(
            f"publish run {running.id} is already running",
            field="wave_run",
        )


async def _latest_run_is_failed_publish(db: AsyncSession, wave_pk: int) -> bool:
    """True iff the newest wave run is a failed publish (safe publish-resume).

    A prior publish run alone is insufficient: after Failed→Sealed→assert
    re-execute, the latest run is assert and publish must stay closed until
    EvidenceValidated again.
    """
    row = (
        await db.execute(
            select(KnowledgeWaveRun)
            .where(KnowledgeWaveRun.wave_id == wave_pk)
            .order_by(KnowledgeWaveRun.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return (
        row is not None
        and row.run_type == RUN_TYPE_PUBLISH
        and row.status == RUN_FAILED
    )


async def _load_scope_facts(
    db: AsyncSession,
    *,
    product_id: int,
    definition_ids: list[str],
) -> dict[str, list[KnowledgeFact]]:
    facts = (
        await db.execute(
            select(KnowledgeFact).where(
                KnowledgeFact.entity_id == product_id,
                KnowledgeFact.definition_id.in_(definition_ids),
            )
        )
    ).scalars().all()
    by_def: dict[str, list[KnowledgeFact]] = {}
    for fact in facts:
        by_def.setdefault(fact.definition_id, []).append(fact)
    return by_def


def _progress(items: list[KnowledgeWaveRunItem]) -> dict[str, int]:
    counts = {
        "pending": 0,
        "running": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "total": len(items),
    }
    for item in items:
        if item.status in counts:
            counts[item.status] += 1
    return counts


async def _publish_product_facts(
    db: AsyncSession,
    *,
    wave: KnowledgeWave,
    product_id: int,
    sku_snapshot: str,
    actor: User,
    change_reason: str,
) -> dict[str, Any]:
    """Publish or skip Facts for one Wave product. Returns item outcome payload."""
    required = list(batch_service.FACT_DEFINITION_ORDER)
    by_def = await _load_scope_facts(
        db, product_id=product_id, definition_ids=required
    )
    outcomes: list[dict[str, Any]] = []
    newly_published = 0
    skipped = 0

    for def_id in required:
        matches = by_def.get(def_id) or []
        if not matches:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=f"sku={sku_snapshot} missing Fact {def_id}",
                details=[{"field": "facts", "message": f"missing {def_id}"}],
            )
        if len(matches) > 1:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=f"sku={sku_snapshot} duplicate Fact {def_id}",
                details=[{"field": "facts", "message": f"duplicate {def_id}"}],
            )
        fact = matches[0]
        if fact.product_type_definition_id != wave.definition_id:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=f"fact_id={fact.id} product_type_definition_id mismatch",
                details=[{"field": "facts.definition", "message": "mismatch"}],
            )
        if fact.status == FACT_PUBLISHED:
            skipped += 1
            outcomes.append(
                {
                    "fact_id": fact.id,
                    "definition_id": def_id,
                    "outcome": OUTCOME_SKIPPED,
                }
            )
            continue
        if fact.status != FACT_ASSERTED:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message=(
                    f"fact_id={fact.id} status={fact.status} "
                    f"is not publishable from Wave orchestrator"
                ),
                details=[{"field": "facts.status", "message": fact.status}],
            )
        await fact_service.publish_fact(
            db,
            fact_id=fact.id,
            actor=actor,
            change_reason=change_reason,
        )
        newly_published += 1
        outcomes.append(
            {
                "fact_id": fact.id,
                "definition_id": def_id,
                "outcome": OUTCOME_PUBLISHED,
            }
        )

    if newly_published == 0 and skipped == len(required):
        item_status = ITEM_SKIPPED
    else:
        item_status = ITEM_SUCCESS
    return {
        "item_status": item_status,
        "newly_published": newly_published,
        "skipped": skipped,
        "failed": 0,
        "facts": outcomes,
        "resumed": skipped > 0,
    }


async def publish_wave(
    db: AsyncSession,
    *,
    wave_id: str,
    change_reason: str,
    actor: User,
    stop_on_first_failure: bool = True,
) -> dict[str, Any]:
    """Governed Wave publish: EvidenceValidated|Failed(publish) → Publishing → Published."""
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )

    wave = await _get_wave(db, wave_id)
    previous_status = wave.status

    if previous_status == WAVE_STATUS_PUBLISHED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Wave is already Published",
            details=[{"field": "status", "message": previous_status}],
        )

    if previous_status == WAVE_STATUS_FAILED:
        if not await _latest_run_is_failed_publish(db, wave.id):
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message=(
                    "Failed waves may publish-resume only when the latest run is a "
                    "failed publish (assert Failed must re-seal via PR3-A resume)"
                ),
                details=[{"field": "status", "message": previous_status}],
            )
    elif previous_status != WAVE_STATUS_EVIDENCE_VALIDATED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only EvidenceValidated waves may publish "
            "(or Failed after a failed publish run)",
            details=[{"field": "status", "message": previous_status}],
        )

    await _verify_manifest_sha(db, wave)
    policy = resolve_wave_policy(wave)
    await batch_service.assert_environment_gates(db, pins=policy["environment_pins"])
    await _assert_no_running_publish(db, wave.id)

    now = datetime.now(UTC)
    run = KnowledgeWaveRun(
        wave_id=wave.id,
        run_type=RUN_TYPE_PUBLISH,
        status=RUN_CREATED,
        created_by=actor.id,
        manifest_sha256_snapshot=wave.manifest_sha256,
        request_snapshot_json={"change_reason": reason},
        started_at=None,
        finished_at=None,
        stop_reason=None,
    )
    db.add(run)
    await db.flush()

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

    assert_transition(previous_status, WAVE_STATUS_PUBLISHING)
    wave.status = WAVE_STATUS_PUBLISHING
    run.status = RUN_RUNNING
    run.started_at = now
    await db.flush()

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.publish.start",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "wave_pk": wave.id,
            "wave_run_id": run.id,
            "from_status": previous_status,
            "to_status": WAVE_STATUS_PUBLISHING,
            "manifest_sha256": wave.manifest_sha256,
            "change_reason": reason,
            "allowlist_count": len(wave.products),
        },
    )
    await db.commit()

    run_id = run.id
    totals = {"total": 0, "published": 0, "skipped": 0, "failed": 0}
    required_n = len(batch_service.FACT_DEFINITION_ORDER)
    totals["total"] = len(wave.products) * required_n

    run = (
        await db.execute(
            select(KnowledgeWaveRun)
            .options(selectinload(KnowledgeWaveRun.items))
            .where(KnowledgeWaveRun.id == run_id)
        )
    ).scalar_one()
    wave = await _get_wave(db, wave_id)
    items = sorted(run.items, key=lambda i: (i.product_id or 0, i.id))

    for item in items:
        item_id = item.id
        product_id = int(item.product_id or 0)
        sku = str(item.sku_snapshot or "")
        item.status = ITEM_RUNNING
        item.started_at = datetime.now(UTC)
        await db.flush()
        try:
            outcome = await _publish_product_facts(
                db,
                wave=wave,
                product_id=product_id,
                sku_snapshot=sku,
                actor=actor,
                change_reason=reason,
            )
            item = next(i for i in run.items if i.id == item_id)
            item.status = outcome["item_status"]
            item.resumed = bool(outcome.get("resumed"))
            item.result_json = {
                "facts": outcome["facts"],
                "newly_published": outcome["newly_published"],
                "skipped": outcome["skipped"],
            }
            item.finished_at = datetime.now(UTC)
            item.error_message = None
            totals["published"] += int(outcome["newly_published"])
            totals["skipped"] += int(outcome["skipped"])
            await db.commit()
        except Exception as exc:  # noqa: BLE001 — item failure → ledger
            await db.rollback()
            run = (
                await db.execute(
                    select(KnowledgeWaveRun)
                    .options(selectinload(KnowledgeWaveRun.items))
                    .where(KnowledgeWaveRun.id == run_id)
                )
            ).scalar_one()
            wave = await _get_wave(db, wave_id)
            failed = next(i for i in run.items if i.id == item_id)
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict):
                err_msg = str(detail.get("message") or detail)[:2000]
            else:
                err_msg = str(detail or exc)[:2000]
            failed.status = ITEM_FAILED
            failed.error_message = err_msg
            failed.finished_at = datetime.now(UTC)
            failed.result_json = {"facts": [], "error": err_msg}
            totals["failed"] += required_n
            await record_audit(
                db,
                actor_user_id=actor.id,
                action="wave.publish.fail",
                entity_type="knowledge_wave_run_item",
                entity_id=failed.id,
                details={
                    "wave_id": wave.wave_id,
                    "wave_run_id": run.id,
                    "product_id": failed.product_id,
                    "sku": failed.sku_snapshot,
                    "error_message": err_msg,
                },
            )
            if stop_on_first_failure:
                await _finalize_failure(
                    db,
                    wave=wave,
                    run=run,
                    actor=actor,
                    stop_reason=err_msg,
                    totals=totals,
                    previous_status=previous_status,
                    change_reason=reason,
                )
                await db.commit()
                return await _serialize(
                    db,
                    wave_id=wave_id,
                    run_id=run_id,
                    previous_status=previous_status,
                    totals=totals,
                )
            await db.commit()

    run = (
        await db.execute(
            select(KnowledgeWaveRun)
            .options(selectinload(KnowledgeWaveRun.items))
            .where(KnowledgeWaveRun.id == run_id)
        )
    ).scalar_one()
    wave = await _get_wave(db, wave_id)
    if any(i.status == ITEM_FAILED for i in run.items):
        await _finalize_failure(
            db,
            wave=wave,
            run=run,
            actor=actor,
            stop_reason="one or more products failed to publish",
            totals=totals,
            previous_status=previous_status,
            change_reason=reason,
        )
    else:
        await _finalize_success(
            db,
            wave=wave,
            run=run,
            actor=actor,
            totals=totals,
            previous_status=previous_status,
            change_reason=reason,
        )
    await db.commit()
    return await _serialize(
        db,
        wave_id=wave_id,
        run_id=run_id,
        previous_status=previous_status,
        totals=totals,
    )


async def _finalize_success(
    db: AsyncSession,
    *,
    wave: KnowledgeWave,
    run: KnowledgeWaveRun,
    actor: User,
    totals: dict[str, int],
    previous_status: str,
    change_reason: str,
) -> None:
    assert_transition(wave.status, WAVE_STATUS_PUBLISHED)
    wave.status = WAVE_STATUS_PUBLISHED
    run.status = RUN_COMPLETED
    run.finished_at = datetime.now(UTC)
    run.stop_reason = None
    await db.flush()
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.publish",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "wave_run_id": run.id,
            "from_status": previous_status,
            "via_status": WAVE_STATUS_PUBLISHING,
            "to_status": WAVE_STATUS_PUBLISHED,
            "manifest_sha256": wave.manifest_sha256,
            "change_reason": change_reason,
            "stats": totals,
        },
    )
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.publish.complete",
        entity_type="knowledge_wave_run",
        entity_id=run.id,
        details={
            "wave_id": wave.wave_id,
            "wave_run_id": run.id,
            "status": RUN_COMPLETED,
            "stats": totals,
        },
    )


async def _finalize_failure(
    db: AsyncSession,
    *,
    wave: KnowledgeWave,
    run: KnowledgeWaveRun,
    actor: User,
    stop_reason: str,
    totals: dict[str, int],
    previous_status: str,
    change_reason: str,
) -> None:
    assert_transition(wave.status, WAVE_STATUS_FAILED)
    wave.status = WAVE_STATUS_FAILED
    run.status = RUN_FAILED
    run.finished_at = datetime.now(UTC)
    run.stop_reason = stop_reason[:2000]
    await db.flush()
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.publish.fail",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "wave_run_id": run.id,
            "from_status": previous_status,
            "to_status": WAVE_STATUS_FAILED,
            "manifest_sha256": wave.manifest_sha256,
            "change_reason": change_reason,
            "stop_reason": run.stop_reason,
            "stats": totals,
        },
    )


async def _serialize(
    db: AsyncSession,
    *,
    wave_id: str,
    run_id: int,
    previous_status: str,
    totals: dict[str, int],
) -> dict[str, Any]:
    wave = await _get_wave(db, wave_id)
    run = (
        await db.execute(
            select(KnowledgeWaveRun)
            .options(selectinload(KnowledgeWaveRun.items))
            .where(KnowledgeWaveRun.id == run_id)
        )
    ).scalar_one()
    items = sorted(run.items, key=lambda i: (i.product_id or 0, i.id))
    return {
        "ok": run.status == RUN_COMPLETED and wave.status == WAVE_STATUS_PUBLISHED,
        "wave_id": wave.wave_id,
        "wave_pk": wave.id,
        "run_id": run.id,
        "previous_status": previous_status,
        "new_status": wave.status,
        "total": totals["total"],
        "published": totals["published"],
        "skipped": totals["skipped"],
        "failed": totals["failed"],
        "manifest_sha256": wave.manifest_sha256,
        "progress": _progress(items),
        "stop_reason": run.stop_reason,
        "wave": wave,
    }
