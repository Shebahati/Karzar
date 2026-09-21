"""Product Type Definition lifecycle + Attribute Memberships (PT-W2).

Ownership boundary:
  Property Dictionary owns canonical property identity/meaning.
  Product Type Definition owns whether/how that property applies to a Product Type.
  Product Fact (later) owns the product-specific value.

No Facts, Evidence, assignment, readout persistence, or JSONB dual-write.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.crud import product_type_definition as ptd_crud
from app.db.models.knowledge import KnowledgePropertyDefinition
from app.db.models.product_type import (
    ALLOWED_VALIDATION_OVERRIDE_KEYS,
    EVIDENCE_REQUIREMENT_OVERRIDES,
    FORBIDDEN_VALIDATION_OVERRIDE_KEYS,
    MEMBERSHIP_REQUIREDNESS,
    MembershipRequiredness,
    ProductType,
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
)
from app.db.models.user import User

# Activation requires Property Dictionary status=active (11A draft|active|deprecated).
# Draft authoring may reference draft properties; activation rejects draft + deprecated.
ACTIVATION_ALLOWED_PROPERTY_STATUSES = frozenset({"active"})
DRAFT_ALLOWED_PROPERTY_STATUSES = frozenset({"draft", "active"})


def _require_draft(definition: ProductTypeDefinition) -> None:
    if definition.status != ProductTypeDefinitionStatus.DRAFT.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=(
                "Product Type Definition is immutable once active or retired; "
                "create a new draft version to change memberships"
            ),
            details=[
                {
                    "field": "status",
                    "message": f"current status is '{definition.status}'",
                }
            ],
        )


def _validate_requiredness(requiredness: str) -> str:
    if requiredness not in MEMBERSHIP_REQUIREDNESS:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="invalid membership requiredness",
            details=[
                {
                    "field": "requiredness",
                    "message": f"allowed={sorted(MEMBERSHIP_REQUIREDNESS)}",
                }
            ],
        )
    return requiredness


def _validate_applicability_condition(
    requiredness: str,
    condition: dict[str, Any] | None,
) -> dict[str, Any]:
    cond = condition if isinstance(condition, dict) else {}
    if requiredness == MembershipRequiredness.CONDITIONAL.value:
        if not cond:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=(
                    "conditional memberships require a non-empty "
                    "machine-readable applicability_condition object"
                ),
                details=[{"field": "applicability_condition", "message": "required"}],
            )
    if not isinstance(cond, dict):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="applicability_condition must be a JSON object",
            details=[{"field": "applicability_condition", "message": "must be object"}],
        )
    return cond


def _validate_validation_overrides(overrides: dict[str, Any] | None) -> dict[str, Any]:
    data = overrides if isinstance(overrides, dict) else {}
    if not isinstance(data, dict):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="validation_overrides must be a JSON object",
            details=[{"field": "validation_overrides", "message": "must be object"}],
        )
    for key in data:
        if key in FORBIDDEN_VALIDATION_OVERRIDE_KEYS:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=(
                    "validation_overrides must not redefine canonical property identity"
                ),
                details=[
                    {
                        "field": f"validation_overrides.{key}",
                        "message": "forbidden identity key",
                    }
                ],
            )
        if key not in ALLOWED_VALIDATION_OVERRIDE_KEYS:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="unknown validation_overrides key",
                details=[
                    {
                        "field": f"validation_overrides.{key}",
                        "message": (
                            f"allowed={sorted(ALLOWED_VALIDATION_OVERRIDE_KEYS)}"
                        ),
                    }
                ],
            )
    return data


def _validate_evidence_override(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in EVIDENCE_REQUIREMENT_OVERRIDES:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="invalid evidence_requirement_override",
            details=[
                {
                    "field": "evidence_requirement_override",
                    "message": f"allowed={sorted(EVIDENCE_REQUIREMENT_OVERRIDES)}",
                }
            ],
        )
    return value


async def _get_product_type_or_404(
    db: AsyncSession, product_type_id: int
) -> ProductType:
    pt = (
        await db.execute(select(ProductType).where(ProductType.id == product_type_id))
    ).scalar_one_or_none()
    if pt is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product Type not found",
            details=[{"field": "product_type_id", "message": "not found"}],
        )
    return pt


async def _get_property_for_draft(
    db: AsyncSession, property_definition_id: str
) -> KnowledgePropertyDefinition:
    prop = (
        await db.execute(
            select(KnowledgePropertyDefinition).where(
                KnowledgePropertyDefinition.definition_id == property_definition_id
            )
        )
    ).scalar_one_or_none()
    if prop is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="canonical Property Definition not found",
            details=[
                {
                    "field": "property_definition_id",
                    "message": f"unknown id '{property_definition_id}'",
                }
            ],
        )
    if prop.status not in DRAFT_ALLOWED_PROPERTY_STATUSES:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=(
                "draft memberships may only reference draft or active "
                "Property Definitions (deprecated rejected)"
            ),
            details=[
                {
                    "field": "property_definition_id",
                    "message": f"status is '{prop.status}'",
                }
            ],
        )
    return prop


async def create_draft_definition(
    db: AsyncSession,
    *,
    product_type_id: int,
    notes: str | None = None,
    version: int | None = None,
) -> ProductTypeDefinition:
    """Create a draft Definition. Does not mutate any active Definition.

    Version rule: if omitted, next_version = max(existing) + 1 (or 1 if none).
    Caller-supplied version must be unique for the Product Type.
    """
    await _get_product_type_or_404(db, product_type_id)

    if version is None:
        current_max = await ptd_crud.max_version_for_product_type(db, product_type_id)
        version = 1 if current_max is None else int(current_max) + 1
    elif version < 1:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="version must be >= 1",
            details=[{"field": "version", "message": "must be >= 1"}],
        )

    definition = ProductTypeDefinition(
        product_type_id=product_type_id,
        version=version,
        status=ProductTypeDefinitionStatus.DRAFT.value,
        notes=notes,
    )
    db.add(definition)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Definition version already exists for this Product Type",
            details=[
                {
                    "field": "version",
                    "message": f"product_type_id={product_type_id} version={version}",
                }
            ],
        ) from exc
    await db.refresh(definition)
    return definition


async def get_definition(
    db: AsyncSession, definition_id: int
) -> ProductTypeDefinition:
    definition = await ptd_crud.get_definition(
        db, definition_id, with_memberships=True
    )
    if definition is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product Type Definition not found",
            details=[{"field": "definition_id", "message": "not found"}],
        )
    return definition


async def list_definitions(
    db: AsyncSession, product_type_id: int
) -> list[ProductTypeDefinition]:
    await _get_product_type_or_404(db, product_type_id)
    return await ptd_crud.list_definitions_for_product_type(db, product_type_id)


async def add_membership(
    db: AsyncSession,
    *,
    definition_id: int,
    property_definition_id: str,
    requiredness: str,
    applicability_condition: dict[str, Any] | None = None,
    validation_overrides: dict[str, Any] | None = None,
    public_visibility_default: bool | None = None,
    filterable: bool | None = None,
    comparable: bool | None = None,
    display_group: str | None = None,
    display_order: int | None = None,
    evidence_requirement_override: str | None = None,
) -> ProductTypeAttributeMembership:
    definition = await ptd_crud.get_definition(
        db, definition_id, with_memberships=False, for_update=True
    )
    if definition is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product Type Definition not found",
            details=[{"field": "definition_id", "message": "not found"}],
        )
    _require_draft(definition)
    requiredness = _validate_requiredness(requiredness)
    condition = _validate_applicability_condition(
        requiredness, applicability_condition
    )
    overrides = _validate_validation_overrides(validation_overrides)
    evidence = _validate_evidence_override(evidence_requirement_override)
    await _get_property_for_draft(db, property_definition_id)

    membership = ProductTypeAttributeMembership(
        product_type_definition_id=definition.id,
        property_definition_id=property_definition_id,
        requiredness=requiredness,
        applicability_condition=condition,
        validation_overrides=overrides,
        public_visibility_default=public_visibility_default,
        filterable=filterable,
        comparable=comparable,
        display_group=display_group,
        display_order=display_order,
        evidence_requirement_override=evidence,
    )
    db.add(membership)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Property already a member of this Definition",
            details=[
                {
                    "field": "property_definition_id",
                    "message": property_definition_id,
                }
            ],
        ) from exc
    await db.refresh(membership)
    return membership


async def update_membership(
    db: AsyncSession,
    *,
    definition_id: int,
    membership_id: int,
    patch: dict[str, Any],
) -> ProductTypeAttributeMembership:
    definition = await ptd_crud.get_definition(
        db, definition_id, for_update=True
    )
    if definition is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product Type Definition not found",
            details=[{"field": "definition_id", "message": "not found"}],
        )
    _require_draft(definition)

    membership = await ptd_crud.get_membership(db, membership_id, for_update=True)
    if (
        membership is None
        or membership.product_type_definition_id != definition_id
    ):
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Membership not found on this Definition",
            details=[{"field": "membership_id", "message": "not found"}],
        )

    if "property_definition_id" in patch and patch["property_definition_id"] is not None:
        new_prop_id = patch["property_definition_id"]
        await _get_property_for_draft(db, new_prop_id)
        membership.property_definition_id = new_prop_id

    requiredness = membership.requiredness
    if "requiredness" in patch and patch["requiredness"] is not None:
        requiredness = _validate_requiredness(patch["requiredness"])
        membership.requiredness = requiredness

    if "applicability_condition" in patch:
        membership.applicability_condition = _validate_applicability_condition(
            requiredness, patch["applicability_condition"]
        )
    else:
        # Re-validate when requiredness alone changes to conditional.
        membership.applicability_condition = _validate_applicability_condition(
            requiredness, membership.applicability_condition
        )

    if "validation_overrides" in patch:
        membership.validation_overrides = _validate_validation_overrides(
            patch["validation_overrides"]
        )

    for field in (
        "public_visibility_default",
        "filterable",
        "comparable",
        "display_group",
        "display_order",
    ):
        if field in patch:
            setattr(membership, field, patch[field])

    if "evidence_requirement_override" in patch:
        membership.evidence_requirement_override = _validate_evidence_override(
            patch["evidence_requirement_override"]
        )

    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Property already a member of this Definition",
            details=[{"field": "property_definition_id", "message": "duplicate"}],
        ) from exc
    await db.refresh(membership)
    return membership


async def remove_membership(
    db: AsyncSession,
    *,
    definition_id: int,
    membership_id: int,
) -> None:
    definition = await ptd_crud.get_definition(db, definition_id, for_update=True)
    if definition is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product Type Definition not found",
            details=[{"field": "definition_id", "message": "not found"}],
        )
    _require_draft(definition)

    membership = await ptd_crud.get_membership(db, membership_id, for_update=True)
    if (
        membership is None
        or membership.product_type_definition_id != definition_id
    ):
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Membership not found on this Definition",
            details=[{"field": "membership_id", "message": "not found"}],
        )
    await db.delete(membership)
    await db.flush()


async def _validate_memberships_for_activation(
    db: AsyncSession,
    memberships: list[ProductTypeAttributeMembership],
) -> None:
    seen: set[str] = set()
    for m in memberships:
        if m.property_definition_id in seen:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Definition contains duplicate property memberships",
                details=[
                    {
                        "field": "property_definition_id",
                        "message": m.property_definition_id,
                    }
                ],
            )
        seen.add(m.property_definition_id)

        _validate_requiredness(m.requiredness)
        _validate_applicability_condition(m.requiredness, m.applicability_condition)
        _validate_validation_overrides(m.validation_overrides)
        _validate_evidence_override(m.evidence_requirement_override)

        prop = (
            await db.execute(
                select(KnowledgePropertyDefinition).where(
                    KnowledgePropertyDefinition.definition_id
                    == m.property_definition_id
                )
            )
        ).scalar_one_or_none()
        if prop is None:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="activation references missing Property Definition",
                details=[
                    {
                        "field": "property_definition_id",
                        "message": m.property_definition_id,
                    }
                ],
            )
        if prop.status not in ACTIVATION_ALLOWED_PROPERTY_STATUSES:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=(
                    "activation requires all membership Property Definitions "
                    "to have status=active (draft and deprecated rejected)"
                ),
                details=[
                    {
                        "field": "property_definition_id",
                        "message": (
                            f"{m.property_definition_id} status={prop.status}"
                        ),
                    }
                ],
            )


async def activate_definition(
    db: AsyncSession,
    *,
    definition_id: int,
    reviewer: User,
    change_reason: str,
) -> ProductTypeDefinition:
    """Transactional activation: retire prior active, activate draft.

    Order (single transaction, caller commits):
      1. Lock draft Definition
      2. Verify draft + validate memberships
      3. Lock + retire existing active (if any)
      4. Flush retire
      5. Activate draft with reviewer/reason/timestamp
      6. Flush activate

    Failure rolls back — never leaves zero-active from a half-applied swap,
    and the partial unique index blocks two-active on Postgres.
    """
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required for activation",
            details=[{"field": "change_reason", "message": "required"}],
        )

    definition = await ptd_crud.get_definition(
        db, definition_id, with_memberships=True, for_update=True
    )
    if definition is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product Type Definition not found",
            details=[{"field": "definition_id", "message": "not found"}],
        )

    await _get_product_type_or_404(db, definition.product_type_id)

    if definition.status != ProductTypeDefinitionStatus.DRAFT.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only a draft Definition may be activated",
            details=[
                {
                    "field": "status",
                    "message": f"current status is '{definition.status}'",
                }
            ],
        )

    memberships = list(definition.memberships)
    await _validate_memberships_for_activation(db, memberships)

    prior = await ptd_crud.get_active_definition_for_product_type(
        db, definition.product_type_id, for_update=True
    )
    if prior is not None and prior.id != definition.id:
        prior.status = ProductTypeDefinitionStatus.RETIRED.value
        await db.flush()

    definition.status = ProductTypeDefinitionStatus.ACTIVE.value
    definition.change_reason = reason
    definition.reviewed_by_user_id = reviewer.id
    definition.activated_at = datetime.now(UTC)

    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="One-active Definition invariant violated",
            details=[
                {
                    "field": "product_type_id",
                    "message": str(definition.product_type_id),
                }
            ],
        ) from exc

    await db.refresh(definition)
    return await get_definition(db, definition.id)
