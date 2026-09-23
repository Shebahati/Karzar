"""Prompt 68 — Wave Execution Engine PR3-A."""

from __future__ import annotations

import asyncio
import copy
from datetime import UTC, datetime
from typing import Any

import pytest
from app.api.deps import get_current_super_admin
from app.core.errors import ErrorCode, api_error
from app.core.security import create_access_token
from app.db.models import Product
from app.db.models.knowledge import (
    KnowledgeEvidenceArtifact,
    KnowledgeEvidenceLink,
    KnowledgeFact,
    KnowledgePropertyDefinition,
    KnowledgeUnit,
)
from app.db.models.knowledge_wave import KnowledgeWave, KnowledgeWaveRun
from app.db.models.product import Brand
from app.db.models.product_type import (
    ProductType,
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
    ProductTypeStatus,
)
from app.main import app
from app.services import knowledge_batch_assert_service as batch_service
from app.services.knowledge_batch_assert_service import (
    REQUIRED_ALEMBIC,
    REQUIRED_ARTIFACT_CHECKSUM,
)
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from tests.conftest import TestingSessionLocal, override_super_admin

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("override_database")

OEM_SHA = REQUIRED_ARTIFACT_CHECKSUM


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def admin_headers(monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "true")
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    headers = {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}
    yield headers
    app.dependency_overrides.pop(get_current_super_admin, None)


async def _ensure_gates(session, *, plane="live", alembic=REQUIRED_ALEMBIC):
    await session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS environment_identity ("
            "id INTEGER PRIMARY KEY, plane VARCHAR(32) NOT NULL, "
            "label VARCHAR(64) NOT NULL, notes TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
    )
    await session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(64) NOT NULL)"
        )
    )
    await session.execute(text("DELETE FROM environment_identity"))
    await session.execute(text("DELETE FROM alembic_version"))
    await session.execute(
        text(
            "INSERT INTO environment_identity (id, plane, label, notes) "
            "VALUES (1, :plane, 'test', 'prompt68')"
        ),
        {"plane": plane},
    )
    await session.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
        {"v": alembic},
    )


async def _seed_gen_caliper_stack(session):
    await _ensure_gates(session)
    session.add(
        KnowledgeUnit(
            dimension="length",
            canonical_code="mm",
            aliases=["mm"],
            status="active",
        )
    )
    await session.flush()
    for definition_id, key, data_type, validation in (
        (
            "def.measurement_range",
            "measurement_range",
            "range",
            {
                "type": "range",
                "max_inclusive": True,
                "min_inclusive": True,
                "require_min_le_max": True,
            },
        ),
        (
            "def.resolution",
            "resolution",
            "number",
            {"type": "number", "exclusive_min": 0},
        ),
        (
            "def.accuracy",
            "accuracy",
            "quantity",
            {
                "type": "quantity",
                "allow_qualifier": ["±", "+", "-", "approx", "max"],
            },
        ),
    ):
        session.add(
            KnowledgePropertyDefinition(
                definition_id=definition_id,
                key=key,
                data_type=data_type,
                label_en=key,
                label_fa=key,
                validation=validation,
                version="1.0.0",
                status="active",
                unit_dimension="length",
                default_unit="mm",
                comparable=False,
                filterable=False,
                customer_facing=False,
            )
        )
    await session.flush()

    pt = ProductType(
        id=1,
        code="GEN_CALIPER",
        slug="gen-caliper",
        name_fa="کولیس عمومی",
        name_en="General Caliper",
        status=ProductTypeStatus.ACTIVE.value,
    )
    session.add(pt)
    await session.flush()
    definition = ProductTypeDefinition(
        id=1,
        product_type_id=1,
        version=1,
        status=ProductTypeDefinitionStatus.ACTIVE.value,
    )
    session.add(definition)
    await session.flush()
    for prop_id, order in (
        ("def.measurement_range", 10),
        ("def.resolution", 20),
        ("def.accuracy", 30),
    ):
        session.add(
            ProductTypeAttributeMembership(
                product_type_definition_id=1,
                property_definition_id=prop_id,
                requiredness="required",
                applicability_condition={},
                validation_overrides={},
                evidence_requirement_override="required",
                display_order=order,
            )
        )
    session.add(
        KnowledgeEvidenceArtifact(
            id=1,
            artifact_id="insize-108a-catalogue-v1",
            kind="oem_catalogue",
            title="INSIZE 108A",
            source_ref="108A.pdf",
            checksum_sha256=OEM_SHA,
            recorded_at=datetime.now(UTC),
            recorder="test",
        )
    )
    brand = await session.get(Brand, 1)
    assert brand is not None
    brand.name = "INSIZE | اینسایز"
    brand.slug = "insize"
    await session.flush()


def _create_product(admin_headers, valid_product_data, sku: str):
    payload = {
        **valid_product_data,
        "sku": sku,
        "name": f"INSIZE caliper {sku}",
        "specifications": {
            "technical_specs": {"keep": True},
            "features": {},
            "dimensions": {},
            "optional_accessories": [],
        },
    }
    resp = client.post("/api/v1/products/", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _sku_unit(sku: str, product_id: int) -> dict[str, Any]:
    return {
        "product_id": product_id,
        "sku": sku,
        "facts": [
            {
                "definition_id": "def.measurement_range",
                "value": {"min": 0, "max": 150},
                "unit": "mm",
                "source_id": f"catalog:insize:test:{sku}",
            },
            {
                "definition_id": "def.resolution",
                "value": 0.01,
                "unit": "mm",
                "source_id": f"catalog:insize:test:{sku}",
            },
            {
                "definition_id": "def.accuracy",
                "value": {"magnitude": 0.03, "qualifier": "±"},
                "unit": "mm",
                "source_id": f"catalog:insize:test:{sku}",
            },
        ],
        "evidence_links": [
            {
                "artifact_id": 1,
                "locator": {
                    "pdf_page": 36,
                    "printed_page": 28,
                    "model": sku,
                    "property": "measurement_range",
                },
            },
            {
                "artifact_id": 1,
                "locator": {
                    "pdf_page": 36,
                    "printed_page": 28,
                    "model": sku,
                    "property": "resolution",
                },
            },
            {
                "artifact_id": 1,
                "locator": {
                    "pdf_page": 36,
                    "printed_page": 28,
                    "model": sku,
                    "property": "accuracy",
                },
            },
        ],
    }


def _policy_json() -> dict[str, Any]:
    return {
        "environment_pins": {
            "plane": "live",
            "alembic": REQUIRED_ALEMBIC,
            "freeze_required": True,
        },
        "validation_rules": {
            "resume_existing_facts": True,
            "resume_existing_assignment": True,
            "resume_from_failed": True,
            "allow_partial_execute": False,
        },
    }


def _seal_wave(admin_headers, *, wave_id: str, product: dict) -> dict:
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": wave_id,
            "brand": "INSIZE",
            "product_type_id": 1,
            "definition_id": 1,
            "policy_json": _policy_json(),
            "products": [
                {"product_id": product["id"], "sku_snapshot": product["sku"]}
            ],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    wave_pk = created.json()["id"]
    reviewed = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Reviewed", "change_reason": "review"},
        headers=admin_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    sealed = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/seal",
        json={"change_reason": "seal"},
        headers=admin_headers,
    )
    assert sealed.status_code == 200, sealed.text
    return sealed.json()


def test_draft_and_reviewed_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W68-DRAFT")
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "EXEC-DRAFT-001",
            "brand": "INSIZE",
            "product_type_id": 1,
            "definition_id": 1,
            "policy_json": _policy_json(),
            "products": [
                {"product_id": product["id"], "sku_snapshot": product["sku"]}
            ],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    unit = _sku_unit(product["sku"], product["id"])
    draft_exec = client.post(
        "/api/v1/knowledge/waves/EXEC-DRAFT-001/execute",
        json={"change_reason": "nope", "sku_units": [unit]},
        headers=admin_headers,
    )
    assert draft_exec.status_code == 409, draft_exec.text

    wave_pk = created.json()["id"]
    client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Reviewed", "change_reason": "r"},
        headers=admin_headers,
    )
    reviewed_exec = client.post(
        "/api/v1/knowledge/waves/EXEC-DRAFT-001/execute",
        json={"change_reason": "nope", "sku_units": [unit]},
        headers=admin_headers,
    )
    assert reviewed_exec.status_code == 409, reviewed_exec.text


async def _seed():
    async with TestingSessionLocal() as session:
        await _seed_gen_caliper_stack(session)
        await session.commit()


def test_environment_mismatch_rejected(admin_headers, valid_product_data, monkeypatch):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W68-ENV")
    sealed = _seal_wave(admin_headers, wave_id="EXEC-ENV-001", product=product)
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "false")
    resp = client.post(
        f"/api/v1/knowledge/waves/{sealed['wave_id']}/execute",
        json={
            "change_reason": "env",
            "sku_units": [_sku_unit(product["sku"], product["id"])],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text
    assert "KARZAR_DEPLOY_FREEZE" in resp.text or "freeze" in resp.text.lower()


def test_sha_mismatch_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W68-SHA")
    sealed = _seal_wave(admin_headers, wave_id="EXEC-SHA-001", product=product)

    async def _corrupt():
        async with TestingSessionLocal() as session:
            wave = await session.get(KnowledgeWave, sealed["id"])
            assert wave is not None
            wave.manifest_sha256 = "a" * 64
            await session.commit()

    _run(_corrupt())
    resp = client.post(
        "/api/v1/knowledge/waves/EXEC-SHA-001/execute",
        json={
            "change_reason": "sha",
            "sku_units": [_sku_unit(product["sku"], product["id"])],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text


def test_sealed_wave_execution_and_ledger(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W68-OK")
    _seal_wave(admin_headers, wave_id="EXEC-OK-001", product=product)
    unit = _sku_unit(product["sku"], product["id"])

    async def _before():
        async with TestingSessionLocal() as session:
            return (
                await session.execute(select(func.count()).select_from(KnowledgeFact))
            ).scalar_one()

    facts_before = _run(_before())

    executed = client.post(
        "/api/v1/knowledge/waves/EXEC-OK-001/execute",
        json={"change_reason": "assert wave", "sku_units": [unit]},
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "completed"
    assert body["wave_status"] == "Asserted"
    assert body["progress"]["success"] == 1
    assert body["created_items"][0]["status"] == "success"
    assert len(body["manifest_sha256"]) == 64

    run_get = client.get(
        f"/api/v1/knowledge/wave-runs/{body['wave_run_id']}",
        headers=admin_headers,
    )
    assert run_get.status_code == 200, run_get.text
    run_body = run_get.json()
    assert run_body["status"] == "completed"
    assert run_body["wave"]["wave_id"] == "EXEC-OK-001"
    assert run_body["progress"]["total"] == 1
    assert run_body["items"][0]["status"] == "success"
    assert run_body["items"][0]["result"]["fact_ids"]

    async def _after():
        async with TestingSessionLocal() as session:
            facts = (
                await session.execute(select(func.count()).select_from(KnowledgeFact))
            ).scalar_one()
            product_row = await session.get(Product, product["id"])
            assert product_row is not None
            return facts, product_row.product_type_id, copy.deepcopy(product_row.specifications)

    facts_after, pt_id, specs = _run(_after())
    assert facts_after == facts_before + 3
    assert pt_id == 1
    assert specs["technical_specs"]["keep"] is True


def test_sku_failure_rollback(admin_headers, valid_product_data, monkeypatch):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W68-FAIL")
    _seal_wave(admin_headers, wave_id="EXEC-FAIL-001", product=product)

    async def _boom(*args, **kwargs):
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="forced SKU failure",
            details=[{"field": "sku", "message": "forced"}],
        )

    monkeypatch.setattr(batch_service, "execute_kb_batch_assert", _boom)

    executed = client.post(
        "/api/v1/knowledge/waves/EXEC-FAIL-001/execute",
        json={
            "change_reason": "fail",
            "sku_units": [_sku_unit(product["sku"], product["id"])],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "failed"
    assert body["wave_status"] == "Failed"
    assert body["created_items"][0]["status"] == "failed"

    async def _check():
        async with TestingSessionLocal() as session:
            facts = (
                await session.execute(
                    select(func.count())
                    .select_from(KnowledgeFact)
                    .where(KnowledgeFact.entity_id == product["id"])
                )
            ).scalar_one()
            product_row = await session.get(Product, product["id"])
            assert product_row is not None
            return facts, product_row.product_type_id

    facts, pt_id = _run(_check())
    assert facts == 0
    assert pt_id is None


def test_resume_failed_run(admin_headers, valid_product_data, monkeypatch):
    _run(_seed())
    p1 = _create_product(admin_headers, valid_product_data, "W68-R1")
    p2 = _create_product(admin_headers, valid_product_data, "W68-R2")

    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "EXEC-RESUME-001",
            "brand": "INSIZE",
            "product_type_id": 1,
            "definition_id": 1,
            "policy_json": _policy_json(),
            "products": [
                {"product_id": p1["id"], "sku_snapshot": p1["sku"]},
                {"product_id": p2["id"], "sku_snapshot": p2["sku"]},
            ],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    wave_pk = created.json()["id"]
    client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Reviewed", "change_reason": "r"},
        headers=admin_headers,
    )
    sealed = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/seal",
        json={"change_reason": "s"},
        headers=admin_headers,
    )
    assert sealed.status_code == 200, sealed.text

    calls = {"n": 0}
    real = batch_service.execute_kb_batch_assert

    async def _flaky(db, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message="second SKU fails",
                details=[{"field": "sku", "message": "fail"}],
            )
        return await real(db, **kwargs)

    monkeypatch.setattr(batch_service, "execute_kb_batch_assert", _flaky)

    units = [_sku_unit(p1["sku"], p1["id"]), _sku_unit(p2["sku"], p2["id"])]
    first = client.post(
        "/api/v1/knowledge/waves/EXEC-RESUME-001/execute",
        json={"change_reason": "partial", "sku_units": units},
        headers=admin_headers,
    )
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "failed"
    failed_run_id = first.json()["wave_run_id"]

    async def _mid():
        async with TestingSessionLocal() as session:
            f1 = (
                await session.execute(
                    select(func.count())
                    .select_from(KnowledgeFact)
                    .where(KnowledgeFact.entity_id == p1["id"])
                )
            ).scalar_one()
            f2 = (
                await session.execute(
                    select(func.count())
                    .select_from(KnowledgeFact)
                    .where(KnowledgeFact.entity_id == p2["id"])
                )
            ).scalar_one()
            return f1, f2

    assert _run(_mid()) == (3, 0)

    monkeypatch.setattr(batch_service, "execute_kb_batch_assert", real)
    resumed = client.post(
        f"/api/v1/knowledge/wave-runs/{failed_run_id}/resume",
        json={"change_reason": "resume remaining"},
        headers=admin_headers,
    )
    assert resumed.status_code == 201, resumed.text
    assert resumed.json()["status"] == "completed"
    assert resumed.json()["wave_status"] == "Asserted"
    assert resumed.json()["wave_run_id"] != failed_run_id

    async def _end():
        async with TestingSessionLocal() as session:
            f1 = (
                await session.execute(
                    select(func.count())
                    .select_from(KnowledgeFact)
                    .where(KnowledgeFact.entity_id == p1["id"])
                )
            ).scalar_one()
            f2 = (
                await session.execute(
                    select(func.count())
                    .select_from(KnowledgeFact)
                    .where(KnowledgeFact.entity_id == p2["id"])
                )
            ).scalar_one()
            runs = (
                await session.execute(select(func.count()).select_from(KnowledgeWaveRun))
            ).scalar_one()
            return f1, f2, runs

    f1, f2, runs = _run(_end())
    assert f1 == 3  # no duplicate
    assert f2 == 3
    assert runs >= 2


def test_execute_does_not_touch_unrelated_kb(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W68-INT")
    _seal_wave(admin_headers, wave_id="EXEC-INT-001", product=product)

    async def _baseline():
        async with TestingSessionLocal() as session:
            artifacts = (
                await session.execute(
                    select(func.count()).select_from(KnowledgeEvidenceArtifact)
                )
            ).scalar_one()
            links = (
                await session.execute(
                    select(func.count()).select_from(KnowledgeEvidenceLink)
                )
            ).scalar_one()
            products = (
                await session.execute(select(func.count()).select_from(Product))
            ).scalar_one()
            return artifacts, links, products

    before = _run(_baseline())
    client.post(
        "/api/v1/knowledge/waves/EXEC-INT-001/execute",
        json={
            "change_reason": "integrity",
            "sku_units": [_sku_unit(product["sku"], product["id"])],
        },
        headers=admin_headers,
    )
    after = _run(_baseline())
    assert after[0] == before[0]  # artifacts unchanged (reuse id=1)
    assert after[2] == before[2]  # product count unchanged
    # links increase for this SKU only — not "untouched" for links on this product
    assert after[1] >= before[1]
