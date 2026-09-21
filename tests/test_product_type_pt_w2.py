"""PT-W2 Product Type Definitions + Attribute Memberships."""

from __future__ import annotations

import asyncio

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models import Product
from app.db.models.knowledge import KnowledgePropertyDefinition
from app.db.models.product_type import (
    ProductType,
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
    ProductTypeStatus,
)
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import (
    USE_POSTGRES_TESTS,
    TestingSessionLocal,
    customer_auth_headers,
    override_super_admin,
)

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("override_database")


def _run(coro):
    return asyncio.run(coro)


async def _seed_property(
    session,
    *,
    definition_id: str,
    key: str,
    status: str = "active",
    data_type: str = "string",
    validation: dict | None = None,
    enum_values: list | None = None,
) -> KnowledgePropertyDefinition:
    prop = KnowledgePropertyDefinition(
        definition_id=definition_id,
        key=key,
        data_type=data_type,
        label_en=key,
        label_fa=key,
        validation=validation if validation is not None else {},
        enum_values=enum_values,
        version="1.0.0",
        status=status,
        comparable=False,
        filterable=False,
        customer_facing=False,
    )
    session.add(prop)
    await session.flush()
    return prop


async def _seed_product_type(
    session,
    *,
    code: str = "GEN_CALIPER",
    slug: str = "general-purpose-caliper",
) -> ProductType:
    pt = ProductType(
        code=code,
        slug=slug,
        name_fa="کولیس عمومی",
        name_en="General-purpose Caliper",
        status=ProductTypeStatus.ACTIVE.value,
    )
    session.add(pt)
    await session.flush()
    return pt


def _admin_headers():
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    return {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}


@pytest.fixture
def admin_headers():
    headers = _admin_headers()
    yield headers
    app.dependency_overrides.pop(get_current_super_admin, None)


# --- Auth matrix ---


def test_definition_routes_anonymous_401():
    assert (
        client.post("/api/v1/knowledge/product-types/1/definitions", json={}).status_code
        == 401
    )
    assert client.get("/api/v1/knowledge/product-types/1/definitions").status_code == 401
    assert client.get("/api/v1/knowledge/product-type-definitions/1").status_code == 401
    assert (
        client.post(
            "/api/v1/knowledge/product-type-definitions/1/memberships",
            json={"property_definition_id": "x", "requiredness": "optional"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/knowledge/product-type-definitions/1/activate",
            json={"change_reason": "x"},
        ).status_code
        == 401
    )


def test_definition_routes_non_super_admin_403(admin_headers):
    # Ensure override cleared so real AuthZ runs for customer.
    app.dependency_overrides.pop(get_current_super_admin, None)
    customer = customer_auth_headers("09125550001")
    assert (
        client.post(
            "/api/v1/knowledge/product-types/1/definitions",
            json={},
            headers=customer,
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/v1/knowledge/product-types/1/definitions",
            headers=customer,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/knowledge/product-type-definitions/1/activate",
            json={"change_reason": "nope"},
            headers=customer,
        ).status_code
        == 403
    )


def test_activation_requires_change_reason(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    created = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    )
    assert created.status_code == 201
    def_id = created.json()["id"]
    missing = client.post(
        f"/api/v1/knowledge/product-type-definitions/{def_id}/activate",
        json={},
        headers=admin_headers,
    )
    assert missing.status_code == 422


def test_activation_reviewer_from_auth_not_body(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.range", key="measuring_range")
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    created = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    )
    def_id = created.json()["id"]
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{def_id}/memberships",
        json={
            "property_definition_id": "def.range",
            "requiredness": "required",
        },
        headers=admin_headers,
    )
    activated = client.post(
        f"/api/v1/knowledge/product-type-definitions/{def_id}/activate",
        json={
            "change_reason": "approved by steward",
            "reviewed_by_user_id": 999999,
        },
        headers=admin_headers,
    )
    assert activated.status_code == 200
    body = activated.json()
    assert body["status"] == "active"
    assert body["change_reason"] == "approved by steward"
    assert body["reviewed_by_user_id"] is not None
    assert body["reviewed_by_user_id"] != 999999
    assert body["activated_at"] is not None


# --- Versioning + activation lifecycle ---


def test_create_draft_auto_version_and_activate_v1_v2(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.a", key="prop_a")
            await _seed_property(session, definition_id="def.b", key="prop_b")
            await session.commit()
            return pt.id

    pt_id = _run(seed())

    v1 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={"notes": "v1"},
        headers=admin_headers,
    )
    assert v1.status_code == 201
    assert v1.json()["version"] == 1
    assert v1.json()["status"] == "draft"
    v1_id = v1.json()["id"]

    m1 = client.post(
        f"/api/v1/knowledge/product-type-definitions/{v1_id}/memberships",
        json={
            "property_definition_id": "def.a",
            "requiredness": "required",
            "display_order": 1,
        },
        headers=admin_headers,
    )
    assert m1.status_code == 201
    m1_id = m1.json()["id"]

    act1 = client.post(
        f"/api/v1/knowledge/product-type-definitions/{v1_id}/activate",
        json={"change_reason": "activate v1"},
        headers=admin_headers,
    )
    assert act1.status_code == 200
    assert act1.json()["status"] == "active"
    assert len(act1.json()["memberships"]) == 1

    v2 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    )
    assert v2.status_code == 201
    assert v2.json()["version"] == 2
    assert v2.json()["status"] == "draft"
    v2_id = v2.json()["id"]

    # While V2 draft, V1 remains sole active
    listed = client.get(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        headers=admin_headers,
    )
    assert listed.status_code == 200
    by_ver = {d["version"]: d for d in listed.json()["items"]}
    assert by_ver[1]["status"] == "active"
    assert by_ver[2]["status"] == "draft"

    client.post(
        f"/api/v1/knowledge/product-type-definitions/{v2_id}/memberships",
        json={
            "property_definition_id": "def.a",
            "requiredness": "optional",
        },
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{v2_id}/memberships",
        json={
            "property_definition_id": "def.b",
            "requiredness": "required",
        },
        headers=admin_headers,
    )

    act2 = client.post(
        f"/api/v1/knowledge/product-type-definitions/{v2_id}/activate",
        json={"change_reason": "activate v2 supersedes v1"},
        headers=admin_headers,
    )
    assert act2.status_code == 200
    assert act2.json()["status"] == "active"
    assert act2.json()["version"] == 2

    listed2 = client.get(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        headers=admin_headers,
    )
    by_ver2 = {d["version"]: d for d in listed2.json()["items"]}
    assert by_ver2[1]["status"] == "retired"
    assert by_ver2[2]["status"] == "active"

    # V1 historical memberships unchanged
    v1_get = client.get(
        f"/api/v1/knowledge/product-type-definitions/{v1_id}",
        headers=admin_headers,
    )
    assert v1_get.status_code == 200
    assert v1_get.json()["status"] == "retired"
    assert len(v1_get.json()["memberships"]) == 1
    assert v1_get.json()["memberships"][0]["id"] == m1_id
    assert v1_get.json()["memberships"][0]["requiredness"] == "required"


def test_duplicate_version_rejected(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    assert (
        client.post(
            f"/api/v1/knowledge/product-types/{pt_id}/definitions",
            json={"version": 1},
            headers=admin_headers,
        ).status_code
        == 201
    )
    dup = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={"version": 1},
        headers=admin_headers,
    )
    assert dup.status_code == 409


# --- Immutability ---


def test_active_and_retired_memberships_immutable(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.x", key="prop_x")
            await _seed_property(session, definition_id="def.y", key="prop_y")
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    v1 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    mid = client.post(
        f"/api/v1/knowledge/product-type-definitions/{v1['id']}/memberships",
        json={"property_definition_id": "def.x", "requiredness": "optional"},
        headers=admin_headers,
    ).json()["id"]
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{v1['id']}/activate",
        json={"change_reason": "lock v1"},
        headers=admin_headers,
    )

    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{v1['id']}/memberships",
            json={"property_definition_id": "def.y", "requiredness": "optional"},
            headers=admin_headers,
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/knowledge/product-type-definitions/{v1['id']}/memberships/{mid}",
            json={"requiredness": "required"},
            headers=admin_headers,
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/knowledge/product-type-definitions/{v1['id']}/memberships/{mid}",
            headers=admin_headers,
        ).status_code
        == 409
    )

    # Retire via V2 activation, then prove V1 still immutable
    v2 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{v2['id']}/memberships",
        json={"property_definition_id": "def.y", "requiredness": "required"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{v2['id']}/activate",
        json={"change_reason": "retire v1"},
        headers=admin_headers,
    )
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{v1['id']}/memberships",
            json={"property_definition_id": "def.y", "requiredness": "optional"},
            headers=admin_headers,
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/knowledge/product-type-definitions/{v1['id']}/memberships/{mid}",
            headers=admin_headers,
        ).status_code
        == 409
    )


def test_draft_memberships_mutable(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.m", key="prop_m")
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    added = client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
        json={"property_definition_id": "def.m", "requiredness": "optional"},
        headers=admin_headers,
    )
    assert added.status_code == 201
    mid = added.json()["id"]
    upd = client.put(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships/{mid}",
        json={"requiredness": "required", "display_order": 3},
        headers=admin_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["requiredness"] == "required"
    assert upd.json()["display_order"] == 3
    assert (
        client.delete(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships/{mid}",
            headers=admin_headers,
        ).status_code
        == 204
    )


# --- Membership semantics ---


def test_duplicate_property_in_same_definition_rejected(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.dup", key="prop_dup")
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={"property_definition_id": "def.dup", "requiredness": "optional"},
            headers=admin_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={"property_definition_id": "def.dup", "requiredness": "required"},
            headers=admin_headers,
        ).status_code
        == 409
    )


def test_same_property_allowed_across_definition_versions(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.shared", key="prop_shared")
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d1 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    d2 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d1['id']}/memberships",
            json={"property_definition_id": "def.shared", "requiredness": "optional"},
            headers=admin_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d2['id']}/memberships",
            json={"property_definition_id": "def.shared", "requiredness": "required"},
            headers=admin_headers,
        ).status_code
        == 201
    )


@pytest.mark.parametrize(
    "requiredness",
    ["required", "optional", "conditional", "forbidden"],
)
def test_requiredness_vocabulary(admin_headers, requiredness):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session, code=f"PT_{requiredness}", slug=f"pt-{requiredness}")
            await _seed_property(
                session,
                definition_id=f"def.{requiredness}",
                key=f"key_{requiredness}",
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    payload = {
        "property_definition_id": f"def.{requiredness}",
        "requiredness": requiredness,
    }
    if requiredness == "conditional":
        payload["applicability_condition"] = {"property": "readout", "equals": "digital"}
    resp = client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
        json=payload,
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["requiredness"] == requiredness


def test_conditional_without_applicability_fails(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.cond", key="prop_cond")
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.cond",
                "requiredness": "conditional",
                "applicability_condition": {},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )


def test_missing_property_rejected(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.does.not.exist",
                "requiredness": "optional",
            },
            headers=admin_headers,
        ).status_code
        == 422
    )


def test_activation_rejects_deprecated_property(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(
                session, definition_id="def.dep", key="prop_dep", status="draft"
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    # Draft authoring may reference draft property
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={"property_definition_id": "def.dep", "requiredness": "optional"},
            headers=admin_headers,
        ).status_code
        == 201
    )

    async def deprecate():
        async with TestingSessionLocal() as session:
            prop = (
                await session.execute(
                    select(KnowledgePropertyDefinition).where(
                        KnowledgePropertyDefinition.definition_id == "def.dep"
                    )
                )
            ).scalar_one()
            prop.status = "deprecated"
            await session.commit()

    _run(deprecate())
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/activate",
            json={"change_reason": "should fail"},
            headers=admin_headers,
        ).status_code
        == 422
    )


def test_validation_overrides_cannot_redefine_identity(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(
                session,
                definition_id="def.vo",
                key="prop_vo",
                data_type="number",
                validation={"min": 0, "max": 100},
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.vo",
                "requiredness": "optional",
                "validation_overrides": {"data_type": "number"},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.vo",
                "requiredness": "optional",
                "validation_overrides": {"unit_dimension": "length"},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )
    # Ambiguous / unproven narrowing keys are rejected (not silently accepted).
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.vo",
                "requiredness": "optional",
                "validation_overrides": {"pattern": ".*"},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )


def test_numeric_override_narrowing_accepted(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(
                session,
                definition_id="def.num",
                key="prop_num",
                data_type="number",
                validation={"min": 0, "max": 100},
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    resp = client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
        json={
            "property_definition_id": "def.num",
            "requiredness": "optional",
            "validation_overrides": {"min": 10, "max": 90},
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["validation_overrides"] == {"min": 10, "max": 90}


def test_numeric_override_widening_rejected(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(
                session,
                definition_id="def.wide",
                key="prop_wide",
                data_type="number",
                validation={"min": 0, "max": 100},
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.wide",
                "requiredness": "optional",
                "validation_overrides": {"min": -1},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.wide",
                "requiredness": "optional",
                "validation_overrides": {"max": 101},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )
    # Previously accepted widening pair must now fail.
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.wide",
                "requiredness": "optional",
                "validation_overrides": {"min": -100, "max": 1000},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )


def test_numeric_override_may_introduce_absent_bound(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(
                session,
                definition_id="def.addmin",
                key="prop_addmin",
                data_type="number",
                validation={"type": "number"},
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    resp = client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
        json={
            "property_definition_id": "def.addmin",
            "requiredness": "optional",
            "validation_overrides": {"min": 0},
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201


def test_length_override_narrowing_and_widening(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(
                session,
                definition_id="def.len",
                key="prop_len",
                data_type="string",
                validation={"min_length": 2, "max_length": 20},
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
            json={
                "property_definition_id": "def.len",
                "requiredness": "optional",
                "validation_overrides": {"min_length": 4, "max_length": 10},
            },
            headers=admin_headers,
        ).status_code
        == 201
    )
    d2 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d2['id']}/memberships",
            json={
                "property_definition_id": "def.len",
                "requiredness": "optional",
                "validation_overrides": {"min_length": 1},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d2['id']}/memberships",
            json={
                "property_definition_id": "def.len",
                "requiredness": "optional",
                "validation_overrides": {"max_length": 21},
            },
            headers=admin_headers,
        ).status_code
        == 422
    )


def test_enum_subset_must_be_canonical_subset(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(
                session,
                definition_id="def.enum",
                key="prop_enum",
                data_type="enum",
                validation={"type": "enum"},
                enum_values=[
                    {"code": "A", "label_en": "A", "label_fa": "الف"},
                    {"code": "B", "label_en": "B", "label_fa": "ب"},
                    {"code": "C", "label_en": "C", "label_fa": "ج"},
                ],
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    ok = client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
        json={
            "property_definition_id": "def.enum",
            "requiredness": "optional",
            "validation_overrides": {"enum_subset": ["A", "C"]},
        },
        headers=admin_headers,
    )
    assert ok.status_code == 201
    assert ok.json()["validation_overrides"]["enum_subset"] == ["A", "C"]

    d2 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    bad = client.post(
        f"/api/v1/knowledge/product-type-definitions/{d2['id']}/memberships",
        json={
            "property_definition_id": "def.enum",
            "requiredness": "optional",
            "validation_overrides": {"enum_subset": ["A", "X"]},
        },
        headers=admin_headers,
    )
    assert bad.status_code == 422


def test_activation_rejects_stale_override_after_canonical_change(admin_headers):
    """Draft override valid at authoring must revalidate against current Property."""

    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(
                session,
                definition_id="def.stale",
                key="prop_stale",
                data_type="number",
                validation={"min": 0, "max": 100},
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    added = client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
        json={
            "property_definition_id": "def.stale",
            "requiredness": "optional",
            "validation_overrides": {"min": 10, "max": 90},
        },
        headers=admin_headers,
    )
    assert added.status_code == 201

    async def tighten_canonical():
        async with TestingSessionLocal() as session:
            prop = (
                await session.execute(
                    select(KnowledgePropertyDefinition).where(
                        KnowledgePropertyDefinition.definition_id == "def.stale"
                    )
                )
            ).scalar_one()
            # Membership min=10 now widens the new canonical min=20.
            prop.validation = {"min": 20, "max": 80}
            await session.commit()

    _run(tighten_canonical())
    assert (
        client.post(
            f"/api/v1/knowledge/product-type-definitions/{d['id']}/activate",
            json={"change_reason": "stale override must fail"},
            headers=admin_headers,
        ).status_code
        == 422
    )


# --- DB one-active + FK / no JSONB touch ---


def test_db_one_active_partial_unique_postgres():
    """Postgres partial unique index rejects two active Definitions."""
    if not USE_POSTGRES_TESTS:
        pytest.skip("partial unique index enforced on Postgres only")

    async def body():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await session.flush()
            session.add(
                ProductTypeDefinition(
                    product_type_id=pt.id,
                    version=1,
                    status=ProductTypeDefinitionStatus.ACTIVE.value,
                )
            )
            await session.commit()
            session.add(
                ProductTypeDefinition(
                    product_type_id=pt.id,
                    version=2,
                    status=ProductTypeDefinitionStatus.ACTIVE.value,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    _run(body())


def test_db_one_active_enforced_via_service_activation(admin_headers):
    """Service never leaves two actives; second activate retires prior."""

    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.one", key="prop_one")
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d1 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{d1['id']}/memberships",
        json={"property_definition_id": "def.one", "requiredness": "optional"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{d1['id']}/activate",
        json={"change_reason": "first"},
        headers=admin_headers,
    )
    d2 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{d2['id']}/memberships",
        json={"property_definition_id": "def.one", "requiredness": "required"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{d2['id']}/activate",
        json={"change_reason": "second"},
        headers=admin_headers,
    )

    async def count_active():
        async with TestingSessionLocal() as session:
            rows = (
                await session.execute(
                    select(ProductTypeDefinition).where(
                        ProductTypeDefinition.product_type_id == pt_id,
                        ProductTypeDefinition.status == "active",
                    )
                )
            ).scalars().all()
            return len(rows)

    assert _run(count_active()) == 1


def test_membership_does_not_duplicate_property_fields(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.own", key="owned_key")
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    m = client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
        json={"property_definition_id": "def.own", "requiredness": "optional"},
        headers=admin_headers,
    ).json()
    assert "label_en" not in m
    assert "data_type" not in m
    assert "key" not in m
    assert m["property_definition_id"] == "def.own"

    async def assert_columns():
        async with TestingSessionLocal() as session:
            row = (
                await session.execute(
                    select(ProductTypeAttributeMembership).where(
                        ProductTypeAttributeMembership.id == m["id"]
                    )
                )
            ).scalar_one()
            assert not hasattr(row, "label_en")
            assert not hasattr(row, "data_type")
            assert row.property_definition_id == "def.own"

    _run(assert_columns())


def test_no_legacy_specifications_jsonb_mutation(admin_headers, valid_product_data):
    payload = {
        **valid_product_data,
        "sku": "PTW2-NO-JSONB",
        "specifications": {
            "technical_specs": {"range": "0-200mm"},
            "features": {"legacy": True},
            "dimensions": {},
            "optional_accessories": [],
        },
    }
    created = client.post(
        "/api/v1/products/",
        json=payload,
        headers=admin_headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    async def snapshot_and_seed():
        async with TestingSessionLocal() as session:
            product = (
                await session.execute(select(Product).where(Product.id == product_id))
            ).scalar_one()
            before = dict(product.specifications)
            pt = await _seed_product_type(session)
            await _seed_property(session, definition_id="def.jsonb", key="prop_jsonb")
            await session.commit()
            return pt.id, before

    pt_id, before = _run(snapshot_and_seed())
    d = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/memberships",
        json={"property_definition_id": "def.jsonb", "requiredness": "optional"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{d['id']}/activate",
        json={"change_reason": "no jsonb touch"},
        headers=admin_headers,
    )

    async def check():
        async with TestingSessionLocal() as session:
            product = (
                await session.execute(select(Product).where(Product.id == product_id))
            ).scalar_one()
            assert product.specifications == before
            assert product.product_type_id is None

    _run(check())


def test_product_type_delete_blocked_when_definition_exists():
    async def body():
        async with TestingSessionLocal() as session:
            if not USE_POSTGRES_TESTS:
                await session.execute(text("PRAGMA foreign_keys=ON"))
            pt = await _seed_product_type(session)
            session.add(
                ProductTypeDefinition(
                    product_type_id=pt.id,
                    version=1,
                    status=ProductTypeDefinitionStatus.DRAFT.value,
                )
            )
            await session.commit()
            await session.delete(pt)
            with pytest.raises(IntegrityError):
                await session.commit()

    _run(body())
