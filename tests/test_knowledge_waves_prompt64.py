"""Prompt 64 — Knowledge Wave Registry PR1 (Draft/Review APIs)."""

from __future__ import annotations

import asyncio
import copy

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models import Product
from app.db.models.knowledge import (
    KnowledgeEvidenceArtifact,
    KnowledgeEvidenceLink,
    KnowledgeFact,
    KnowledgePropertyDefinition,
)
from app.db.models.knowledge_wave import KnowledgeWave
from app.db.models.product_type import (
    ProductType,
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
    ProductTypeStatus,
)
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.conftest import (
    TestingSessionLocal,
    customer_auth_headers,
    override_super_admin,
)

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("override_database")


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def admin_headers():
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    headers = {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}
    yield headers
    app.dependency_overrides.pop(get_current_super_admin, None)


async def _seed_property(session, *, definition_id, key, data_type="string"):
    prop = KnowledgePropertyDefinition(
        definition_id=definition_id,
        key=key,
        data_type=data_type,
        label_en=key,
        label_fa=key,
        validation={},
        version="1.0.0",
        status="active",
        comparable=False,
        filterable=False,
        customer_facing=False,
    )
    session.add(prop)
    await session.flush()
    return prop


async def _seed_type_with_membership(session, *, property_definition_id, code="WAVE_PT"):
    pt = ProductType(
        code=code,
        slug=f"slug-{code.lower()}",
        name_fa="کولیس",
        status=ProductTypeStatus.ACTIVE.value,
    )
    session.add(pt)
    await session.flush()
    definition = ProductTypeDefinition(
        product_type_id=pt.id,
        version=1,
        status=ProductTypeDefinitionStatus.ACTIVE.value,
    )
    session.add(definition)
    await session.flush()
    membership = ProductTypeAttributeMembership(
        product_type_definition_id=definition.id,
        property_definition_id=property_definition_id,
        requiredness="optional",
        applicability_condition={},
        validation_overrides={},
        evidence_requirement_override=None,
    )
    session.add(membership)
    await session.flush()
    return pt, definition


def _create_product(admin_headers, valid_product_data, sku="WAVE-SKU-1"):
    payload = {
        **valid_product_data,
        "sku": sku,
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


def _seed_wave_deps(admin_headers, valid_product_data, *, sku="WAVE-SKU-1"):
    product = _create_product(admin_headers, valid_product_data, sku=sku)

    async def _seed():
        async with TestingSessionLocal() as session:
            prop = await _seed_property(
                session, definition_id="def.wave.accuracy", key="accuracy"
            )
            pt, definition = await _seed_type_with_membership(
                session, property_definition_id=prop.definition_id
            )
            await session.commit()
            return pt.id, definition.id, product["id"], product["sku"]

    return _run(_seed())


# --- Auth ---


def test_wave_routes_non_admin_rejected(valid_product_data):
    headers = customer_auth_headers()
    assert (
        client.post(
            "/api/v1/knowledge/waves",
            json={
                "wave_id": "w1",
                "brand": "INSIZE",
                "product_type_id": 1,
                "definition_id": 1,
            },
            headers=headers,
        ).status_code
        == 403
    )
    assert client.get("/api/v1/knowledge/waves", headers=headers).status_code == 403
    assert client.get("/api/v1/knowledge/waves/1", headers=headers).status_code == 403
    assert (
        client.patch("/api/v1/knowledge/waves/1", json={"brand": "X"}, headers=headers).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/knowledge/waves/1/review",
            json={"to_status": "Reviewed", "change_reason": "x"},
            headers=headers,
        ).status_code
        == 403
    )


def test_create_draft_wave(admin_headers, valid_product_data):
    pt_id, def_id, product_id, sku = _seed_wave_deps(admin_headers, valid_product_data)
    resp = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "INSIZE-CALIPER-WAVE-PR1-001",
            "brand": "INSIZE",
            "product_type_id": pt_id,
            "definition_id": def_id,
            "policy_json": {"plane": "test"},
            "products": [{"product_id": product_id, "sku_snapshot": sku}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["wave_id"] == "INSIZE-CALIPER-WAVE-PR1-001"
    assert body["status"] == "Draft"
    assert body["manifest_sha256"] is None
    assert body["brand"] == "INSIZE"
    assert body["product_type_id"] == pt_id
    assert body["definition_id"] == def_id
    assert body["policy_json"] == {"plane": "test"}
    assert len(body["products"]) == 1
    assert body["products"][0]["product_id"] == product_id
    assert body["products"][0]["sku_snapshot"] == sku

    listed = client.get("/api/v1/knowledge/waves", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    got = client.get(f"/api/v1/knowledge/waves/{body['id']}", headers=admin_headers)
    assert got.status_code == 200
    assert got.json()["id"] == body["id"]


def test_duplicate_wave_id_rejected(admin_headers, valid_product_data):
    pt_id, def_id, product_id, sku = _seed_wave_deps(
        admin_headers, valid_product_data, sku="WAVE-DUP-1"
    )
    payload = {
        "wave_id": "DUP-WAVE-ID",
        "brand": "INSIZE",
        "product_type_id": pt_id,
        "definition_id": def_id,
        "products": [{"product_id": product_id, "sku_snapshot": sku}],
    }
    first = client.post("/api/v1/knowledge/waves", json=payload, headers=admin_headers)
    assert first.status_code == 201, first.text
    second = client.post("/api/v1/knowledge/waves", json=payload, headers=admin_headers)
    assert second.status_code == 409, second.text


def test_review_transition_draft_reviewed_draft(admin_headers, valid_product_data):
    pt_id, def_id, product_id, sku = _seed_wave_deps(
        admin_headers, valid_product_data, sku="WAVE-REV-1"
    )
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "REVIEW-WAVE-001",
            "brand": "INSIZE",
            "product_type_id": pt_id,
            "definition_id": def_id,
            "products": [{"product_id": product_id, "sku_snapshot": sku}],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    wave_pk = created.json()["id"]

    reviewed = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Reviewed", "change_reason": "Owner review OK"},
        headers=admin_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "Reviewed"
    assert reviewed.json()["reviewed_by"] is not None

    # PATCH rejected while Reviewed
    patch_fail = client.patch(
        f"/api/v1/knowledge/waves/{wave_pk}",
        json={"brand": "OTHER"},
        headers=admin_headers,
    )
    assert patch_fail.status_code == 409, patch_fail.text

    back = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Draft", "change_reason": "Send back for edits"},
        headers=admin_headers,
    )
    assert back.status_code == 200, back.text
    assert back.json()["status"] == "Draft"
    assert back.json()["reviewed_by"] is None

    patched = client.patch(
        f"/api/v1/knowledge/waves/{wave_pk}",
        json={"brand": "INSIZE-EDITED", "policy_json": {"k": 1}},
        headers=admin_headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["brand"] == "INSIZE-EDITED"
    assert patched.json()["policy_json"] == {"k": 1}


def test_wave_create_does_not_touch_facts_products_evidence(
    admin_headers, valid_product_data
):
    pt_id, def_id, product_id, sku = _seed_wave_deps(
        admin_headers, valid_product_data, sku="WAVE-INTACT-1"
    )

    async def _baseline():
        async with TestingSessionLocal() as session:
            facts = (await session.execute(select(func.count()).select_from(KnowledgeFact))).scalar_one()
            artifacts = (
                await session.execute(select(func.count()).select_from(KnowledgeEvidenceArtifact))
            ).scalar_one()
            links = (
                await session.execute(select(func.count()).select_from(KnowledgeEvidenceLink))
            ).scalar_one()
            products = (await session.execute(select(func.count()).select_from(Product))).scalar_one()
            product_row = await session.get(Product, product_id)
            assert product_row is not None
            specs = copy.deepcopy(product_row.specifications)
            return facts, artifacts, links, products, specs

    before = _run(_baseline())

    resp = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "INTACT-WAVE-001",
            "brand": "INSIZE",
            "product_type_id": pt_id,
            "definition_id": def_id,
            "products": [{"product_id": product_id, "sku_snapshot": sku}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    wave_pk = resp.json()["id"]
    review = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Reviewed", "change_reason": "integrity check"},
        headers=admin_headers,
    )
    assert review.status_code == 200, review.text

    async def _after():
        async with TestingSessionLocal() as session:
            facts = (await session.execute(select(func.count()).select_from(KnowledgeFact))).scalar_one()
            artifacts = (
                await session.execute(select(func.count()).select_from(KnowledgeEvidenceArtifact))
            ).scalar_one()
            links = (
                await session.execute(select(func.count()).select_from(KnowledgeEvidenceLink))
            ).scalar_one()
            products = (await session.execute(select(func.count()).select_from(Product))).scalar_one()
            product_row = await session.get(Product, product_id)
            assert product_row is not None
            waves = (
                await session.execute(select(func.count()).select_from(KnowledgeWave))
            ).scalar_one()
            return facts, artifacts, links, products, copy.deepcopy(product_row.specifications), waves

    after = _run(_after())
    assert after[0] == before[0]  # facts
    assert after[1] == before[1]  # artifacts
    assert after[2] == before[2]  # links
    assert after[3] == before[3]  # products count
    assert after[4] == before[4]  # product JSONB specs untouched
    assert after[5] >= 1  # wave row created
