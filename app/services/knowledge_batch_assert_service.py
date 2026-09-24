"""Governed SKU-unit Knowledge Base batch assert (Prompt 41).

Orchestrates existing Product Type assignment, Fact create, and Evidence link
services on one shared AsyncSession. The HTTP endpoint commits once.

Does not publish Facts, create Artifacts, mutate JSONB, or change Dictionary /
Definitions / taxonomy.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, NoReturn

from fastapi import status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge import KnowledgeEvidenceArtifact, KnowledgeFact
from app.db.models.product import Brand, Product
from app.db.models.product_type import (
    ProductType,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
    ProductTypeStatus,
)
from app.db.models.user import User
from app.services import knowledge_evidence_service as evidence_service
from app.services import knowledge_fact_service as fact_service
from app.services import product_type_assignment_service as assignment_service
from app.services.alembic_revision_compat import is_runtime_revision_compatible

# Immutable Batch 1 execution manifest (Prompt 38).
BATCH1_MANIFEST_SHA256 = (
    "0c9f19d94db6e134e82550d51b7bcd1087e43ba5faf2bf0d70e62fc0390363c7"
)
REQUIRED_ALEMBIC = "n7o8p9q0r1s2"
REQUIRED_PLANE = "live"
REQUIRED_PRODUCT_TYPE_ID = 1
REQUIRED_PRODUCT_TYPE_CODE = "GEN_CALIPER"
REQUIRED_DEFINITION_ID = 1
REQUIRED_ARTIFACT_DB_ID = 1
REQUIRED_ARTIFACT_CHECKSUM = (
    "4b251dbbd6b662e64dcc1703dd373886f8e3df8e3363a5406bc706c8aa85123b"
)
REQUIRED_FACT_DEFINITIONS = frozenset(
    {
        "def.measurement_range",
        "def.resolution",
        "def.accuracy",
    }
)
FACT_DEFINITION_ORDER = (
    "def.measurement_range",
    "def.resolution",
    "def.accuracy",
)


def _conflict(message: str, *, field: str) -> NoReturn:
    raise api_error(
        status.HTTP_409_CONFLICT,
        error_code=ErrorCode.CONFLICT,
        message=message,
        details=[{"field": field, "message": message}],
    )


def _validation(message: str, *, field: str) -> NoReturn:
    raise api_error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        error_code=ErrorCode.VALIDATION_FAILED,
        message=message,
        details=[{"field": field, "message": message}],
    )


async def _assert_safety_gates(
    db: AsyncSession, *, pins: dict[str, Any] | None = None
) -> None:
    required_freeze = True
    required_plane = REQUIRED_PLANE
    required_alembic = REQUIRED_ALEMBIC
    if pins:
        required_freeze = bool(pins.get("freeze_required", True))
        required_plane = str(pins.get("plane") or REQUIRED_PLANE)
        required_alembic = str(pins.get("alembic") or REQUIRED_ALEMBIC)

    if required_freeze:
        freeze = (os.environ.get("KARZAR_DEPLOY_FREEZE") or "").strip().lower()
        if freeze != "true":
            _conflict(
                "KARZAR_DEPLOY_FREEZE must be true for kb-batch-assert",
                field="KARZAR_DEPLOY_FREEZE",
            )

    plane_row = (
        await db.execute(
            text("SELECT plane FROM environment_identity WHERE id = 1")
        )
    ).first()
    if plane_row is None or str(plane_row[0]) != required_plane:
        _conflict(
            f"environment_identity.plane must be {required_plane!r}",
            field="environment_identity.plane",
        )

    alembic_row = (await db.execute(text("SELECT version_num FROM alembic_version"))).first()
    if alembic_row is None or not str(alembic_row[0] or "").strip():
        _conflict(
            "alembic_version is missing",
            field="alembic_version",
        )
    runtime_alembic = str(alembic_row[0]).strip()
    # Sealed pin = minimum compatible lineage revision (equal or descendant).
    if not is_runtime_revision_compatible(required_alembic, runtime_alembic):
        _conflict(
            (
                f"alembic_version {runtime_alembic!r} is not compatible with "
                f"sealed pin {required_alembic!r} "
                f"(runtime must equal or descend from the sealed revision)"
            ),
            field="alembic_version",
        )


async def assert_environment_gates(
    db: AsyncSession, *, pins: dict[str, Any] | None = None
) -> None:
    """Public freeze/plane/alembic gates (Batch-1 defaults or wave pins).

    ``environment_pins.alembic`` is a minimum compatible Alembic lineage pin:
    runtime must equal the sealed revision or be a descendant of it in the
    Alembic revision graph. Plane and freeze_required remain exact checks.
    """
    await _assert_safety_gates(db, pins=pins)


def _brand_matches(brand: Brand | None, expected: str) -> bool:
    if brand is None:
        return False
    exp = (expected or "").strip().upper()
    name = (brand.name or "").upper()
    slug = (brand.slug or "").lower()
    if not exp:
        return _brand_is_insize(brand)
    return exp in name or exp.lower() in slug or _brand_is_insize(brand)


def _brand_is_insize(brand: Brand | None) -> bool:
    if brand is None:
        return False
    name = (brand.name or "").upper()
    slug = (brand.slug or "").lower()
    return "INSIZE" in name or "insize" in slug


def _specs_fingerprint(specifications: Any) -> str:
    canonical = json.dumps(
        specifications,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _load_product_for_batch(
    db: AsyncSession,
    *,
    product_id: int,
    expected_sku: str,
    brand_expected: str | None = None,
    allow_existing_assignment: bool = False,
    expected_product_type_id: int | None = None,
) -> Product:
    product = (
        await db.execute(
            select(Product)
            .options(selectinload(Product.brand))
            .where(Product.id == product_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if product is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product not found",
            details=[{"field": "product_id", "message": "not found"}],
        )
    if product.sku != expected_sku:
        _conflict(
            "SKU does not match Product row for path product_id",
            field="sku",
        )
    if product.deleted_at is not None:
        _conflict("Product is deleted", field="deleted_at")
    # Knowledge assertion is orthogonal to storefront commercial state.
    # is_active / is_available / price must not gate Fact assertion.
    if brand_expected:
        if not _brand_matches(product.brand, brand_expected):
            _conflict(
                f"Product brand must match wave brand {brand_expected!r}",
                field="brand",
            )
    elif not _brand_is_insize(product.brand):
        _conflict("Product brand must be INSIZE", field="brand")
    if product.product_type_id is not None:
        if (
            allow_existing_assignment
            and expected_product_type_id is not None
            and product.product_type_id == expected_product_type_id
        ):
            return product
        _conflict(
            "Product already has a Product Type assignment",
            field="product_type_id",
        )
    return product


async def _assert_product_type_and_definition(
    db: AsyncSession,
    *,
    product_type_id: int = REQUIRED_PRODUCT_TYPE_ID,
    definition_id: int = REQUIRED_DEFINITION_ID,
    require_gen_caliper_literals: bool = True,
) -> ProductTypeDefinition:
    pt = await db.get(ProductType, product_type_id)
    if pt is None or pt.status != ProductTypeStatus.ACTIVE.value:
        _conflict(
            "Product Type must be active",
            field="product_type_id",
        )
    if require_gen_caliper_literals and (
        product_type_id != REQUIRED_PRODUCT_TYPE_ID
        or pt.code != REQUIRED_PRODUCT_TYPE_CODE
    ):
        _conflict(
            "GEN_CALIPER Product Type id=1 must be active",
            field="product_type_id",
        )

    definition = await db.get(ProductTypeDefinition, definition_id)
    if (
        definition is None
        or definition.product_type_id != product_type_id
        or definition.status != ProductTypeDefinitionStatus.ACTIVE.value
    ):
        _conflict(
            "Product Type Definition must be active for product_type_id",
            field="definition_id",
        )
    if require_gen_caliper_literals and (
        definition_id != REQUIRED_DEFINITION_ID or definition.version != 1
    ):
        _conflict(
            "Product Type Definition id=1 version=1 must be active",
            field="definition_id",
        )
    return definition


async def _assert_artifact(db: AsyncSession) -> KnowledgeEvidenceArtifact:
    artifact = await db.get(KnowledgeEvidenceArtifact, REQUIRED_ARTIFACT_DB_ID)
    if artifact is None:
        _conflict(
            "Evidence Artifact DB id=1 is required",
            field="artifact_id",
        )
    if (artifact.checksum_sha256 or "").lower() != REQUIRED_ARTIFACT_CHECKSUM:
        _conflict(
            "Evidence Artifact checksum does not match OEM 108A catalogue",
            field="artifact_checksum_sha256",
        )
    return artifact


def _normalize_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(facts) != 3:
        _validation("Exactly 3 Facts are required", field="facts")
    seen: set[str] = set()
    by_def: dict[str, dict[str, Any]] = {}
    for item in facts:
        def_id = item.get("definition_id")
        if def_id not in REQUIRED_FACT_DEFINITIONS:
            _validation(
                f"Unsupported definition_id {def_id!r}",
                field="facts.definition_id",
            )
        if def_id in seen:
            _validation(f"Duplicate definition_id {def_id!r}", field="facts")
        seen.add(def_id)
        by_def[def_id] = item
    if seen != REQUIRED_FACT_DEFINITIONS:
        _validation(
            "Facts must be exactly measurement_range, resolution, accuracy",
            field="facts",
        )
    return [by_def[d] for d in FACT_DEFINITION_ORDER]


def _normalize_evidence_links(
    links: list[dict[str, Any]], *, ordered_definition_ids: list[str]
) -> list[dict[str, Any]]:
    if len(links) != 3:
        _validation("Exactly 3 Evidence links are required", field="evidence_links")
    property_by_def = {
        "def.measurement_range": "measurement_range",
        "def.resolution": "resolution",
        "def.accuracy": "accuracy",
    }
    by_prop: dict[str, dict[str, Any]] = {}
    for item in links:
        if item.get("artifact_id") != REQUIRED_ARTIFACT_DB_ID:
            _validation(
                "artifact_id must be 1 (reuse existing OEM catalogue Artifact)",
                field="evidence_links.artifact_id",
            )
        locator = item.get("locator")
        if not isinstance(locator, dict):
            _validation("locator must be an object", field="evidence_links.locator")
        prop = locator.get("property")
        if prop not in property_by_def.values():
            _validation(
                f"Unsupported locator.property {prop!r}",
                field="evidence_links.locator.property",
            )
        if prop in by_prop:
            _validation(f"Duplicate locator.property {prop!r}", field="evidence_links")
        for required_key in ("pdf_page", "printed_page", "model", "property"):
            if required_key not in locator:
                _validation(
                    f"locator missing {required_key}",
                    field="evidence_links.locator",
                )
        by_prop[prop] = item

    ordered: list[dict[str, Any]] = []
    for def_id in ordered_definition_ids:
        prop = property_by_def[def_id]
        if prop not in by_prop:
            _validation(
                f"Missing Evidence link for property {prop!r}",
                field="evidence_links",
            )
        ordered.append(by_prop[prop])
    return ordered


async def _assert_no_existing_facts(db: AsyncSession, *, product_id: int) -> None:
    existing = (
        await db.execute(
            select(KnowledgeFact.definition_id).where(
                KnowledgeFact.entity_id == product_id,
                KnowledgeFact.definition_id.in_(REQUIRED_FACT_DEFINITIONS),
            )
        )
    ).scalars().all()
    if existing:
        _conflict(
            f"Existing Fact(s) for definition_id(s): {sorted(existing)}",
            field="facts",
        )


async def execute_kb_batch_assert(
    db: AsyncSession,
    *,
    product_id: int,
    manifest_sha256: str,
    sku: str,
    product_type_id: int,
    definition_id: int,
    facts: list[dict[str, Any]],
    evidence_links: list[dict[str, Any]],
    change_reason: str,
    actor: User,
    wave_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one SKU KB unit on ``db`` without committing.

    Caller (HTTP endpoint / wave executor) must commit once on success
    or rollback on error.

    When ``wave_context`` is provided (PR3-A), pins / brand / PT come from
    the sealed wave; Batch-1 SHA literal check is skipped. Fact/Evidence
    creation still uses existing services only.
    """
    pins = None
    resume_facts = False
    resume_assignment = False
    brand_expected: str | None = None
    if wave_context:
        pins = wave_context.get("environment_pins") or {}
        rules = wave_context.get("validation_rules") or {}
        resume_facts = bool(rules.get("resume_existing_facts", True))
        resume_assignment = bool(rules.get("resume_existing_assignment", True))
        brand_expected = str(wave_context.get("brand") or "")
        expected_sha = str(wave_context.get("manifest_sha256") or "").lower()
        if (manifest_sha256 or "").strip().lower() != expected_sha:
            _conflict(
                "manifest_sha256 does not match sealed wave",
                field="manifest_sha256",
            )
        if product_type_id != int(wave_context["product_type_id"]):
            _validation(
                "product_type_id must match sealed wave",
                field="product_type_id",
            )
        if definition_id != int(wave_context["definition_id"]):
            _validation(
                "definition_id must match sealed wave",
                field="definition_id",
            )
    else:
        await _assert_safety_gates(db)
        if (manifest_sha256 or "").strip().lower() != BATCH1_MANIFEST_SHA256:
            _conflict(
                "manifest_sha256 does not match immutable Batch 1 execution manifest",
                field="manifest_sha256",
            )
        if product_type_id != REQUIRED_PRODUCT_TYPE_ID:
            _validation(
                "product_type_id must be 1 (GEN_CALIPER)",
                field="product_type_id",
            )
        if definition_id != REQUIRED_DEFINITION_ID:
            _validation(
                "definition_id must be 1 (GEN_CALIPER Definition V1)",
                field="definition_id",
            )

    if wave_context:
        await _assert_safety_gates(db, pins=pins)

    reason = (change_reason or "").strip()
    if not reason:
        _validation("change_reason is required", field="change_reason")

    # Wave path still uses Batch-1 fact shape for PR3-A (3 defs); keeps
    # evidence/artifact rules via same normalizers.
    ordered_facts = _normalize_facts(facts)
    ordered_links = _normalize_evidence_links(
        evidence_links,
        ordered_definition_ids=[f["definition_id"] for f in ordered_facts],
    )

    product = await _load_product_for_batch(
        db,
        product_id=product_id,
        expected_sku=sku,
        brand_expected=brand_expected,
        allow_existing_assignment=resume_assignment if wave_context else False,
        expected_product_type_id=product_type_id if wave_context else None,
    )
    specs_before = _specs_fingerprint(product.specifications)

    await _assert_product_type_and_definition(
        db,
        product_type_id=product_type_id,
        definition_id=definition_id,
        require_gen_caliper_literals=wave_context is None,
    )
    await _assert_artifact(db)

    existing_defs = (
        await db.execute(
            select(KnowledgeFact.definition_id).where(
                KnowledgeFact.entity_id == product.id,
                KnowledgeFact.definition_id.in_(REQUIRED_FACT_DEFINITIONS),
            )
        )
    ).scalars().all()
    if existing_defs:
        if wave_context and resume_facts and set(existing_defs) == REQUIRED_FACT_DEFINITIONS:
            existing_facts = (
                await db.execute(
                    select(KnowledgeFact).where(
                        KnowledgeFact.entity_id == product.id,
                        KnowledgeFact.definition_id.in_(REQUIRED_FACT_DEFINITIONS),
                    )
                )
            ).scalars().all()
            by_def = {f.definition_id: f for f in existing_facts}
            ordered_existing = [by_def[d] for d in FACT_DEFINITION_ORDER]
            return {
                "product_id": product.id,
                "sku": product.sku,
                "product_type_id": product.product_type_id,
                "definition_id": definition_id,
                "manifest_sha256": (manifest_sha256 or "").strip().lower(),
                "resumed": True,
                "facts": [
                    {
                        "id": f.id,
                        "definition_id": f.definition_id,
                        "status": f.status,
                        "source_id": f.source_id,
                    }
                    for f in ordered_existing
                ],
                "evidence_links": [],
                "published_count": 0,
                "specifications_fingerprint": specs_before,
            }
        await _assert_no_existing_facts(db, product_id=product.id)

    # --- mutation block (still uncommitted) ---
    if product.product_type_id is None:
        await assignment_service.assign_product_type(
            db,
            product_id=product.id,
            product_type_id=product_type_id,
            change_reason=reason,
            actor=actor,
        )
    elif product.product_type_id != product_type_id:
        _conflict(
            "Product Type assignment does not match wave",
            field="product_type_id",
        )

    created_facts: list[KnowledgeFact] = []
    for fact_payload in ordered_facts:
        fact = await fact_service.create_fact(
            db,
            product_id=product.id,
            definition_id=fact_payload["definition_id"],
            value=fact_payload["value"],
            unit=fact_payload.get("unit"),
            qualifier=fact_payload.get("qualifier"),
            source_id=fact_payload["source_id"],
            confidence=fact_payload.get("confidence"),
            actor=actor,
        )
        created_facts.append(fact)

    created_links = []
    for fact, link_payload in zip(created_facts, ordered_links, strict=True):
        link = await evidence_service.link_artifact_to_fact(
            db,
            artifact_pk=int(link_payload["artifact_id"]),
            fact_id=fact.id,
            locator=link_payload["locator"],
            notes=link_payload.get("notes"),
            actor=actor,
        )
        created_links.append(link)

    await db.refresh(product)
    if product.product_type_id != product_type_id:
        _conflict("postcondition failed: product_type_id", field="product_type_id")
    if _specs_fingerprint(product.specifications) != specs_before:
        _conflict("postcondition failed: specifications JSONB mutated", field="specifications")

    for fact in created_facts:
        await db.refresh(fact)
        if fact.status != "asserted":
            _conflict("postcondition failed: Fact not asserted", field="facts")
        if fact.product_type_definition_id != definition_id:
            _conflict(
                "postcondition failed: product_type_definition_id",
                field="facts",
            )

    return {
        "product_id": product.id,
        "sku": product.sku,
        "product_type_id": product.product_type_id,
        "definition_id": definition_id,
        "manifest_sha256": (manifest_sha256 or "").strip().lower(),
        "resumed": False,
        "facts": [
            {
                "id": f.id,
                "definition_id": f.definition_id,
                "status": f.status,
                "source_id": f.source_id,
            }
            for f in created_facts
        ],
        "evidence_links": [
            {
                "id": link.id,
                "fact_id": link.fact_id,
                "artifact_id": link.artifact_id,
                "relation_type": link.relation_type,
            }
            for link in created_links
        ],
        "published_count": 0,
        "specifications_fingerprint": specs_before,
    }
