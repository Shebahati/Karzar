"""Governed Fact lifecycle + append-only revisions (Prompt 12 / A4).

Ownership:
  Property Dictionary — canonical meaning
  Product Type Definition — applicability / narrowing
  Fact — product-specific value
  Evidence (Prompt 13) — required when membership.evidence_requirement_override=required

Published Fact mutations re-run the full publish gate (candidate-first).
Existing-Fact mutations lock the Fact row (FOR UPDATE) to serialize revisions.
No JSONB dual-write. No Product Type assignment in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge import (
    FACT_STATUSES,
    PUBLIC_FACT_STATUSES,
    KnowledgeFact,
    KnowledgeFactRevision,
    KnowledgePropertyDefinition,
    KnowledgeUnit,
)
from app.db.models.product import Product
from app.db.models.product_type import (
    MembershipRequiredness,
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
)
from app.db.models.user import User
from app.services import knowledge_evidence_service as evidence_service
from app.services.fact_validation import validate_fact_payload

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "asserted": frozenset({"published", "deprecated"}),
    "published": frozenset({"disputed", "deprecated"}),
    "disputed": frozenset({"deprecated"}),
    "deprecated": frozenset(),
}


@dataclass(frozen=True, slots=True)
class PublishValidationResult:
    """Outcome of the single authoritative publication validation path."""

    normalized_value: Any
    normalized_unit: str | None
    product_type_definition_id: int
    source_id: str
    confidence: Decimal | None


def recorder_from_user(user: User) -> str:
    return f"user:{user.id}"


def is_public_fact_status(status_value: str) -> bool:
    return status_value in PUBLIC_FACT_STATUSES


def _require_source_id(source_id: str) -> str:
    cleaned = (source_id or "").strip()
    if not cleaned:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="source_id is required provenance identity (not Evidence FK yet)",
            details=[{"field": "source_id", "message": "required non-empty"}],
        )
    return cleaned


def _validate_confidence(confidence: Decimal | float | None) -> Decimal | None:
    if confidence is None:
        return None
    value = Decimal(str(confidence))
    if value < 0 or value > 1:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="confidence must be between 0 and 1",
            details=[{"field": "confidence", "message": "0 <= confidence <= 1"}],
        )
    return value


async def _get_product(db: AsyncSession, product_id: int) -> Product:
    product = await db.get(Product, product_id)
    if product is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product not found",
            details=[{"field": "product_id", "message": "not found"}],
        )
    return product


async def _get_active_property(
    db: AsyncSession, definition_id: str
) -> KnowledgePropertyDefinition:
    prop = (
        await db.execute(
            select(KnowledgePropertyDefinition).where(
                KnowledgePropertyDefinition.definition_id == definition_id
            )
        )
    ).scalar_one_or_none()
    if prop is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Property Definition not found",
            details=[{"field": "definition_id", "message": "not found"}],
        )
    if prop.status != "active":
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Property Definition must be active",
            details=[{"field": "definition_id", "message": f"status={prop.status}"}],
        )
    return prop


async def _list_units_for_dimension(
    db: AsyncSession, dimension: str | None
) -> list[KnowledgeUnit]:
    if not dimension:
        return []
    return list(
        (
            await db.execute(
                select(KnowledgeUnit).where(KnowledgeUnit.dimension == dimension)
            )
        )
        .scalars()
        .all()
    )


async def _get_active_definition(
    db: AsyncSession, product_type_id: int
) -> ProductTypeDefinition | None:
    return (
        await db.execute(
            select(ProductTypeDefinition)
            .where(
                ProductTypeDefinition.product_type_id == product_type_id,
                ProductTypeDefinition.status
                == ProductTypeDefinitionStatus.ACTIVE.value,
            )
            .options(selectinload(ProductTypeDefinition.memberships))
        )
    ).scalar_one_or_none()


def _membership_for(
    definition: ProductTypeDefinition | None, property_definition_id: str
) -> ProductTypeAttributeMembership | None:
    if definition is None:
        return None
    for m in definition.memberships:
        if m.property_definition_id == property_definition_id:
            return m
    return None


def _assert_applicability_for_write(
    *,
    product: Product,
    active_definition: ProductTypeDefinition | None,
    membership: ProductTypeAttributeMembership | None,
    property_definition_id: str,
) -> None:
    """Asserted/disputed Facts: enforce forbidden/missing membership when Definition exists."""
    if product.product_type_id is None:
        return
    if active_definition is None:
        return
    if membership is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=(
                "Property is not a member of the Product's active Product Type Definition"
            ),
            details=[
                {
                    "field": "definition_id",
                    "message": property_definition_id,
                }
            ],
        )
    if membership.requiredness == MembershipRequiredness.FORBIDDEN.value:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Property is forbidden for this Product Type Definition",
            details=[{"field": "definition_id", "message": "forbidden membership"}],
        )


def _evaluate_conditional_or_fail(
    membership: ProductTypeAttributeMembership,
) -> None:
    """Fail closed: PT-W2 stores conditions but has no rules engine yet."""
    if membership.requiredness != MembershipRequiredness.CONDITIONAL.value:
        return
    raise api_error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        error_code="FACT_APPLICABILITY_UNRESOLVED",
        message=(
            "conditional membership applicability cannot be deterministically "
            "evaluated; publication fails closed until a rules engine exists"
        ),
        details=[
            {
                "field": "applicability_condition",
                "message": "unresolved conditional membership",
            }
        ],
    )


async def _append_revision(
    db: AsyncSession,
    fact: KnowledgeFact,
    *,
    change_reason: str | None,
) -> KnowledgeFactRevision:
    """Append next revision. Caller MUST hold Fact row lock for existing Facts."""
    current_max = (
        await db.execute(
            select(func.max(KnowledgeFactRevision.revision_number)).where(
                KnowledgeFactRevision.fact_id == fact.id
            )
        )
    ).scalar_one()
    next_rev = 1 if current_max is None else int(current_max) + 1
    revision = KnowledgeFactRevision(
        fact_id=fact.id,
        revision_number=next_rev,
        value=fact.value,
        unit=fact.unit,
        qualifier=fact.qualifier,
        status=fact.status,
        source_id=fact.source_id,
        confidence=fact.confidence,
        product_type_definition_id=fact.product_type_definition_id,
        recorded_at=fact.recorded_at,
        recorder=fact.recorder,
        change_reason=change_reason,
    )
    db.add(revision)
    await db.flush()
    return revision


async def get_fact(db: AsyncSession, fact_id: int) -> KnowledgeFact:
    fact = await db.get(KnowledgeFact, fact_id)
    if fact is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Fact not found",
            details=[{"field": "fact_id", "message": "not found"}],
        )
    return fact


async def get_fact_for_update(db: AsyncSession, fact_id: int) -> KnowledgeFact:
    """Load Fact with row lock to serialize mutations/revision numbering."""
    fact = (
        await db.execute(
            select(KnowledgeFact)
            .where(KnowledgeFact.id == fact_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if fact is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Fact not found",
            details=[{"field": "fact_id", "message": "not found"}],
        )
    return fact


async def list_facts_for_product(
    db: AsyncSession,
    product_id: int,
    *,
    public_only: bool = False,
) -> list[KnowledgeFact]:
    await _get_product(db, product_id)
    stmt = select(KnowledgeFact).where(KnowledgeFact.entity_id == product_id)
    if public_only:
        stmt = stmt.where(KnowledgeFact.status == "published")
    stmt = stmt.order_by(KnowledgeFact.id)
    return list((await db.execute(stmt)).scalars().all())


async def list_revisions(
    db: AsyncSession, fact_id: int
) -> list[KnowledgeFactRevision]:
    await get_fact(db, fact_id)
    return list(
        (
            await db.execute(
                select(KnowledgeFactRevision)
                .where(KnowledgeFactRevision.fact_id == fact_id)
                .order_by(KnowledgeFactRevision.revision_number)
            )
        )
        .scalars()
        .all()
    )


async def validate_publish_candidate(
    db: AsyncSession,
    *,
    entity_id: int,
    definition_id: str,
    value: Any,
    unit: str | None,
    source_id: str,
    confidence: Decimal | float | None,
    fact_id: int | None = None,
) -> PublishValidationResult:
    """Single authoritative publication validation path (candidate-first; no ORM mutate)."""
    product = await _get_product(db, entity_id)
    prop = await _get_active_property(db, definition_id)
    source = _require_source_id(source_id)
    conf = _validate_confidence(confidence)

    if product.product_type_id is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Cannot publish Fact for Product without product_type_id",
            details=[{"field": "product_type_id", "message": "required for publish"}],
        )

    active_definition = await _get_active_definition(db, product.product_type_id)
    if active_definition is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Cannot publish Fact without an active Product Type Definition",
            details=[
                {
                    "field": "product_type_definition_id",
                    "message": "no active Definition",
                }
            ],
        )

    membership = _membership_for(active_definition, definition_id)
    if membership is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Property is not a member of the active Product Type Definition",
            details=[{"field": "definition_id", "message": "missing membership"}],
        )
    if membership.requiredness == MembershipRequiredness.FORBIDDEN.value:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Cannot publish forbidden Property for this Product Type",
            details=[{"field": "definition_id", "message": "forbidden"}],
        )
    _evaluate_conditional_or_fail(membership)

    # Evidence requirement (Prompt 13):
    #   required     → at least one FACT_SUPPORTED_BY link to an existing Artifact
    #   recommended  → publish allowed without Evidence
    #   not_required → publish allowed without Evidence
    #   null         → default: no Evidence gate
    if membership.evidence_requirement_override == "required":
        resolved_fact_id = fact_id
        if resolved_fact_id is None:
            resolved_fact_id = await db.scalar(
                select(KnowledgeFact.id).where(
                    KnowledgeFact.entity_id == entity_id,
                    KnowledgeFact.definition_id == definition_id,
                )
            )
        has_evidence = False
        if resolved_fact_id is not None:
            has_evidence = await evidence_service.fact_has_supporting_evidence(
                db, resolved_fact_id
            )
        if not has_evidence:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=(
                    "Membership requires Evidence before publish; "
                    "link a FACT_SUPPORTED_BY Evidence Artifact to this Fact"
                ),
                details=[
                    {
                        "field": "evidence_requirement_override",
                        "message": "required",
                    }
                ],
            )

    units = await _list_units_for_dimension(db, prop.unit_dimension)
    normalized, resolved_unit = validate_fact_payload(
        property_definition=prop,
        value=value,
        unit=unit,
        units=units,
        overrides=membership.validation_overrides,
        for_publish=True,
    )
    return PublishValidationResult(
        normalized_value=normalized,
        normalized_unit=resolved_unit,
        product_type_definition_id=active_definition.id,
        source_id=source,
        confidence=conf,
    )


async def create_fact(
    db: AsyncSession,
    *,
    product_id: int,
    definition_id: str,
    value: Any,
    unit: str | None,
    qualifier: str | None,
    source_id: str,
    confidence: Decimal | float | None,
    actor: User,
) -> KnowledgeFact:
    product = await _get_product(db, product_id)
    prop = await _get_active_property(db, definition_id)
    source = _require_source_id(source_id)
    conf = _validate_confidence(confidence)

    active_definition: ProductTypeDefinition | None = None
    membership: ProductTypeAttributeMembership | None = None
    if product.product_type_id is not None:
        active_definition = await _get_active_definition(db, product.product_type_id)
        membership = _membership_for(active_definition, definition_id)
    _assert_applicability_for_write(
        product=product,
        active_definition=active_definition,
        membership=membership,
        property_definition_id=definition_id,
    )

    units = await _list_units_for_dimension(db, prop.unit_dimension)
    overrides = membership.validation_overrides if membership else None
    normalized, resolved_unit = validate_fact_payload(
        property_definition=prop,
        value=value,
        unit=unit,
        units=units,
        overrides=overrides,
        for_publish=False,
    )

    now = datetime.now(UTC)
    fact = KnowledgeFact(
        entity_id=product.id,
        definition_id=definition_id,
        product_type_definition_id=(
            active_definition.id if active_definition is not None else None
        ),
        value=normalized,
        unit=resolved_unit,
        qualifier=qualifier,
        status="asserted",
        source_id=source,
        confidence=conf,
        recorded_at=now,
        recorder=recorder_from_user(actor),
    )
    db.add(fact)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="A Fact already exists for this Product and Property",
            details=[
                {
                    "field": "definition_id",
                    "message": f"entity_id={product_id} definition_id={definition_id}",
                }
            ],
        ) from exc
    await _append_revision(db, fact, change_reason="create")
    await db.refresh(fact)
    return fact


async def update_fact(
    db: AsyncSession,
    *,
    fact_id: int,
    patch: dict[str, Any],
    actor: User,
    change_reason: str | None = None,
) -> KnowledgeFact:
    fact = await get_fact_for_update(db, fact_id)
    if fact.status == "deprecated":
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Deprecated Facts cannot be mutated in Prompt 12",
            details=[{"field": "status", "message": "deprecated"}],
        )
    if "status" in patch:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="status changes require explicit lifecycle endpoints",
            details=[{"field": "status", "message": "not allowed on update"}],
        )

    # Candidate-first: assemble proposed state before any ORM mutation.
    candidate_value = patch["value"] if "value" in patch else fact.value
    candidate_unit = patch["unit"] if "unit" in patch else fact.unit
    candidate_qualifier = (
        patch["qualifier"] if "qualifier" in patch else fact.qualifier
    )
    candidate_source = (
        _require_source_id(patch["source_id"])
        if "source_id" in patch
        else fact.source_id
    )
    candidate_confidence = (
        _validate_confidence(patch.get("confidence"))
        if "confidence" in patch
        else fact.confidence
    )

    if fact.status == "published":
        reason = (change_reason or "").strip()
        if not reason:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="change_reason is required when updating a published Fact",
                details=[{"field": "change_reason", "message": "required"}],
            )
        publish_result = await validate_publish_candidate(
            db,
            entity_id=fact.entity_id,
            definition_id=fact.definition_id,
            value=candidate_value,
            unit=candidate_unit,
            source_id=candidate_source,
            confidence=candidate_confidence,
            fact_id=fact.id,
        )
        fact.value = publish_result.normalized_value
        fact.unit = publish_result.normalized_unit
        fact.qualifier = candidate_qualifier
        fact.source_id = publish_result.source_id
        fact.confidence = publish_result.confidence
        fact.product_type_definition_id = publish_result.product_type_definition_id
        # status remains published
        fact.recorded_at = datetime.now(UTC)
        fact.recorder = recorder_from_user(actor)
        await db.flush()
        await _append_revision(db, fact, change_reason=reason)
        await db.refresh(fact)
        return fact

    # asserted / disputed: assertion-time validation (not full publish gate)
    product = await _get_product(db, fact.entity_id)
    prop = await _get_active_property(db, fact.definition_id)
    active_definition: ProductTypeDefinition | None = None
    membership: ProductTypeAttributeMembership | None = None
    if product.product_type_id is not None:
        active_definition = await _get_active_definition(db, product.product_type_id)
        membership = _membership_for(active_definition, fact.definition_id)
    _assert_applicability_for_write(
        product=product,
        active_definition=active_definition,
        membership=membership,
        property_definition_id=fact.definition_id,
    )

    units = await _list_units_for_dimension(db, prop.unit_dimension)
    overrides = membership.validation_overrides if membership else None
    normalized, resolved_unit = validate_fact_payload(
        property_definition=prop,
        value=candidate_value,
        unit=candidate_unit,
        units=units,
        overrides=overrides,
        for_publish=False,
    )

    fact.value = normalized
    fact.unit = resolved_unit
    fact.qualifier = candidate_qualifier
    fact.source_id = candidate_source
    fact.confidence = candidate_confidence
    if fact.status == "asserted" and active_definition is not None:
        fact.product_type_definition_id = active_definition.id
    fact.recorded_at = datetime.now(UTC)
    fact.recorder = recorder_from_user(actor)
    await db.flush()
    await _append_revision(
        db,
        fact,
        change_reason=(change_reason or "update").strip() or "update",
    )
    await db.refresh(fact)
    return fact


async def _transition(
    db: AsyncSession,
    *,
    fact_id: int,
    to_status: str,
    actor: User,
    change_reason: str,
) -> KnowledgeFact:
    if to_status not in FACT_STATUSES:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="invalid Fact status",
            details=[{"field": "status", "message": to_status}],
        )
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )

    fact = await get_fact_for_update(db, fact_id)
    allowed = ALLOWED_TRANSITIONS.get(fact.status, frozenset())
    if to_status not in allowed:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=f"Cannot transition Fact from '{fact.status}' to '{to_status}'",
            details=[
                {
                    "field": "status",
                    "message": f"allowed={sorted(allowed)}",
                }
            ],
        )

    if to_status == "published":
        publish_result = await validate_publish_candidate(
            db,
            entity_id=fact.entity_id,
            definition_id=fact.definition_id,
            value=fact.value,
            unit=fact.unit,
            source_id=fact.source_id,
            confidence=fact.confidence,
            fact_id=fact.id,
        )
        fact.value = publish_result.normalized_value
        fact.unit = publish_result.normalized_unit
        fact.source_id = publish_result.source_id
        fact.confidence = publish_result.confidence
        fact.product_type_definition_id = publish_result.product_type_definition_id

    fact.status = to_status
    fact.recorded_at = datetime.now(UTC)
    fact.recorder = recorder_from_user(actor)
    await db.flush()
    await _append_revision(db, fact, change_reason=reason)
    await db.refresh(fact)
    return fact


async def publish_fact(
    db: AsyncSession,
    *,
    fact_id: int,
    actor: User,
    change_reason: str,
) -> KnowledgeFact:
    return await _transition(
        db,
        fact_id=fact_id,
        to_status="published",
        actor=actor,
        change_reason=change_reason,
    )


async def dispute_fact(
    db: AsyncSession,
    *,
    fact_id: int,
    actor: User,
    change_reason: str,
) -> KnowledgeFact:
    return await _transition(
        db,
        fact_id=fact_id,
        to_status="disputed",
        actor=actor,
        change_reason=change_reason,
    )


async def deprecate_fact(
    db: AsyncSession,
    *,
    fact_id: int,
    actor: User,
    change_reason: str,
) -> KnowledgeFact:
    return await _transition(
        db,
        fact_id=fact_id,
        to_status="deprecated",
        actor=actor,
        change_reason=change_reason,
    )
