"""Definition-driven Wave Fact contract (Prompt 138).

Wave Fact scope is derived from the sealed Product Type Definition's
``required`` attribute memberships. Active Definitions are immutable under
``product_type_definition_service`` (memberships may only change on a new
draft version), so ``wave.definition_id`` remains a stable contract pin after
seal.

Optional / conditional / forbidden memberships are out of Wave required scope
for this contract. Conditional evaluation is not invented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge import KnowledgePropertyDefinition
from app.db.models.product_type import (
    MembershipRequiredness,
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
)

# Properties usable in a Wave Fact contract (Dictionary active only).
_USABLE_PROPERTY_STATUSES = frozenset({"active"})


@dataclass(frozen=True, slots=True)
class WaveFactContractMembership:
    membership_id: int
    property_definition_id: str
    property_key: str
    display_order: int | None
    evidence_requirement_override: str | None


@dataclass(frozen=True, slots=True)
class WaveFactContract:
    """Ordered required Fact contract for one Product Type Definition."""

    definition_id: int
    required_memberships: tuple[WaveFactContractMembership, ...]
    evidence_required_definition_ids: tuple[str, ...]

    @property
    def required_definition_ids(self) -> tuple[str, ...]:
        return tuple(m.property_definition_id for m in self.required_memberships)

    @property
    def property_key_by_definition_id(self) -> dict[str, str]:
        return {
            m.property_definition_id: m.property_key for m in self.required_memberships
        }

    @property
    def required_count(self) -> int:
        return len(self.required_memberships)


def _validation(message: str, *, field: str) -> None:
    raise api_error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        error_code=ErrorCode.VALIDATION_FAILED,
        message=message,
        details=[{"field": field, "message": message}],
    )


def _conflict(message: str, *, field: str) -> None:
    raise api_error(
        status.HTTP_409_CONFLICT,
        error_code=ErrorCode.CONFLICT,
        message=message,
        details=[{"field": field, "message": message}],
    )


def _sort_required_memberships(
    memberships: list[ProductTypeAttributeMembership],
) -> list[ProductTypeAttributeMembership]:
    """display_order ASC NULLS LAST, then membership.id ASC."""
    return sorted(
        memberships,
        key=lambda m: (
            m.display_order is None,
            m.display_order if m.display_order is not None else 0,
            int(m.id),
        ),
    )


def _evidence_required_ids(
    ordered: list[WaveFactContractMembership],
    *,
    require_evidence: bool,
) -> tuple[str, ...]:
    """Resolve which required Facts need Evidence under Wave policy.

    Decision (fail-closed, documented):
    - ``evidence_requirement_override == "required"`` → always require Evidence
    - ``evidence_requirement_override == "not_required"`` → never require for Wave
    - otherwise, when Wave policy ``require_evidence=True`` → require Evidence
      for every remaining required membership (including null / recommended)
    - when ``require_evidence=False`` → only explicit ``required`` override
    """
    out: list[str] = []
    for m in ordered:
        override = m.evidence_requirement_override
        if override == "not_required":
            continue
        if override == "required" or require_evidence:
            out.append(m.property_definition_id)
    return tuple(out)


async def resolve_definition_fact_contract(
    db: AsyncSession,
    definition_id: int,
    *,
    require_evidence: bool,
) -> WaveFactContract:
    """Load sealed Definition memberships and return the Wave Fact contract."""
    definition = (
        await db.execute(
            select(ProductTypeDefinition)
            .options(selectinload(ProductTypeDefinition.memberships))
            .where(ProductTypeDefinition.id == int(definition_id))
        )
    ).scalar_one_or_none()
    if definition is None:
        _conflict(
            f"Product Type Definition id={definition_id} not found",
            field="definition_id",
        )

    required_rows = [
        m
        for m in definition.memberships
        if m.requiredness == MembershipRequiredness.REQUIRED.value
    ]
    if not required_rows:
        _validation(
            "Product Type Definition has zero required memberships",
            field="definition_id",
        )

    ordered_rows = _sort_required_memberships(required_rows)
    prop_ids = [m.property_definition_id for m in ordered_rows]
    props = (
        await db.execute(
            select(KnowledgePropertyDefinition).where(
                KnowledgePropertyDefinition.definition_id.in_(prop_ids)
            )
        )
    ).scalars().all()
    by_id = {p.definition_id: p for p in props}

    memberships: list[WaveFactContractMembership] = []
    for row in ordered_rows:
        prop = by_id.get(row.property_definition_id)
        if prop is None:
            _conflict(
                f"Property Definition {row.property_definition_id!r} missing",
                field="memberships.property_definition_id",
            )
        if prop.status not in _USABLE_PROPERTY_STATUSES:
            _conflict(
                f"Property Definition {prop.definition_id!r} status={prop.status!r} "
                "is not usable for Wave Fact contract",
                field="memberships.property_definition_id",
            )
        memberships.append(
            WaveFactContractMembership(
                membership_id=int(row.id),
                property_definition_id=prop.definition_id,
                property_key=prop.key,
                display_order=row.display_order,
                evidence_requirement_override=row.evidence_requirement_override,
            )
        )

    frozen = tuple(memberships)
    return WaveFactContract(
        definition_id=int(definition.id),
        required_memberships=frozen,
        evidence_required_definition_ids=_evidence_required_ids(
            list(frozen),
            require_evidence=require_evidence,
        ),
    )


def wave_require_evidence_from_policy(policy_json: dict[str, Any] | None) -> bool:
    """Read Wave policy ``require_evidence`` (default True — fail-closed)."""
    policy: dict[str, Any] = policy_json if isinstance(policy_json, dict) else {}
    if "require_evidence" in policy:
        return bool(policy.get("require_evidence"))
    rules_raw = policy.get("validation_rules")
    rules: dict[str, Any] = rules_raw if isinstance(rules_raw, dict) else {}
    if "require_evidence" in rules:
        return bool(rules.get("require_evidence"))
    return True
