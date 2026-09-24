"""PR3-B.2 — Wave evidence validation (Asserted → EvidenceValidated).

Read-only checks against Facts / Evidence / assert run ledger, then a single
lifecycle transition via ``knowledge_wave_lifecycle.assert_transition``.
Does not publish Facts, mutate Evidence, or touch Product JSONB.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge import (
    KnowledgeEvidenceArtifact,
    KnowledgeEvidenceLink,
    KnowledgeFact,
)
from app.db.models.knowledge_wave import (
    KnowledgeWave,
    KnowledgeWaveRun,
)
from app.db.models.product import Product
from app.db.models.product_type import ProductType, ProductTypeDefinition
from app.db.models.user import User
from app.services import knowledge_batch_assert_service as batch_service
from app.services.audit_service import record_audit
from app.services.knowledge_wave_lifecycle import (
    WAVE_STATUS_ASSERTED,
    WAVE_STATUS_EVIDENCE_VALIDATED,
    assert_transition,
)
from app.services.knowledge_wave_service import (
    build_canonical_manifest_payload,
    compute_manifest_sha256,
)

RUN_TYPE_ASSERT = "assert"
RUN_COMPLETED = "completed"
ITEM_FAILED = "failed"
RELATION_FACT_SUPPORTED_BY = "FACT_SUPPORTED_BY"
VALID_FACT_STATUSES = frozenset({"asserted", "published"})
REQUIRED_LOCATOR_KEYS = ("pdf_page", "printed_page", "model", "property")


def _issue(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}


def fact_definition_match_issues(
    *,
    sku_snapshot: str,
    def_id: str,
    matches: list[KnowledgeFact],
    wave_definition_id: int,
) -> list[dict[str, str]]:
    """Validate one product×definition Fact set (coverage / duplicate / status / pin)."""
    issues: list[dict[str, str]] = []
    if not matches:
        issues.append(_issue("facts", f"sku={sku_snapshot} missing {def_id}"))
        return issues
    if len(matches) > 1:
        issues.append(_issue("facts", f"sku={sku_snapshot} duplicate {def_id}"))
        return issues
    fact = matches[0]
    if fact.status not in VALID_FACT_STATUSES:
        issues.append(
            _issue("facts.status", f"fact_id={fact.id} status={fact.status}")
        )
    if fact.product_type_definition_id != wave_definition_id:
        issues.append(
            _issue(
                "facts.definition",
                f"fact_id={fact.id} product_type_definition_id mismatch",
            )
        )
    return issues


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


async def collect_evidence_validation_issues(
    db: AsyncSession,
    wave: KnowledgeWave,
) -> tuple[list[dict[str, str]], dict[str, Any], str | None]:
    """Read-only evidence readiness checks. Returns (issues, stats, digest)."""
    issues: list[dict[str, str]] = []
    digest: str | None = None
    stats: dict[str, Any] = {
        "allowlist_count": len(wave.products),
        "assert_run_id": None,
        "assert_run_items": 0,
        "facts_checked": 0,
        "evidence_links_checked": 0,
        "property_definitions": list(batch_service.FACT_DEFINITION_ORDER),
    }

    if wave.status != WAVE_STATUS_ASSERTED:
        issues.append(
            _issue(
                "status",
                f"Evidence validation requires Asserted (current={wave.status})",
            )
        )

    if not wave.manifest_sha256:
        issues.append(_issue("manifest_sha256", "missing"))
    else:
        pt = await db.get(ProductType, wave.product_type_id)
        definition = await db.get(ProductTypeDefinition, wave.definition_id)
        if pt is None or definition is None:
            issues.append(_issue("definition_id", "product_type/definition unresolvable"))
        else:
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
                issues.append(_issue("manifest_sha256", "drift vs canonical payload"))

    policy = wave.policy_json if isinstance(wave.policy_json, dict) else {}
    pins = policy.get("environment_pins") or {}
    try:
        await batch_service.assert_environment_gates(db, pins=pins)
    except HTTPException as exc:
        if isinstance(exc.detail, dict):
            msg = str(exc.detail.get("message") or "environment gate failed")
            field = "environment_pins"
            details = exc.detail.get("details") or []
            if details and isinstance(details[0], dict) and details[0].get("field"):
                field = str(details[0]["field"])
            issues.append(_issue(field, msg))
        else:
            issues.append(_issue("environment_pins", "environment gate failed"))

    # Latest completed assert run for this wave
    run = (
        await db.execute(
            select(KnowledgeWaveRun)
            .options(selectinload(KnowledgeWaveRun.items))
            .where(
                KnowledgeWaveRun.wave_id == wave.id,
                KnowledgeWaveRun.run_type == RUN_TYPE_ASSERT,
            )
            .order_by(KnowledgeWaveRun.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        issues.append(_issue("assert_run", "no assert run found"))
    else:
        stats["assert_run_id"] = run.id
        stats["assert_run_items"] = len(run.items)
        if run.status != RUN_COMPLETED:
            issues.append(
                _issue("assert_run", f"latest assert run status={run.status}")
            )
        failed_items = [i for i in run.items if i.status == ITEM_FAILED]
        if failed_items:
            issues.append(
                _issue(
                    "assert_run_items",
                    f"failed items={len(failed_items)}",
                )
            )
        allow = {
            (int(p.product_id), str(p.sku_snapshot)) for p in wave.products
        }
        run_keys = {
            (int(i.product_id), str(i.sku_snapshot))
            for i in run.items
            if i.product_id is not None and i.sku_snapshot
        }
        if run_keys != allow:
            issues.append(
                _issue(
                    "assert_run_items",
                    "run items do not match sealed allowlist",
                )
            )

    required_defs = list(batch_service.FACT_DEFINITION_ORDER)
    for row in sorted(wave.products, key=lambda p: (p.product_id, p.sku_snapshot)):
        product = await db.get(Product, row.product_id)
        if product is None:
            issues.append(
                _issue(
                    "products",
                    f"product_id={row.product_id} missing",
                )
            )
            continue
        if str(product.sku) != str(row.sku_snapshot):
            issues.append(
                _issue(
                    "products.sku_snapshot",
                    f"product_id={row.product_id} sku mismatch",
                )
            )
        if product.product_type_id != wave.product_type_id:
            issues.append(
                _issue(
                    "products.product_type_id",
                    f"product_id={row.product_id} type mismatch",
                )
            )

        facts = (
            await db.execute(
                select(KnowledgeFact).where(
                    KnowledgeFact.entity_id == row.product_id,
                    KnowledgeFact.definition_id.in_(required_defs),
                )
            )
        ).scalars().all()
        by_def: dict[str, list[KnowledgeFact]] = {}
        for fact in facts:
            by_def.setdefault(fact.definition_id, []).append(fact)

        for def_id in required_defs:
            matches = by_def.get(def_id) or []
            def_issues = fact_definition_match_issues(
                sku_snapshot=str(row.sku_snapshot),
                def_id=def_id,
                matches=matches,
                wave_definition_id=int(wave.definition_id),
            )
            if def_issues:
                issues.extend(def_issues)
                # Missing / duplicate: skip evidence checks for this definition.
                if not matches or len(matches) > 1:
                    continue
                # Status / pin issues: still inspect evidence on the single Fact.
            if not matches:
                continue
            fact = matches[0]
            stats["facts_checked"] += 1

            links = (
                await db.execute(
                    select(KnowledgeEvidenceLink).where(
                        KnowledgeEvidenceLink.fact_id == fact.id,
                        KnowledgeEvidenceLink.relation_type
                        == RELATION_FACT_SUPPORTED_BY,
                    )
                )
            ).scalars().all()
            if not links:
                issues.append(
                    _issue(
                        "evidence_links",
                        f"fact_id={fact.id} missing FACT_SUPPORTED_BY",
                    )
                )
                continue
            if len(links) > 1:
                issues.append(
                    _issue(
                        "evidence_links",
                        f"fact_id={fact.id} multiple FACT_SUPPORTED_BY links",
                    )
                )
            for link in links:
                stats["evidence_links_checked"] += 1
                artifact = await db.get(
                    KnowledgeEvidenceArtifact, int(link.artifact_id)
                )
                if artifact is None:
                    issues.append(
                        _issue(
                            "artifact",
                            f"artifact pk={link.artifact_id} missing",
                        )
                    )
                    continue
                checksum = (artifact.checksum_sha256 or "").lower()
                if checksum != batch_service.REQUIRED_ARTIFACT_CHECKSUM:
                    issues.append(
                        _issue(
                            "artifact.checksum_sha256",
                            f"artifact pk={artifact.id} checksum mismatch",
                        )
                    )
                locator = link.locator if isinstance(link.locator, dict) else None
                if not isinstance(locator, dict):
                    issues.append(
                        _issue(
                            "evidence_links.locator",
                            f"fact_id={fact.id} locator must be object",
                        )
                    )
                    continue
                for key in REQUIRED_LOCATOR_KEYS:
                    if key not in locator:
                        issues.append(
                            _issue(
                                "evidence_links.locator",
                                f"fact_id={fact.id} missing {key}",
                            )
                        )
                expected_prop = def_id.removeprefix("def.")
                if locator.get("property") != expected_prop:
                    issues.append(
                        _issue(
                            "evidence_links.locator.property",
                            f"fact_id={fact.id} property mismatch",
                        )
                    )

    return issues, stats, digest


async def validate_wave_evidence(
    db: AsyncSession,
    *,
    wave_id: str,
    change_reason: str,
    actor: User,
) -> dict[str, Any]:
    """Validate evidence readiness and transition Asserted → EvidenceValidated."""
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )

    wave = await _get_wave_by_wave_id(db, wave_id)
    previous_status = wave.status

    if previous_status == WAVE_STATUS_EVIDENCE_VALIDATED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Wave is already EvidenceValidated",
            details=[{"field": "status", "message": previous_status}],
        )

    if previous_status != WAVE_STATUS_ASSERTED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only Asserted waves may validate evidence",
            details=[{"field": "status", "message": previous_status}],
        )

    issues, stats, digest = await collect_evidence_validation_issues(db, wave)
    if issues:
        await record_audit(
            db,
            actor_user_id=actor.id,
            action="wave.evidence_validate.fail",
            entity_type="knowledge_wave",
            entity_id=wave.id,
            details={
                "wave_id": wave.wave_id,
                "from_status": previous_status,
                "manifest_sha256": wave.manifest_sha256,
                "stats": stats,
                "issue_count": len(issues),
                "issues": issues[:50],
                "change_reason": reason,
            },
        )
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Wave evidence validation failed",
            details=[{"field": i["field"], "message": i["message"]} for i in issues],
        )

    assert_transition(previous_status, WAVE_STATUS_EVIDENCE_VALIDATED)
    wave.status = WAVE_STATUS_EVIDENCE_VALIDATED
    await db.flush()

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.evidence_validate",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "from_status": previous_status,
            "to_status": WAVE_STATUS_EVIDENCE_VALIDATED,
            "manifest_sha256": wave.manifest_sha256 or digest,
            "stats": stats,
            "change_reason": reason,
            "actor_user_id": actor.id,
        },
    )

    refreshed = await _get_wave_by_wave_id(db, wave.wave_id)
    return {
        "wave": refreshed,
        "previous_status": previous_status,
        "new_status": refreshed.status,
        "ok": True,
        "wave_id": refreshed.wave_id,
        "manifest_sha256": refreshed.manifest_sha256,
        "stats": stats,
        "issues": [],
    }
