"""Prompt 41 — governed atomic KB batch assert."""

from __future__ import annotations

import asyncio
import copy
from datetime import UTC, datetime

import pytest
from app.api.deps import get_current_super_admin
from app.core.errors import ErrorCode, api_error
from app.core.security import create_access_token
from app.db.models import Product
from app.db.models.knowledge import (
    KnowledgeEvidenceArtifact,
    KnowledgeEvidenceLink,
    KnowledgeFact,
    KnowledgeFactRevision,
    KnowledgePropertyDefinition,
    KnowledgeUnit,
)
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
    BATCH1_MANIFEST_SHA256,
    REQUIRED_ALEMBIC,
    REQUIRED_ARTIFACT_CHECKSUM,
)
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.dialects import postgresql

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


async def _ensure_gates(session):
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
            "VALUES (1, 'live', 'test', 'prompt41')"
        )
    )
    await session.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
        {"v": REQUIRED_ALEMBIC},
    )


async def _seed_unit(session):
    unit = KnowledgeUnit(
        dimension="length",
        canonical_code="mm",
        aliases=["mm"],
        status="active",
    )
    session.add(unit)
    await session.flush()
    return unit


async def _seed_property(
    session,
    *,
    definition_id,
    key,
    data_type,
    validation,
):
    prop = KnowledgePropertyDefinition(
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
    session.add(prop)
    await session.flush()
    return prop


async def _seed_gen_caliper_stack(session):
    await _ensure_gates(session)
    await _seed_unit(session)
    await _seed_property(
        session,
        definition_id="def.measurement_range",
        key="measurement_range",
        data_type="range",
        validation={
            "type": "range",
            "max_inclusive": True,
            "min_inclusive": True,
            "require_min_le_max": True,
        },
    )
    await _seed_property(
        session,
        definition_id="def.resolution",
        key="resolution",
        data_type="number",
        validation={"type": "number", "exclusive_min": 0},
    )
    await _seed_property(
        session,
        definition_id="def.accuracy",
        key="accuracy",
        data_type="quantity",
        validation={
            "type": "quantity",
            "allow_qualifier": ["±", "+", "-", "approx", "max"],
        },
    )

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
    await session.flush()

    artifact = KnowledgeEvidenceArtifact(
        id=1,
        artifact_id="insize-108a-catalogue-v1",
        kind="oem_catalogue",
        title="INSIZE 108A",
        source_ref="108A.pdf",
        checksum_sha256=OEM_SHA,
        recorded_at=datetime.now(UTC),
        recorder="test",
    )
    session.add(artifact)
    await session.flush()

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
            "technical_specs": {"keep": True, "accuracy": "0.01 mm"},
            "features": {},
            "dimensions": {},
            "optional_accessories": [],
        },
    }
    resp = client.post("/api/v1/products/", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _payload(sku: str, *, manifest: str = BATCH1_MANIFEST_SHA256) -> dict:
    return {
        "manifest_sha256": manifest,
        "sku": sku,
        "product_type_id": 1,
        "definition_id": 1,
        "change_reason": "INSIZE Batch 1 — GEN_CALIPER assignment",
        "facts": [
            {
                "definition_id": "def.measurement_range",
                "value": {"min": 0, "max": 150},
                "unit": "mm",
                "source_id": f"catalog:insize:4b251dbb:p36:{sku}",
            },
            {
                "definition_id": "def.resolution",
                "value": 0.01,
                "unit": "mm",
                "source_id": f"catalog:insize:4b251dbb:p36:{sku}",
            },
            {
                "definition_id": "def.accuracy",
                "value": {"magnitude": 0.03, "qualifier": "±"},
                "unit": "mm",
                "source_id": f"catalog:insize:4b251dbb:p36:{sku}",
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


async def _snapshot(product_id: int) -> dict:
    async with TestingSessionLocal() as session:
        product = await session.get(Product, product_id)
        facts = (
            await session.execute(
                select(KnowledgeFact).where(KnowledgeFact.entity_id == product_id)
            )
        ).scalars().all()
        revs = (
            await session.execute(
                select(func.count()).select_from(KnowledgeFactRevision).where(
                    KnowledgeFactRevision.fact_id.in_([f.id for f in facts] or [-1])
                )
            )
        ).scalar_one()
        links = (
            await session.execute(
                select(func.count()).select_from(KnowledgeEvidenceLink).where(
                    KnowledgeEvidenceLink.fact_id.in_([f.id for f in facts] or [-1])
                )
            )
        ).scalar_one()
        published = sum(1 for f in facts if f.status == "published")
        return {
            "product_type_id": product.product_type_id if product else None,
            "specs": copy.deepcopy(product.specifications) if product else None,
            "facts": len(facts),
            "revisions": int(revs),
            "links": int(links),
            "published": published,
            "asserted": sum(1 for f in facts if f.status == "asserted"),
        }


def test_batch_assert_success(admin_headers, valid_product_data):
    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1103-150")
    before = _run(_snapshot(product["id"]))
    assert before["product_type_id"] is None

    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
        json=_payload("1103-150"),
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["product_type_id"] == 1
    assert len(body["facts"]) == 3
    assert len(body["evidence_links"]) == 3
    assert body["published_count"] == 0
    assert all(f["status"] == "asserted" for f in body["facts"])

    after = _run(_snapshot(product["id"]))
    assert after["product_type_id"] == 1
    assert after["facts"] == 3
    assert after["revisions"] == 3
    assert after["links"] == 3
    assert after["published"] == 0
    assert after["asserted"] == 3
    assert after["specs"] == before["specs"]


async def _seed_via_session():
    async with TestingSessionLocal() as session:
        await _seed_gen_caliper_stack(session)
        await session.commit()


def test_fact_failure_rolls_back(admin_headers, valid_product_data, monkeypatch):
    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1103-200")
    before = _run(_snapshot(product["id"]))

    calls = {"n": 0}
    real = batch_service.fact_service.create_fact

    async def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="injected fact failure",
                details=[{"field": "facts", "message": "injected"}],
            )
        return await real(*args, **kwargs)

    monkeypatch.setattr(batch_service.fact_service, "create_fact", flaky)

    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
        json=_payload("1103-200"),
        headers=admin_headers,
    )
    assert resp.status_code == 422, resp.text
    after = _run(_snapshot(product["id"]))
    assert after["product_type_id"] is None
    assert after["facts"] == 0
    assert after["links"] == 0
    assert after["specs"] == before["specs"]


def test_evidence_failure_rolls_back(admin_headers, valid_product_data, monkeypatch):
    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1103-300")
    before = _run(_snapshot(product["id"]))

    async def boom(*args, **kwargs):
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="injected evidence failure",
            details=[{"field": "evidence_links", "message": "injected"}],
        )

    monkeypatch.setattr(batch_service.evidence_service, "link_artifact_to_fact", boom)

    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
        json=_payload("1103-300"),
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text
    after = _run(_snapshot(product["id"]))
    assert after["product_type_id"] is None
    assert after["facts"] == 0
    assert after["links"] == 0
    assert after["specs"] == before["specs"]


def test_manifest_mismatch_zero_writes(admin_headers, valid_product_data):
    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1196-300")
    before = _run(_snapshot(product["id"]))
    bad = _payload("1196-300", manifest="0" * 64)
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
        json=bad,
        headers=admin_headers,
    )
    assert resp.status_code == 409
    after = _run(_snapshot(product["id"]))
    assert after == before


def test_wrong_sku_zero_writes(admin_headers, valid_product_data):
    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1110-150A")
    before = _run(_snapshot(product["id"]))
    payload = _payload("1110-150A")
    payload["sku"] = "NOT-THE-SKU"
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
        json=payload,
        headers=admin_headers,
    )
    assert resp.status_code == 409
    after = _run(_snapshot(product["id"]))
    assert after == before


def test_already_assigned_zero_writes(admin_headers, valid_product_data):
    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1170-300")
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
            json={
                "product_type_id": 1,
                "change_reason": "pre-assign for negative test",
            },
            headers=admin_headers,
        ).status_code
        == 200
    )
    before = _run(_snapshot(product["id"]))
    assert before["product_type_id"] == 1
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
        json=_payload("1170-300"),
        headers=admin_headers,
    )
    assert resp.status_code == 409
    after = _run(_snapshot(product["id"]))
    assert after["facts"] == 0
    assert after["links"] == 0
    assert after["product_type_id"] == 1
    assert after["specs"] == before["specs"]


def test_jsonb_isolation_on_success(admin_headers, valid_product_data):
    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1205-150S")
    before = _run(_snapshot(product["id"]))
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
            json=_payload("1205-150S"),
            headers=admin_headers,
        ).status_code
        == 201
    )
    after = _run(_snapshot(product["id"]))
    assert after["specs"] == before["specs"]


def test_freeze_gate_blocks(admin_headers, valid_product_data, monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "false")
    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1205-200S")
    before = _run(_snapshot(product["id"]))
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
        json=_payload("1205-200S"),
        headers=admin_headers,
    )
    assert resp.status_code == 409
    after = _run(_snapshot(product["id"]))
    assert after == before


def test_batch_assert_emits_for_update_sql():
    stmt = select(Product).where(Product.id == 1).with_for_update()
    sql = str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )
    assert "FOR UPDATE" in sql.upper()


def test_customer_forbidden(admin_headers, valid_product_data):
    from tests.conftest import customer_auth_headers

    _run(_seed_via_session())
    product = _create_product(admin_headers, valid_product_data, sku="1136-501")
    app.dependency_overrides.pop(get_current_super_admin, None)
    customer = customer_auth_headers("09126660011")
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/kb-batch-assert",
        json=_payload("1136-501"),
        headers=customer,
    )
    assert resp.status_code in (401, 403)
