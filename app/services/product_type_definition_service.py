"""Product Type Definition lifecycle + Attribute Memberships (PT-W2).

Ownership boundary:
  Property Dictionary owns canonical property identity/meaning.
  Product Type Definition owns whether/how that property applies to a Product Type.
  Product Fact (later) owns the product-specific value.

No Facts, Evidence, assignment, readout persistence, or JSONB dual-write.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, NoReturn

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.crud import product_type_definition as ptd_crud
from app.db.models.knowledge import KnowledgePropertyDefinition
from app.db.models.product_type import (
    ALLOWED_VALIDATION_OVERRIDE_KEYS,
    ENUM_SUBSET_DATA_TYPES,
    EVIDENCE_REQUIREMENT_OVERRIDES,
    FORBIDDEN_VALIDATION_OVERRIDE_KEYS,
    LENGTH_BOUND_DATA_TYPES,
    MEMBERSHIP_REQUIREDNESS,
    NUMERIC_BOUND_DATA_TYPES,
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
    """Store a machine-readable condition payload for later runtime evaluation.

    PT-W2 does not evaluate a rules DSL here — only requires a non-empty object
    when requiredness is conditional.
    """
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


def _override_field_error(field: str, message: str) -> NoReturn:
    raise api_error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        error_code=ErrorCode.VALIDATION_FAILED,
        message="validation_overrides violate narrowing rules",
        details=[{"field": f"validation_overrides.{field}", "message": message}],
    )


def _as_comparable_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        _override_field_error(field, "must be a number")
    return float(value)


def _as_non_negative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _override_field_error(field, "must be an integer")
    if value < 0:
        _override_field_error(field, "must be >= 0")
    return value


def _canonical_enum_codes(enum_values: list[Any] | None) -> set[str]:
    """Normalize 11A enum_values to comparable codes.

    Runtime seed shape: [{"code": "...", "label_en": "...", "label_fa": "..."}, ...]
    Also accept plain string codes for defensive compatibility.
    """
    if not enum_values:
        return set()
    codes: set[str] = set()
    for item in enum_values:
        if isinstance(item, dict):
            code = item.get("code")
            if not isinstance(code, str) or not code:
                raise api_error(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    error_code=ErrorCode.VALIDATION_FAILED,
                    message="canonical Property enum_values has invalid entries",
                    details=[
                        {
                            "field": "enum_values",
                            "message": "each entry requires non-empty string code",
                        }
                    ],
                )
            codes.add(code)
        elif isinstance(item, str) and item:
            codes.add(item)
        else:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="canonical Property enum_values has invalid entries",
                details=[{"field": "enum_values", "message": "unsupported entry shape"}],
            )
    return codes


def validate_membership_overrides(
    property_definition: KnowledgePropertyDefinition,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Enforce narrowing-only validation_overrides against a Property Definition.

    Supported keys (monotonic): min, max, min_length, max_length, enum_subset.
    Ambiguous keys are rejected rather than accepted as potentially widening.
    """
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
                message=(
                    "validation_overrides key is unsupported or lacks a proven "
                    "narrowing rule"
                ),
                details=[
                    {
                        "field": f"validation_overrides.{key}",
                        "message": (
                            f"allowed={sorted(ALLOWED_VALIDATION_OVERRIDE_KEYS)}"
                        ),
                    }
                ],
            )

    canonical = (
        property_definition.validation
        if isinstance(property_definition.validation, dict)
        else {}
    )
    data_type = property_definition.data_type

    effective_min: float | None = None
    effective_max: float | None = None
    if "min" in canonical and canonical["min"] is not None:
        effective_min = _as_comparable_number(canonical["min"], field="canonical.min")
    if "max" in canonical and canonical["max"] is not None:
        effective_max = _as_comparable_number(canonical["max"], field="canonical.max")

    if "min" in data:
        if data_type not in NUMERIC_BOUND_DATA_TYPES:
            _override_field_error(
                "min",
                f"not applicable to data_type '{data_type}'",
            )
        member_min = _as_comparable_number(data["min"], field="min")
        if effective_min is not None and member_min < effective_min:
            _override_field_error(
                "min",
                f"widens canonical min={effective_min}; membership min must be >=",
            )
        effective_min = member_min

    if "max" in data:
        if data_type not in NUMERIC_BOUND_DATA_TYPES:
            _override_field_error(
                "max",
                f"not applicable to data_type '{data_type}'",
            )
        member_max = _as_comparable_number(data["max"], field="max")
        if effective_max is not None and member_max > effective_max:
            _override_field_error(
                "max",
                f"widens canonical max={effective_max}; membership max must be <=",
            )
        effective_max = member_max

    if (
        effective_min is not None
        and effective_max is not None
        and effective_min > effective_max
    ):
        _override_field_error(
            "min",
            f"effective min ({effective_min}) > effective max ({effective_max})",
        )

    effective_min_len: int | None = None
    effective_max_len: int | None = None
    if "min_length" in canonical and canonical["min_length"] is not None:
        effective_min_len = _as_non_negative_int(
            canonical["min_length"], field="canonical.min_length"
        )
    if "max_length" in canonical and canonical["max_length"] is not None:
        effective_max_len = _as_non_negative_int(
            canonical["max_length"], field="canonical.max_length"
        )

    if "min_length" in data:
        if data_type not in LENGTH_BOUND_DATA_TYPES:
            _override_field_error(
                "min_length",
                f"not applicable to data_type '{data_type}'",
            )
        member_min_len = _as_non_negative_int(data["min_length"], field="min_length")
        if effective_min_len is not None and member_min_len < effective_min_len:
            _override_field_error(
                "min_length",
                (
                    f"widens canonical min_length={effective_min_len}; "
                    "membership min_length must be >="
                ),
            )
        effective_min_len = member_min_len

    if "max_length" in data:
        if data_type not in LENGTH_BOUND_DATA_TYPES:
            _override_field_error(
                "max_length",
                f"not applicable to data_type '{data_type}'",
            )
        member_max_len = _as_non_negative_int(data["max_length"], field="max_length")
        if effective_max_len is not None and member_max_len > effective_max_len:
            _override_field_error(
                "max_length",
                (
                    f"widens canonical max_length={effective_max_len}; "
                    "membership max_length must be <="
                ),
            )
        effective_max_len = member_max_len

    if (
        effective_min_len is not None
        and effective_max_len is not None
        and effective_min_len > effective_max_len
    ):
        _override_field_error(
            "min_length",
            (
                f"effective min_length ({effective_min_len}) > "
                f"effective max_length ({effective_max_len})"
            ),
        )

    if "enum_subset" in data:
        if data_type not in ENUM_SUBSET_DATA_TYPES:
            _override_field_error(
                "enum_subset",
                f"not applicable to data_type '{data_type}'",
            )
        subset = data["enum_subset"]
        if not isinstance(subset, list) or not subset:
            _override_field_error(
                "enum_subset",
                "must be a non-empty list of enum codes",
            )
        if not all(isinstance(code, str) and code for code in subset):
            _override_field_error(
                "enum_subset",
                "each entry must be a non-empty string code",
            )
        canonical_codes = _canonical_enum_codes(property_definition.enum_values)
        if not canonical_codes:
            _override_field_error(
                "enum_subset",
                "canonical Property has no enum_values to subset",
            )
        unknown = sorted({code for code in subset if code not in canonical_codes})
        if unknown:
            _override_field_error(
                "enum_subset",
                f"codes not in canonical enum_values: {unknown}",
            )
        # Deduplicate while preserving order for stable storage.
        data = {**data, "enum_subset": list(dict.fromkeys(subset))}

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
    evidence = _validate_evidence_override(evidence_requirement_override)
    prop = await _get_property_for_draft(db, property_definition_id)
    overrides = validate_membership_overrides(prop, validation_overrides)

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

    prop = await _get_property_for_draft(db, membership.property_definition_id)
    if "validation_overrides" in patch:
        membership.validation_overrides = validate_membership_overrides(
            prop, patch["validation_overrides"]
        )
    else:
        # Property identity may have changed — re-check stored overrides.
        membership.validation_overrides = validate_membership_overrides(
            prop, membership.validation_overrides
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
        # Revalidate narrowing against *current* canonical validation/enum_values.
        validate_membership_overrides(prop, m.validation_overrides)


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
