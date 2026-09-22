"""Prompt 13 / A5 — Evidence + taxonomy runtime tests."""

from __future__ import annotations

import asyncio
import copy

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models import Product
from app.db.models.knowledge import (
    KB001_EDGE_TYPES,
    KnowledgeFact,
    KnowledgeFactRevision,
    KnowledgePropertyDefinition,
)
from app.db.models.product_type import (
    ProductType,
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
    ProductTypeStatus,
)
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from tests.conftest import (
    TestingSessionLocal,
    customer_auth_headers,
    override_super_admin,
)

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("override_database")

VALID_SHA = "4b251dbbd6b662e64dcc1703dd373886f8e3df8e3363a5406bc706c8aa85123b"


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


async def _seed_type_with_membership(
    session,
    *,
    property_definition_id,
    evidence_requirement_override=None,
    code="GEN_CALIPER",
):
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
        evidence_requirement_override=evidence_requirement_override,
    )
    session.add(membership)
    await session.flush()
    return pt, definition, membership


def _create_product(admin_headers, valid_product_data, sku="P13-1"):
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


def _assign_type(product_id, pt_id):
    async def assign():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product_id)
            p.product_type_id = pt_id
            await session.commit()

    _run(assign())


def _create_asserted_fact(admin_headers, product_id, definition_id, value="0.02"):
    resp = client.post(
        f"/api/v1/knowledge/products/{product_id}/facts",
        json={"definition_id": definition_id, "value": value, "source_id": "s"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Auth ---


def test_evidence_routes_anonymous_401():
    assert client.post("/api/v1/knowledge/evidence/artifacts", json={}).status_code == 401


def test_evidence_routes_customer_403(admin_headers):
    app.dependency_overrides.pop(get_current_super_admin, None)
    customer = customer_auth_headers("09126660001")
    assert (
        client.post(
            "/api/v1/knowledge/evidence/artifacts",
            json={
                "artifact_id": "a1",
                "kind": "oem_catalogue",
                "source_ref": "x",
            },
            headers=customer,
        ).status_code
        == 403
    )


def test_taxonomy_routes_anonymous_401():
    assert client.post("/api/v1/knowledge/taxonomy/nodes", json={}).status_code == 401


# --- Evidence ---


def test_artifact_malformed_sha_rejected(admin_headers):
    resp = client.post(
        "/api/v1/knowledge/evidence/artifacts",
        json={
            "artifact_id": "bad-sha",
            "kind": "oem_catalogue",
            "checksum_sha256": "not-a-sha",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_artifact_valid_sha_accepted(admin_headers):
    resp = client.post(
        "/api/v1/knowledge/evidence/artifacts",
        json={
            "artifact_id": "insize-cat-test",
            "kind": "oem_catalogue",
            "title": "INSIZE OEM catalogue (fixture)",
            "checksum_sha256": VALID_SHA,
            "publisher": "INSIZE",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["checksum_sha256"] == VALID_SHA
    assert body["artifact_id"] == "insize-cat-test"


def test_evidence_required_publish_gate(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(
                session, definition_id="def.accuracy", key="accuracy"
            )
            pt, _, _ = await _seed_type_with_membership(
                session,
                property_definition_id="def.accuracy",
                evidence_requirement_override="required",
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="P13-ACC")
    specs_before = copy.deepcopy(product["specifications"])
    _assign_type(product["id"], pt_id)
    fact = _create_asserted_fact(
        admin_headers, product["id"], "def.accuracy", value="±0.02"
    )
    fact_id = fact["id"]

    # No evidence → publish fails
    pub = client.post(
        f"/api/v1/knowledge/facts/{fact_id}/publish",
        json={"change_reason": "no evidence yet"},
        headers=admin_headers,
    )
    assert pub.status_code == 422
    assert "Evidence" in pub.json()["message"]

    # Revision count still 1 (create only)
    async def rev_count():
        async with TestingSessionLocal() as session:
            return await session.scalar(
                select(func.count())
                .select_from(KnowledgeFactRevision)
                .where(KnowledgeFactRevision.fact_id == fact_id)
            )

    assert _run(rev_count()) == 1

    # Artifact + wrong fact link does not satisfy
    art_other = client.post(
        "/api/v1/knowledge/evidence/artifacts",
        json={
            "artifact_id": "art-other",
            "kind": "oem_catalogue",
            "checksum_sha256": VALID_SHA,
        },
        headers=admin_headers,
    )
    assert art_other.status_code == 201

    # Create another fact for wrong-link test
    async def seed2():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.other", key="other")
            # reuse same PT membership? need membership for other — skip publish path
            await session.commit()

    _run(seed2())
    # Link artifact to THIS fact
    art = client.post(
        "/api/v1/knowledge/evidence/artifacts",
        json={
            "artifact_id": "art-correct",
            "kind": "oem_catalogue",
            "checksum_sha256": VALID_SHA.replace("4", "5", 1),
            "source_ref": "catalog:insize:fixture",
        },
        headers=admin_headers,
    )
    assert art.status_code == 201, art.text
    link = client.post(
        f"/api/v1/knowledge/facts/{fact_id}/evidence-links",
        json={
            "artifact_id": art.json()["id"],
            "locator": {"page": 35, "model": "1108-150"},
        },
        headers=admin_headers,
    )
    assert link.status_code == 201, link.text

    # Linking must NOT auto-publish
    async def fact_status():
        async with TestingSessionLocal() as session:
            f = await session.get(KnowledgeFact, fact_id)
            return f.status

    assert _run(fact_status()) == "asserted"
    assert _run(rev_count()) == 1

    # Now publish succeeds
    pub2 = client.post(
        f"/api/v1/knowledge/facts/{fact_id}/publish",
        json={"change_reason": "evidence linked"},
        headers=admin_headers,
    )
    assert pub2.status_code == 200, pub2.text
    assert pub2.json()["status"] == "published"
    assert _run(rev_count()) == 2

    # specifications unchanged (no JSONB dual-write)
    async def specs_keep():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            return (p.specifications or {}).get("technical_specs", {}).get("keep")

    assert _run(specs_keep()) is True
    assert specs_before.get("technical_specs", {}).get("keep") is True


def test_evidence_for_other_fact_does_not_satisfy(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.a", key="a")
            await _seed_property(session, definition_id="def.b", key="b")
            pt, definition, _ = await _seed_type_with_membership(
                session,
                property_definition_id="def.a",
                evidence_requirement_override="required",
                code="GEN_CAL_2",
            )
            session.add(
                ProductTypeAttributeMembership(
                    product_type_definition_id=definition.id,
                    property_definition_id="def.b",
                    requiredness="optional",
                    applicability_condition={},
                    validation_overrides={},
                    evidence_requirement_override="required",
                )
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="P13-TWO")
    _assign_type(product["id"], pt_id)
    fact_a = _create_asserted_fact(admin_headers, product["id"], "def.a")
    fact_b = _create_asserted_fact(admin_headers, product["id"], "def.b")

    art = client.post(
        "/api/v1/knowledge/evidence/artifacts",
        json={
            "artifact_id": "art-b-only",
            "kind": "datasheet",
            "source_ref": "ref-b",
        },
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/facts/{fact_b['id']}/evidence-links",
            json={"artifact_id": art["id"]},
            headers=admin_headers,
        ).status_code
        == 201
    )
    # Fact A still blocked
    assert (
        client.post(
            f"/api/v1/knowledge/facts/{fact_a['id']}/publish",
            json={"change_reason": "wrong evidence"},
            headers=admin_headers,
        ).status_code
        == 422
    )


def test_recommended_and_not_required_allow_publish_without_evidence(
    admin_headers, valid_product_data
):
    for override, sku in (("recommended", "P13-REC"), ("not_required", "P13-NR")):

        async def seed(ov=override):
            async with TestingSessionLocal() as session:
                did = f"def.{ov}"
                await _seed_property(session, definition_id=did, key=ov)
                pt, _, _ = await _seed_type_with_membership(
                    session,
                    property_definition_id=did,
                    evidence_requirement_override=ov,
                    code=f"CODE_{ov.upper()}",
                )
                await session.commit()
                return pt.id, did

        pt_id, did = _run(seed())
        product = _create_product(admin_headers, valid_product_data, sku=sku)
        _assign_type(product["id"], pt_id)
        fact = _create_asserted_fact(admin_headers, product["id"], did)
        pub = client.post(
            f"/api/v1/knowledge/facts/{fact['id']}/publish",
            json={"change_reason": "no evidence needed"},
            headers=admin_headers,
        )
        assert pub.status_code == 200, pub.text


def test_duplicate_evidence_link_rejected(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.dup", key="dup")
            pt, _, _ = await _seed_type_with_membership(
                session, property_definition_id="def.dup", code="DUP_PT"
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="P13-DUP")
    _assign_type(product["id"], pt_id)
    fact = _create_asserted_fact(admin_headers, product["id"], "def.dup")
    art = client.post(
        "/api/v1/knowledge/evidence/artifacts",
        json={"artifact_id": "dup-art", "kind": "manual", "source_ref": "r"},
        headers=admin_headers,
    ).json()
    body = {"artifact_id": art["id"], "locator": {"page": 1}}
    assert (
        client.post(
            f"/api/v1/knowledge/facts/{fact['id']}/evidence-links",
            json=body,
            headers=admin_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/knowledge/facts/{fact['id']}/evidence-links",
            json=body,
            headers=admin_headers,
        ).status_code
        == 409
    )


# --- Taxonomy ---


def test_taxonomy_slug_unique_within_dimension(admin_headers):
    payload = {
        "node_id": "app-1",
        "dimension": "application",
        "node_type": "application",
        "slug": "turning",
        "name_fa": "تراشکاری",
    }
    assert (
        client.post(
            "/api/v1/knowledge/taxonomy/nodes", json=payload, headers=admin_headers
        ).status_code
        == 201
    )
    payload2 = {**payload, "node_id": "app-2"}
    assert (
        client.post(
            "/api/v1/knowledge/taxonomy/nodes", json=payload2, headers=admin_headers
        ).status_code
        == 409
    )


def test_deprecated_node_rejects_assignment(admin_headers, valid_product_data):
    node = client.post(
        "/api/v1/knowledge/taxonomy/nodes",
        json={
            "node_id": "ind-1",
            "dimension": "industry",
            "node_type": "industry",
            "slug": "auto",
            "name_fa": "خودرو",
        },
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/taxonomy/nodes/{node['id']}/status",
            json={"status": "active"},
            headers=admin_headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/knowledge/taxonomy/nodes/{node['id']}/status",
            json={"status": "deprecated"},
            headers=admin_headers,
        ).status_code
        == 200
    )
    product = _create_product(admin_headers, valid_product_data, sku="P13-TAX")
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/classification-assignments",
        json={
            "taxonomy_node_id": node["id"],
            "assignment_role": "industry",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_product_type_bridge_conflict_refused(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            pt_a = ProductType(
                code="PT_A",
                slug="pt-a",
                name_fa="A",
                status=ProductTypeStatus.ACTIVE.value,
            )
            pt_b = ProductType(
                code="PT_B",
                slug="pt-b",
                name_fa="B",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add_all([pt_a, pt_b])
            await session.commit()
            return pt_a.id, pt_b.id

    pt_a_id, pt_b_id = _run(seed())
    node = client.post(
        "/api/v1/knowledge/taxonomy/nodes",
        json={
            "node_id": "family-pt-b",
            "dimension": "family",
            "node_type": "product_type",
            "slug": "type-b",
            "name_fa": "نوع ب",
            "product_type_id": pt_b_id,
        },
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/taxonomy/nodes/{node['id']}/status",
            json={"status": "active"},
            headers=admin_headers,
        ).status_code
        == 200
    )
    product = _create_product(admin_headers, valid_product_data, sku="P13-BRIDGE")
    _assign_type(product["id"], pt_a_id)  # primary is A, bridge is B
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/classification-assignments",
        json={
            "taxonomy_node_id": node["id"],
            "assignment_role": "product_type_bridge",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422
    assert "conflict" in resp.json()["message"].lower() or "Product Type" in resp.json()[
        "message"
    ]


def test_kb001_edge_registry_unchanged():
    assert "PRODUCT_CLASSIFIED_AS" not in KB001_EDGE_TYPES


def test_a5_tables_exist_via_metadata():
    from app.db.models.knowledge import (
        KnowledgeClassificationAssignment,
        KnowledgeEvidenceArtifact,
        KnowledgeEvidenceLink,
        KnowledgeTaxonomyNode,
    )

    assert KnowledgeEvidenceArtifact.__tablename__ == "knowledge_evidence_artifacts"
    assert KnowledgeEvidenceLink.__tablename__ == "knowledge_evidence_links"
    assert KnowledgeTaxonomyNode.__tablename__ == "knowledge_taxonomy_nodes"
    assert (
        KnowledgeClassificationAssignment.__tablename__
        == "knowledge_classification_assignments"
    )


def test_commerce_category_not_mutated_by_taxonomy(admin_headers):
    # Creating a taxonomy node with no commerce_category_id must not touch categories.
    async def count_categories():
        async with TestingSessionLocal() as session:
            return await session.scalar(text("SELECT COUNT(*) FROM categories"))

    before = _run(count_categories())
    assert (
        client.post(
            "/api/v1/knowledge/taxonomy/nodes",
            json={
                "node_id": "tech-1",
                "dimension": "technical",
                "node_type": "technical_class",
                "slug": "ip54",
                "name_fa": "IP54",
            },
            headers=admin_headers,
        ).status_code
        == 201
    )
    assert _run(count_categories()) == before
