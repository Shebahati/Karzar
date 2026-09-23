"""Knowledge Wave Registry PR1/PR2 — Draft/Review/Seal + validation (no execute)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge_wave import KnowledgeWave, KnowledgeWaveProduct
from app.db.models.product import Product
from app.db.models.product_type import ProductType, ProductTypeDefinition
from app.db.models.user import User
from app.services.audit_service import record_audit
from app.services.knowledge_wave_lifecycle import (
    WAVE_STATUS_ABORTED,
    WAVE_STATUS_ASSERTED,
    WAVE_STATUS_DRAFT,
    WAVE_STATUS_EXECUTING,
    WAVE_STATUS_FAILED,
    WAVE_STATUS_REVIEWED,
    WAVE_STATUS_SEALED,
    assert_mutable_pre_seal,
    assert_transition,
)

MANIFEST_SCHEMA = "kb.wave.manifest.v1"


async def _get_wave_or_404(db: AsyncSession, wave_pk: int) -> KnowledgeWave:
    wave = (
        await db.execute(
            select(KnowledgeWave)
            .options(selectinload(KnowledgeWave.products))
            .where(KnowledgeWave.id == wave_pk)
        )
    ).scalar_one_or_none()
    if wave is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Wave not found",
            details=[{"field": "id", "message": "not found"}],
        )
    return wave


async def _assert_pt_and_definition(
    db: AsyncSession, *, product_type_id: int, definition_id: int
) -> tuple[ProductType, ProductTypeDefinition]:
    pt = await db.get(ProductType, product_type_id)
    if pt is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="product_type_id does not exist",
            details=[{"field": "product_type_id", "message": "not found"}],
        )
    definition = await db.get(ProductTypeDefinition, definition_id)
    if definition is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="definition_id does not exist",
            details=[{"field": "definition_id", "message": "not found"}],
        )
    if definition.product_type_id != product_type_id:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="definition_id does not belong to product_type_id",
            details=[
                {"field": "definition_id", "message": "mismatched product_type_id"},
            ],
        )
    return pt, definition


def _policy_is_valid(policy_json: Any) -> bool:
    return isinstance(policy_json, dict)


def build_canonical_manifest_payload(
    *,
    wave_id: str,
    brand: str,
    product_type: ProductType,
    definition: ProductTypeDefinition,
    policy_json: dict[str, Any],
    products: list[KnowledgeWaveProduct],
) -> dict[str, Any]:
    """Immutable seal payload — order of products is normalized by product_id, sku."""
    allowlist = sorted(
        (
            {"product_id": int(p.product_id), "sku_snapshot": str(p.sku_snapshot)}
            for p in products
        ),
        key=lambda row: (row["product_id"], row["sku_snapshot"]),
    )
    return {
        "schema": MANIFEST_SCHEMA,
        "wave_id": wave_id,
        "brand": brand,
        "product_type": {"id": int(product_type.id), "code": product_type.code},
        "definition": {
            "id": int(definition.id),
            "version": int(definition.version),
        },
        "policy_json": policy_json if isinstance(policy_json, dict) else {},
        "products": allowlist,
    }


def compute_manifest_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _replace_products(
    db: AsyncSession,
    wave: KnowledgeWave,
    products: list[dict[str, Any]],
) -> None:
    """Replace allowlist via DELETE+INSERT — no relationship mutation (async-safe)."""
    seen_product_ids: set[int] = set()
    seen_skus: set[str] = set()
    validated: list[tuple[int, str]] = []
    for item in products:
        product_id = int(item["product_id"])
        sku = str(item["sku_snapshot"]).strip()
        if not sku:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="sku_snapshot is required",
                details=[{"field": "products.sku_snapshot", "message": "required"}],
            )
        if product_id in seen_product_ids:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="duplicate product_id in products list",
                details=[{"field": "products.product_id", "message": str(product_id)}],
            )
        if sku in seen_skus:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="duplicate sku_snapshot in products list",
                details=[{"field": "products.sku_snapshot", "message": sku}],
            )
        seen_product_ids.add(product_id)
        seen_skus.add(sku)
        product = await db.get(Product, product_id)
        if product is None:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="product_id does not exist",
                details=[{"field": "products.product_id", "message": str(product_id)}],
            )
        validated.append((product_id, sku))

    await db.execute(
        delete(KnowledgeWaveProduct).where(KnowledgeWaveProduct.wave_id == wave.id)
    )
    for product_id, sku in validated:
        db.add(
            KnowledgeWaveProduct(
                wave_id=wave.id,
                product_id=product_id,
                sku_snapshot=sku,
            )
        )


async def create_draft_wave(
    db: AsyncSession,
    *,
    wave_id: str,
    brand: str,
    product_type_id: int,
    definition_id: int,
    policy_json: dict[str, Any] | None,
    products: list[dict[str, Any]] | None,
    actor: User,
) -> KnowledgeWave:
    wid = (wave_id or "").strip()
    if not wid:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="wave_id is required",
            details=[{"field": "wave_id", "message": "required"}],
        )
    brand_norm = (brand or "").strip()
    if not brand_norm:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="brand is required",
            details=[{"field": "brand", "message": "required"}],
        )
    if policy_json is not None and not _policy_is_valid(policy_json):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="policy_json must be an object",
            details=[{"field": "policy_json", "message": "must be object"}],
        )

    await _assert_pt_and_definition(
        db, product_type_id=product_type_id, definition_id=definition_id
    )

    wave = KnowledgeWave(
        wave_id=wid,
        status=WAVE_STATUS_DRAFT,
        manifest_sha256=None,
        brand=brand_norm,
        product_type_id=product_type_id,
        definition_id=definition_id,
        policy_json=policy_json or {},
        created_by=actor.id,
        reviewed_by=None,
    )
    db.add(wave)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="wave_id already exists",
            details=[{"field": "wave_id", "message": wid}],
        ) from exc

    product_list = products or []
    if product_list:
        await _replace_products(db, wave, product_list)
        try:
            await db.flush()
        except IntegrityError as exc:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message="wave product allowlist conflict",
                details=[{"field": "products", "message": "unique constraint"}],
            ) from exc

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="knowledge_wave.create",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "status": wave.status,
            "brand": wave.brand,
            "product_type_id": wave.product_type_id,
            "definition_id": wave.definition_id,
            "product_count": len(product_list),
        },
    )
    return await _get_wave_or_404(db, wave.id)


async def list_waves(db: AsyncSession) -> list[KnowledgeWave]:
    result = await db.execute(
        select(KnowledgeWave)
        .options(selectinload(KnowledgeWave.products))
        .order_by(KnowledgeWave.id.asc())
    )
    return list(result.scalars().all())


async def get_wave(db: AsyncSession, wave_pk: int) -> KnowledgeWave:
    return await _get_wave_or_404(db, wave_pk)


async def update_draft_wave(
    db: AsyncSession,
    *,
    wave_pk: int,
    patch: dict[str, Any],
    actor: User,
) -> KnowledgeWave:
    wave = await _get_wave_or_404(db, wave_pk)
    assert_mutable_pre_seal(wave.status)
    if wave.status != WAVE_STATUS_DRAFT:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only Draft waves may be patched",
            details=[{"field": "status", "message": f"current status is '{wave.status}'"}],
        )

    if "brand" in patch and patch["brand"] is not None:
        brand_norm = str(patch["brand"]).strip()
        if not brand_norm:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="brand is required",
                details=[{"field": "brand", "message": "required"}],
            )
        wave.brand = brand_norm

    product_type_id = patch.get("product_type_id", wave.product_type_id)
    definition_id = patch.get("definition_id", wave.definition_id)
    if "product_type_id" in patch or "definition_id" in patch:
        if product_type_id is None or definition_id is None:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="product_type_id and definition_id are required",
                details=[{"field": "product_type_id", "message": "required"}],
            )
        await _assert_pt_and_definition(
            db, product_type_id=int(product_type_id), definition_id=int(definition_id)
        )
        wave.product_type_id = int(product_type_id)
        wave.definition_id = int(definition_id)

    if "policy_json" in patch and patch["policy_json"] is not None:
        if not _policy_is_valid(patch["policy_json"]):
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="policy_json must be an object",
                details=[{"field": "policy_json", "message": "must be object"}],
            )
        wave.policy_json = patch["policy_json"]

    if "products" in patch and patch["products"] is not None:
        await _replace_products(db, wave, patch["products"])

    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="wave update conflict",
            details=[{"field": "wave", "message": "integrity error"}],
        ) from exc

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="knowledge_wave.update_draft",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={"wave_id": wave.wave_id, "patch_keys": sorted(patch.keys())},
    )
    return await _get_wave_or_404(db, wave.id)


async def review_wave(
    db: AsyncSession,
    *,
    wave_pk: int,
    to_status: str,
    change_reason: str,
    actor: User,
) -> KnowledgeWave:
    """PR1 transitions: Draft → Reviewed and Reviewed → Draft. Not Sealed."""
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )
    target = (to_status or "").strip()
    if target not in (WAVE_STATUS_DRAFT, WAVE_STATUS_REVIEWED):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="to_status must be Draft or Reviewed",
            details=[{"field": "to_status", "message": target}],
        )

    wave = await _get_wave_or_404(db, wave_pk)
    from_status = wave.status

    if from_status not in (WAVE_STATUS_DRAFT, WAVE_STATUS_REVIEWED):
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Sealed waves cannot transition via review",
            details=[{"field": "status", "message": from_status}],
        )

    if from_status == target:
        if target == WAVE_STATUS_REVIEWED:
            wave.reviewed_by = actor.id
        await db.flush()
    else:
        assert_transition(from_status, target)
        if from_status == WAVE_STATUS_DRAFT and target == WAVE_STATUS_REVIEWED:
            wave.status = WAVE_STATUS_REVIEWED
            wave.reviewed_by = actor.id
            await db.flush()
        elif from_status == WAVE_STATUS_REVIEWED and target == WAVE_STATUS_DRAFT:
            wave.status = WAVE_STATUS_DRAFT
            wave.reviewed_by = None
            await db.flush()
        else:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message=f"Illegal review transition {from_status} → {target}",
                details=[
                    {"field": "status", "message": from_status},
                    {"field": "to_status", "message": target},
                ],
            )

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="knowledge_wave.review",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "from_status": from_status,
            "to_status": wave.status,
            "change_reason": reason,
        },
    )
    return await _get_wave_or_404(db, wave.id)


async def _collect_validation_issues(
    db: AsyncSession,
    wave: KnowledgeWave,
    *,
    tier: str,
) -> tuple[list[dict[str, str]], str | None]:
    issues: list[dict[str, str]] = []

    if not (wave.wave_id or "").strip():
        issues.append(
            {"field": "wave_id", "message": "required", "severity": "error"}
        )
    if not (wave.brand or "").strip():
        issues.append({"field": "brand", "message": "required", "severity": "error"})
    if not _policy_is_valid(wave.policy_json):
        issues.append(
            {
                "field": "policy_json",
                "message": "must be object",
                "severity": "error",
            }
        )

    pt = await db.get(ProductType, wave.product_type_id)
    definition = await db.get(ProductTypeDefinition, wave.definition_id)
    if pt is None:
        issues.append(
            {
                "field": "product_type_id",
                "message": "not found",
                "severity": "error",
            }
        )
    if definition is None:
        issues.append(
            {
                "field": "definition_id",
                "message": "not found",
                "severity": "error",
            }
        )
    elif pt is not None and definition.product_type_id != pt.id:
        issues.append(
            {
                "field": "definition_id",
                "message": "mismatched product_type_id",
                "severity": "error",
            }
        )

    for row in wave.products:
        product = await db.get(Product, row.product_id)
        if product is None:
            issues.append(
                {
                    "field": "products.product_id",
                    "message": f"{row.product_id} not found",
                    "severity": "error",
                }
            )

    preview_sha: str | None = None
    if pt is not None and definition is not None and _policy_is_valid(wave.policy_json):
        payload = build_canonical_manifest_payload(
            wave_id=wave.wave_id,
            brand=wave.brand,
            product_type=pt,
            definition=definition,
            policy_json=wave.policy_json,
            products=list(wave.products),
        )
        preview_sha = compute_manifest_sha256(payload)

    if tier in ("pre_seal", "execution_readiness"):
        if not wave.products:
            issues.append(
                {
                    "field": "products",
                    "message": "allowlist required before seal",
                    "severity": "error",
                }
            )
        if wave.status not in (
            WAVE_STATUS_REVIEWED,
            WAVE_STATUS_SEALED,
        ) and tier == "pre_seal":
            # pre_seal validation may be called while still Draft to surface readiness
            if wave.status == WAVE_STATUS_DRAFT:
                issues.append(
                    {
                        "field": "status",
                        "message": "must be Reviewed before seal",
                        "severity": "warning",
                    }
                )

    if tier == "execution_readiness":
        if wave.status not in (
            WAVE_STATUS_SEALED,
            WAVE_STATUS_EXECUTING,
            WAVE_STATUS_ASSERTED,
            WAVE_STATUS_FAILED,
            WAVE_STATUS_ABORTED,
        ):
            issues.append(
                {
                    "field": "status",
                    "message": "must be Sealed (or post-seal) for execution readiness",
                    "severity": "error",
                }
            )
        if not wave.manifest_sha256:
            issues.append(
                {
                    "field": "manifest_sha256",
                    "message": "missing seal digest",
                    "severity": "error",
                }
            )
        elif preview_sha and wave.manifest_sha256 != preview_sha:
            issues.append(
                {
                    "field": "manifest_sha256",
                    "message": "stored digest does not match canonical payload",
                    "severity": "error",
                }
            )

    return issues, preview_sha


async def validate_wave(
    db: AsyncSession,
    *,
    wave_pk: int,
    actor: User,
) -> dict[str, Any]:
    """Status-tiered validation. Never executes."""
    wave = await _get_wave_or_404(db, wave_pk)
    if wave.status == WAVE_STATUS_DRAFT:
        tier = "basic"
    elif wave.status == WAVE_STATUS_REVIEWED:
        tier = "pre_seal"
    elif wave.status == WAVE_STATUS_SEALED:
        tier = "execution_readiness"
    else:
        # Executing/Asserted/Failed/Aborted — still report readiness vs digest
        tier = "execution_readiness"

    issues, preview_sha = await _collect_validation_issues(db, wave, tier=tier)
    ok = not any(i.get("severity") == "error" for i in issues)

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.validate",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "status": wave.status,
            "validation_tier": tier,
            "ok": ok,
            "issue_count": len(issues),
        },
    )

    return {
        "wave_pk": wave.id,
        "wave_id": wave.wave_id,
        "status": wave.status,
        "validation_tier": tier,
        "ok": ok,
        "issues": issues,
        "preview_manifest_sha256": preview_sha,
        "stored_manifest_sha256": wave.manifest_sha256,
    }


async def seal_wave(
    db: AsyncSession,
    *,
    wave_pk: int,
    change_reason: str,
    actor: User,
) -> KnowledgeWave:
    """Reviewed → Sealed with deterministic manifest_sha256. No execute."""
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )

    wave = await _get_wave_or_404(db, wave_pk)
    if wave.status == WAVE_STATUS_DRAFT:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Draft waves cannot be sealed (Reviewed required)",
            details=[{"field": "status", "message": WAVE_STATUS_DRAFT}],
        )
    if wave.status == WAVE_STATUS_SEALED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Wave is already Sealed",
            details=[
                {"field": "status", "message": WAVE_STATUS_SEALED},
                {
                    "field": "manifest_sha256",
                    "message": wave.manifest_sha256 or "",
                },
            ],
        )
    if wave.status != WAVE_STATUS_REVIEWED:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=f"Cannot seal wave from status '{wave.status}'",
            details=[{"field": "status", "message": wave.status}],
        )
    assert_transition(WAVE_STATUS_REVIEWED, WAVE_STATUS_SEALED)

    issues, preview_sha = await _collect_validation_issues(
        db, wave, tier="pre_seal"
    )
    errors = [i for i in issues if i.get("severity") == "error"]
    if errors or not preview_sha:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Wave failed pre-seal validation",
            details=[
                {"field": e["field"], "message": e["message"]} for e in errors
            ]
            or [{"field": "manifest", "message": "could not compute digest"}],
        )

    pt, definition = await _assert_pt_and_definition(
        db,
        product_type_id=wave.product_type_id,
        definition_id=wave.definition_id,
    )
    # Recompute under assert for type narrowing / frozen snapshot.
    payload = build_canonical_manifest_payload(
        wave_id=wave.wave_id,
        brand=wave.brand,
        product_type=pt,
        definition=definition,
        policy_json=wave.policy_json if isinstance(wave.policy_json, dict) else {},
        products=list(wave.products),
    )
    digest = compute_manifest_sha256(payload)
    if digest != preview_sha:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Seal digest mismatch during seal",
            details=[{"field": "manifest_sha256", "message": "internal mismatch"}],
        )

    wave.manifest_sha256 = digest
    wave.status = WAVE_STATUS_SEALED
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="manifest_sha256 conflict (duplicate seal digest)",
            details=[{"field": "manifest_sha256", "message": digest}],
        ) from exc

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="wave.seal",
        entity_type="knowledge_wave",
        entity_id=wave.id,
        details={
            "wave_id": wave.wave_id,
            "from_status": WAVE_STATUS_REVIEWED,
            "to_status": WAVE_STATUS_SEALED,
            "manifest_sha256": digest,
            "change_reason": reason,
            "product_count": len(wave.products),
        },
    )
    return await _get_wave_or_404(db, wave.id)
