"""Prompt 65 — Knowledge Wave Registry PR2 (Seal + validation)."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json

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
from app.services.knowledge_wave_service import (
    build_canonical_manifest_payload,
    compute_manifest_sha256,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.conftest import (
    TestingSessionLocal,
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


async def _seed_type_with_membership(session, *, property_definition_id, code="WAVE_PT65"):
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


def _create_product(admin_headers, valid_product_data, sku="WAVE65-SKU-1"):
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


def _seed_wave_deps(admin_headers, valid_product_data, *, sku="WAVE65-SKU-1", code="WAVE_PT65"):
    product = _create_product(admin_headers, valid_product_data, sku=sku)

    async def _seed():
        async with TestingSessionLocal() as session:
            prop = await _seed_property(
                session, definition_id=f"def.wave65.{code.lower()}", key="accuracy"
            )
            pt, definition = await _seed_type_with_membership(
                session, property_definition_id=prop.definition_id, code=code
            )
            await session.commit()
            return pt.id, definition.id, product["id"], product["sku"], pt.code, definition.version

    return _run(_seed())


def _create_reviewed_wave(admin_headers, valid_product_data, *, wave_id, sku, code):
    pt_id, def_id, product_id, sku_val, pt_code, def_version = _seed_wave_deps(
        admin_headers, valid_product_data, sku=sku, code=code
    )
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": wave_id,
            "brand": "INSIZE",
            "product_type_id": pt_id,
            "definition_id": def_id,
            "policy_json": {"plane": "test", "b": 2, "a": 1},
            "products": [{"product_id": product_id, "sku_snapshot": sku_val}],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    wave_pk = created.json()["id"]
    reviewed = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Reviewed", "change_reason": "ready to seal"},
        headers=admin_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    return {
        "wave_pk": wave_pk,
        "product_id": product_id,
        "sku": sku_val,
        "pt_id": pt_id,
        "def_id": def_id,
        "pt_code": pt_code,
        "def_version": def_version,
        "body": reviewed.json(),
    }


def test_reviewed_wave_can_seal(admin_headers, valid_product_data):
    ctx = _create_reviewed_wave(
        admin_headers,
        valid_product_data,
        wave_id="SEAL-OK-001",
        sku="WAVE65-SEAL-1",
        code="WAVE_SEAL_OK",
    )
    sealed = client.post(
        f"/api/v1/knowledge/waves/{ctx['wave_pk']}/seal",
        json={"change_reason": "Owner seal"},
        headers=admin_headers,
    )
    assert sealed.status_code == 200, sealed.text
    body = sealed.json()
    assert body["status"] == "Sealed"
    assert body["manifest_sha256"] is not None
    assert len(body["manifest_sha256"]) == 64
    assert body["manifest_sha256"] == body["manifest_sha256"].lower()


def test_draft_wave_cannot_seal(admin_headers, valid_product_data):
    pt_id, def_id, product_id, sku, *_ = _seed_wave_deps(
        admin_headers, valid_product_data, sku="WAVE65-DRAFT-1", code="WAVE_DRAFT_SEAL"
    )
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "SEAL-DRAFT-001",
            "brand": "INSIZE",
            "product_type_id": pt_id,
            "definition_id": def_id,
            "products": [{"product_id": product_id, "sku_snapshot": sku}],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    wave_pk = created.json()["id"]
    sealed = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/seal",
        json={"change_reason": "should fail"},
        headers=admin_headers,
    )
    assert sealed.status_code == 409, sealed.text


def test_manifest_sha_deterministic_same_payload(admin_headers, valid_product_data):
    ctx = _create_reviewed_wave(
        admin_headers,
        valid_product_data,
        wave_id="SEAL-SHA-001",
        sku="WAVE65-SHA-1",
        code="WAVE_SHA_OK",
    )

    class _PT:
        def __init__(self, id_, code):
            self.id = id_
            self.code = code

    class _Def:
        def __init__(self, id_, version):
            self.id = id_
            self.version = version

    class _Prod:
        def __init__(self, product_id, sku_snapshot):
            self.product_id = product_id
            self.sku_snapshot = sku_snapshot

    payload_a = build_canonical_manifest_payload(
        wave_id="SEAL-SHA-001",
        brand="INSIZE",
        product_type=_PT(ctx["pt_id"], ctx["pt_code"]),
        definition=_Def(ctx["def_id"], ctx["def_version"]),
        policy_json={"plane": "test", "b": 2, "a": 1},
        products=[_Prod(ctx["product_id"], ctx["sku"])],
    )
    # Same logical payload with different key insertion order
    payload_b = build_canonical_manifest_payload(
        wave_id="SEAL-SHA-001",
        brand="INSIZE",
        product_type=_PT(ctx["pt_id"], ctx["pt_code"]),
        definition=_Def(ctx["def_id"], ctx["def_version"]),
        policy_json={"a": 1, "b": 2, "plane": "test"},
        products=[_Prod(ctx["product_id"], ctx["sku"])],
    )
    sha_a = compute_manifest_sha256(payload_a)
    sha_b = compute_manifest_sha256(payload_b)
    assert sha_a == sha_b

    # Direct json canonicalization also stable
    raw = json.dumps(payload_a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == sha_a

    sealed = client.post(
        f"/api/v1/knowledge/waves/{ctx['wave_pk']}/seal",
        json={"change_reason": "sha check"},
        headers=admin_headers,
    )
    assert sealed.status_code == 200, sealed.text
    assert sealed.json()["manifest_sha256"] == sha_a


def test_sealed_wave_rejects_mutation(admin_headers, valid_product_data):
    ctx = _create_reviewed_wave(
        admin_headers,
        valid_product_data,
        wave_id="SEAL-IMM-001",
        sku="WAVE65-IMM-1",
        code="WAVE_IMM_OK",
    )
    sealed = client.post(
        f"/api/v1/knowledge/waves/{ctx['wave_pk']}/seal",
        json={"change_reason": "freeze"},
        headers=admin_headers,
    )
    assert sealed.status_code == 200, sealed.text
    wave_pk = ctx["wave_pk"]

    for patch in (
        {"brand": "OTHER"},
        {"policy_json": {"x": 1}},
        {"product_type_id": ctx["pt_id"], "definition_id": ctx["def_id"]},
        {"products": [{"product_id": ctx["product_id"], "sku_snapshot": ctx["sku"]}]},
    ):
        resp = client.patch(
            f"/api/v1/knowledge/waves/{wave_pk}",
            json=patch,
            headers=admin_headers,
        )
        assert resp.status_code == 409, (patch, resp.text)

    # Sealed → Draft forbidden via review
    back = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Draft", "change_reason": "undo"},
        headers=admin_headers,
    )
    assert back.status_code == 409, back.text

    # Read still allowed
    got = client.get(f"/api/v1/knowledge/waves/{wave_pk}", headers=admin_headers)
    assert got.status_code == 200
    assert got.json()["status"] == "Sealed"


def test_validate_endpoint_tiers(admin_headers, valid_product_data):
    pt_id, def_id, product_id, sku, *_ = _seed_wave_deps(
        admin_headers, valid_product_data, sku="WAVE65-VAL-1", code="WAVE_VAL_OK"
    )
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "VAL-WAVE-001",
            "brand": "INSIZE",
            "product_type_id": pt_id,
            "definition_id": def_id,
            "products": [{"product_id": product_id, "sku_snapshot": sku}],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    wave_pk = created.json()["id"]

    draft_val = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/validate",
        headers=admin_headers,
    )
    assert draft_val.status_code == 200, draft_val.text
    assert draft_val.json()["validation_tier"] == "basic"
    assert draft_val.json()["ok"] is True

    reviewed = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/review",
        json={"to_status": "Reviewed", "change_reason": "review"},
        headers=admin_headers,
    )
    assert reviewed.status_code == 200, reviewed.text

    pre_seal = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/validate",
        headers=admin_headers,
    )
    assert pre_seal.status_code == 200, pre_seal.text
    assert pre_seal.json()["validation_tier"] == "pre_seal"
    assert pre_seal.json()["ok"] is True
    assert pre_seal.json()["preview_manifest_sha256"]

    sealed = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/seal",
        json={"change_reason": "seal for validate"},
        headers=admin_headers,
    )
    assert sealed.status_code == 200, sealed.text

    ready = client.post(
        f"/api/v1/knowledge/waves/{wave_pk}/validate",
        headers=admin_headers,
    )
    assert ready.status_code == 200, ready.text
    body = ready.json()
    assert body["validation_tier"] == "execution_readiness"
    assert body["ok"] is True
    assert body["stored_manifest_sha256"] == body["preview_manifest_sha256"]


def test_seal_validate_do_not_touch_facts_products_evidence(
    admin_headers, valid_product_data
):
    ctx = _create_reviewed_wave(
        admin_headers,
        valid_product_data,
        wave_id="SEAL-INTACT-001",
        sku="WAVE65-INTACT-1",
        code="WAVE_INTACT",
    )

    async def _baseline():
        async with TestingSessionLocal() as session:
            facts = (
                await session.execute(select(func.count()).select_from(KnowledgeFact))
            ).scalar_one()
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
            product_row = await session.get(Product, ctx["product_id"])
            assert product_row is not None
            return facts, artifacts, links, products, copy.deepcopy(product_row.specifications)

    before = _run(_baseline())

    assert (
        client.post(
            f"/api/v1/knowledge/waves/{ctx['wave_pk']}/validate",
            headers=admin_headers,
        ).status_code
        == 200
    )
    sealed = client.post(
        f"/api/v1/knowledge/waves/{ctx['wave_pk']}/seal",
        json={"change_reason": "integrity"},
        headers=admin_headers,
    )
    assert sealed.status_code == 200, sealed.text
    assert (
        client.post(
            f"/api/v1/knowledge/waves/{ctx['wave_pk']}/validate",
            headers=admin_headers,
        ).status_code
        == 200
    )

    async def _after():
        async with TestingSessionLocal() as session:
            facts = (
                await session.execute(select(func.count()).select_from(KnowledgeFact))
            ).scalar_one()
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
            product_row = await session.get(Product, ctx["product_id"])
            assert product_row is not None
            waves = (
                await session.execute(select(func.count()).select_from(KnowledgeWave))
            ).scalar_one()
            return (
                facts,
                artifacts,
                links,
                products,
                copy.deepcopy(product_row.specifications),
                waves,
            )

    after = _run(_after())
    assert after[0] == before[0]
    assert after[1] == before[1]
    assert after[2] == before[2]
    assert after[3] == before[3]
    assert after[4] == before[4]
    assert after[5] >= 1
