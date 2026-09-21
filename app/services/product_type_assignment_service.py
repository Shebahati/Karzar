"""Reviewed Product Type assignment (PT-W3A).

Manual assign / reassign / clear only. No Category/title inference.
Locks Product row FOR UPDATE. Does not mutate Facts or legacy JSONB.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, api_error
from app.crud import audit as crud_audit
from app.crud import product_type_definition as ptd_crud
from app.db.models.knowledge import KnowledgeFact, KnowledgePropertyDefinition, KnowledgeUnit
from app.db.models.product import Product
from app.db.models.product_type import (
    MembershipRequiredness,
    ProductType,
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
    ProductTypeStatus,
)
from app.db.models.user import User
from app.services.audit_service import record_audit
from app.services.fact_validation import validate_fact_payload

COMPATIBILITY_FACT_STATUSES = frozenset({"asserted", "disputed"})


async def get_product_for_update(db: AsyncSession, product_id: int) -> Product:
    product = (
        await db.execute(
            select(Product).where(Product.id == product_id).with_for_update()
        )
    ).scalar_one_or_none()
    if product is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product not found",
            details=[{"field": "product_id", "message": "not found"}],
        )
    return product


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


def _require_change_reason(change_reason: str) -> str:
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )
    return reason


def _membership_for(
    definition: ProductTypeDefinition,
    property_definition_id: str,
) -> ProductTypeAttributeMembership | None:
    for m in definition.memberships:
        if m.property_definition_id == property_definition_id:
            return m
    return None


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


async def _load_active_definition_with_memberships(
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


async def _count_published_facts(db: AsyncSession, product_id: int) -> int:
    rows = (
        await db.execute(
            select(KnowledgeFact.id).where(
                KnowledgeFact.entity_id == product_id,
                KnowledgeFact.status == "published",
            )
        )
    ).all()
    return len(rows)


async def _load_compatibility_facts(
    db: AsyncSession, product_id: int
) -> list[KnowledgeFact]:
    return list(
        (
            await db.execute(
                select(KnowledgeFact).where(
                    KnowledgeFact.entity_id == product_id,
                    KnowledgeFact.status.in_(COMPATIBILITY_FACT_STATUSES),
                )
            )
        )
        .scalars()
        .all()
    )


async def _validate_assignment_target(
    db: AsyncSession, product_type_id: int
) -> tuple[ProductType, ProductTypeDefinition]:
    pt = await db.get(ProductType, product_type_id)
    if pt is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Product Type not found",
            details=[{"field": "product_type_id", "message": "not found"}],
        )
    if pt.status != ProductTypeStatus.ACTIVE.value:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Only an active Product Type may be assigned",
            details=[
                {
                    "field": "product_type_id",
                    "message": f"status={pt.status}",
                }
            ],
        )
    definition = await _load_active_definition_with_memberships(db, product_type_id)
    if definition is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Product Type has no active Definition; cannot assign",
            details=[
                {
                    "field": "product_type_id",
                    "message": "no active Product Type Definition",
                }
            ],
        )
    return pt, definition


async def _preflight_facts_against_definition(
    db: AsyncSession,
    *,
    product_id: int,
    definition: ProductTypeDefinition,
) -> None:
    """Validate asserted/disputed Facts against target Definition.

    Conditional membership does not require condition resolution for
    assignment (Facts may remain internal). Deprecated Facts are ignored.
    Does not mutate Facts.
    """
    facts = await _load_compatibility_facts(db, product_id)
    if not facts:
        return

    incompatibilities: list[dict[str, Any]] = []
    for fact in facts:
        membership = _membership_for(definition, fact.definition_id)
        if membership is None:
            incompatibilities.append(
                {
                    "field": f"fact_id={fact.id}",
                    "message": (
                        f"definition_id={fact.definition_id}; "
                        "reason=missing membership"
                    ),
                }
            )
            continue
        if membership.requiredness == MembershipRequiredness.FORBIDDEN.value:
            incompatibilities.append(
                {
                    "field": f"fact_id={fact.id}",
                    "message": (
                        f"definition_id={fact.definition_id}; "
                        "reason=forbidden membership"
                    ),
                }
            )
            continue

        prop = (
            await db.execute(
                select(KnowledgePropertyDefinition).where(
                    KnowledgePropertyDefinition.definition_id == fact.definition_id
                )
            )
        ).scalar_one_or_none()
        if prop is None or prop.status != "active":
            incompatibilities.append(
                {
                    "field": f"fact_id={fact.id}",
                    "message": (
                        f"definition_id={fact.definition_id}; "
                        "reason=property not active"
                    ),
                }
            )
            continue

        units = await _list_units_for_dimension(db, prop.unit_dimension)
        try:
            validate_fact_payload(
                property_definition=prop,
                value=fact.value,
                unit=fact.unit,
                units=units,
                overrides=membership.validation_overrides,
                for_publish=False,
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            reason = str(
                detail.get("message")
                or "value/unit/constraint incompatible with target Definition"
            )
            incompatibilities.append(
                {
                    "field": f"fact_id={fact.id}",
                    "message": (
                        f"definition_id={fact.definition_id}; reason={reason}"
                    ),
                }
            )

    if incompatibilities:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=(
                "One or more asserted/disputed Facts are incompatible with the "
                "target Product Type Definition; clean Facts before assignment"
            ),
            details=incompatibilities,
        )


async def get_assignment(
    db: AsyncSession, product_id: int
) -> dict[str, Any]:
    product = await _get_product(db, product_id)
    current_id = product.product_type_id
    result: dict[str, Any] = {
        "product_id": product.id,
        "current_product_type_id": current_id,
        "product_type": None,
        "active_definition_id": None,
    }
    if current_id is None:
        return result

    pt = await db.get(ProductType, current_id)
    if pt is None:
        return result

    active = await ptd_crud.get_active_definition_for_product_type(db, current_id)
    result["product_type"] = {
        "id": pt.id,
        "code": pt.code,
        "slug": pt.slug,
        "name_fa": pt.name_fa,
        "name_en": pt.name_en,
        "status": pt.status,
    }
    result["active_definition_id"] = active.id if active is not None else None
    return result


async def assign_product_type(
    db: AsyncSession,
    *,
    product_id: int,
    product_type_id: int | None,
    change_reason: str,
    actor: User,
) -> dict[str, Any]:
    """Assign, reassign, or clear product_type_id with Fact-safety gates.

    Idempotent when old == new (no audit spam). Never mutates Facts or JSONB.
    """
    reason = _require_change_reason(change_reason)
    product = await get_product_for_update(db, product_id)
    old_id = product.product_type_id

    # Idempotent no-op
    if old_id == product_type_id:
        return await get_assignment(db, product_id)

    published_count = await _count_published_facts(db, product_id)

    if product_type_id is None:
        # Clear
        if published_count > 0:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message=(
                    "Cannot clear Product Type while published Facts exist; "
                    "explicit reclassification workflow required"
                ),
                details=[
                    {
                        "field": "product_type_id",
                        "message": f"published_facts={published_count}",
                    }
                ],
            )
        product.product_type_id = None
        action = "product_type.clear"
    else:
        # Assign / reassign
        if old_id is not None and published_count > 0:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message=(
                    "Cannot reassign Product Type while published Facts exist; "
                    "explicit reclassification workflow required"
                ),
                details=[
                    {
                        "field": "product_type_id",
                        "message": (
                            f"current={old_id} requested={product_type_id} "
                            f"published_facts={published_count}"
                        ),
                    }
                ],
            )

        _pt, definition = await _validate_assignment_target(db, product_type_id)
        await _preflight_facts_against_definition(
            db, product_id=product_id, definition=definition
        )
        product.product_type_id = product_type_id
        action = (
            "product_type.reassign" if old_id is not None else "product_type.assign"
        )

    await db.flush()

    await crud_audit.record_product_change(
        db,
        product_id=product.id,
        field_name="product_type_id",
        old_value=str(old_id) if old_id is not None else None,
        new_value=str(product_type_id) if product_type_id is not None else None,
        reason=reason,
        actor_user_id=actor.id,
    )
    await record_audit(
        db,
        actor_user_id=actor.id,
        action=action,
        entity_type="product",
        entity_id=product.id,
        details={
            "change_reason": reason,
            "old_product_type_id": old_id,
            "new_product_type_id": product_type_id,
        },
    )
    return await get_assignment(db, product_id)
