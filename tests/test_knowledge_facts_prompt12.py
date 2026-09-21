"""Prompt 12 / A4 — Facts + append-only revisions."""

from __future__ import annotations

import asyncio
import copy

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models import Product
from app.db.models.knowledge import (
    KnowledgeFact,
    KnowledgeFactRevision,
    KnowledgePropertyDefinition,
    KnowledgeUnit,
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


@pytest.fixture
def admin_headers():
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    headers = {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}
    yield headers
    app.dependency_overrides.pop(get_current_super_admin, None)


async def _seed_unit(session, *, dimension="length", code="mm", aliases=None):
    unit = KnowledgeUnit(
        dimension=dimension,
        canonical_code=code,
        aliases=aliases or ["میلی‌متر", "mm"],
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
    data_type="number",
    validation=None,
    enum_values=None,
    unit_dimension=None,
    default_unit=None,
):
    prop = KnowledgePropertyDefinition(
        definition_id=definition_id,
        key=key,
        data_type=data_type,
        unit_dimension=unit_dimension,
        default_unit=default_unit,
        label_en=key,
        label_fa=key,
        validation=validation or {},
        enum_values=enum_values,
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
    requiredness="optional",
    validation_overrides=None,
    evidence_requirement_override=None,
    applicability_condition=None,
):
    pt = ProductType(
        code="GEN_CAL",
        slug="general-purpose-caliper",
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
        requiredness=requiredness,
        applicability_condition=applicability_condition or {},
        validation_overrides=validation_overrides or {},
        evidence_requirement_override=evidence_requirement_override,
    )
    session.add(membership)
    await session.flush()
    return pt, definition, membership


def _create_product(admin_headers, valid_product_data, sku="FACT-1"):
    payload = {**valid_product_data, "sku": sku, "specifications": {
        "technical_specs": {"keep": True},
        "features": {},
        "dimensions": {},
        "optional_accessories": [],
    }}
    resp = client.post("/api/v1/products/", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Auth ---


def test_fact_routes_anonymous_401():
    assert client.post("/api/v1/knowledge/products/1/facts", json={}).status_code == 401
    assert client.get("/api/v1/knowledge/products/1/facts").status_code == 401
    assert client.get("/api/v1/knowledge/facts/1").status_code == 401
    assert client.put("/api/v1/knowledge/facts/1", json={}).status_code == 401
    assert client.post("/api/v1/knowledge/facts/1/publish", json={"change_reason": "x"}).status_code == 401


def test_fact_routes_non_admin_403(admin_headers):
    app.dependency_overrides.pop(get_current_super_admin, None)
    customer = customer_auth_headers("09126660001")
    assert client.get("/api/v1/knowledge/products/1/facts", headers=customer).status_code == 403
    assert client.post(
        "/api/v1/knowledge/facts/1/publish",
        json={"change_reason": "x"},
        headers=customer,
    ).status_code == 403


# --- Lifecycle / revisions ---


def test_create_update_publish_dispute_deprecate_revisions(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_unit(session)
            await _seed_property(
                session,
                definition_id="def.res",
                key="resolution",
                data_type="number",
                validation={"min": 0, "max": 10},
                unit_dimension="length",
                default_unit="mm",
            )
            pt, definition, _ = await _seed_type_with_membership(
                session,
                property_definition_id="def.res",
                validation_overrides={"max": 5},
            )
            await session.commit()
            return pt.id, definition.id

    pt_id, defn_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-LIFE")

    async def assign():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            p.product_type_id = pt_id
            await session.commit()

    _run(assign())

    created = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={
            "definition_id": "def.res",
            "value": 0.01,
            "unit": "mm",
            "source_id": "manual:test",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    fact = created.json()
    assert fact["status"] == "asserted"
    assert fact["product_type_definition_id"] == defn_id
    fact_id = fact["id"]

    revs = client.get(f"/api/v1/knowledge/facts/{fact_id}/revisions", headers=admin_headers)
    assert revs.status_code == 200
    assert revs.json()["total"] == 1
    assert revs.json()["items"][0]["revision_number"] == 1

    updated = client.put(
        f"/api/v1/knowledge/facts/{fact_id}",
        json={"value": 0.02, "change_reason": "tweak"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["value"] == 0.02
    revs2 = client.get(f"/api/v1/knowledge/facts/{fact_id}/revisions", headers=admin_headers).json()
    assert revs2["total"] == 2
    assert revs2["items"][0]["value"] == 0.01
    assert revs2["items"][1]["value"] == 0.02

    published = client.post(
        f"/api/v1/knowledge/facts/{fact_id}/publish",
        json={"change_reason": "ready"},
        headers=admin_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert client.get(f"/api/v1/knowledge/facts/{fact_id}/revisions", headers=admin_headers).json()["total"] == 3

    disputed = client.post(
        f"/api/v1/knowledge/facts/{fact_id}/dispute",
        json={"change_reason": "conflict"},
        headers=admin_headers,
    )
    assert disputed.status_code == 200
    assert disputed.json()["status"] == "disputed"

    # dispute only from published — re-seed path: deprecate from disputed
    deprecated = client.post(
        f"/api/v1/knowledge/facts/{fact_id}/deprecate",
        json={"change_reason": "retire"},
        headers=admin_headers,
    )
    assert deprecated.status_code == 200
    assert deprecated.json()["status"] == "deprecated"
    assert client.get(f"/api/v1/knowledge/facts/{fact_id}/revisions", headers=admin_headers).json()["total"] == 5


def test_failed_publish_is_atomic(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(
                session,
                definition_id="def.bool",
                key="data_output",
                data_type="boolean",
            )
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-ATOMIC")
    created = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={
            "definition_id": "def.bool",
            "value": True,
            "source_id": "manual:atomic",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201
    fact_id = created.json()["id"]
    before = client.get(f"/api/v1/knowledge/facts/{fact_id}", headers=admin_headers).json()
    fail = client.post(
        f"/api/v1/knowledge/facts/{fact_id}/publish",
        json={"change_reason": "no type"},
        headers=admin_headers,
    )
    assert fail.status_code == 422
    after = client.get(f"/api/v1/knowledge/facts/{fact_id}", headers=admin_headers).json()
    assert after["status"] == before["status"] == "asserted"
    assert client.get(f"/api/v1/knowledge/facts/{fact_id}/revisions", headers=admin_headers).json()["total"] == 1


def test_duplicate_current_fact_rejected(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(
                session, definition_id="def.dup", key="dup", data_type="string"
            )
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-DUP")
    body = {"definition_id": "def.dup", "value": "a", "source_id": "s1"}
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json=body,
        headers=admin_headers,
    ).status_code == 201
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json=body,
        headers=admin_headers,
    ).status_code == 409


# --- Validation matrix ---


@pytest.mark.parametrize(
    "data_type,value,extra",
    [
        ("boolean", True, {}),
        ("integer", 4, {}),
        ("number", 0.01, {"unit_dimension": "length", "default_unit": "mm"}),
        ("quantity", {"magnitude": 0.02, "qualifier": "±"}, {"unit_dimension": "length", "default_unit": "mm"}),
        ("range", {"min": 0, "max": 150}, {"unit_dimension": "length", "default_unit": "mm"}),
        ("enum", "digital", {"enum_values": [
            {"code": "digital", "label_en": "D", "label_fa": "د"},
            {"code": "dial", "label_en": "Dial", "label_fa": "ع"},
        ]}),
        ("string", "abc", {}),
        ("string_array", ["a", "b"], {}),
    ],
)
def test_datatype_shapes_accepted(admin_headers, valid_product_data, data_type, value, extra):
    async def seed():
        async with TestingSessionLocal() as session:
            if extra.get("unit_dimension"):
                await _seed_unit(session)
            await _seed_property(
                session,
                definition_id=f"def.{data_type}",
                key=f"k_{data_type}",
                data_type=data_type,
                validation={},
                enum_values=extra.get("enum_values"),
                unit_dimension=extra.get("unit_dimension"),
                default_unit=extra.get("default_unit"),
            )
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku=f"DT-{data_type}")
    payload = {
        "definition_id": f"def.{data_type}",
        "value": value,
        "source_id": "seed",
    }
    if extra.get("default_unit"):
        payload["unit"] = extra["default_unit"]
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json=payload,
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text


def test_bool_rejected_as_integer_and_number(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.i", key="i", data_type="integer")
            await _seed_property(session, definition_id="def.n", key="n", data_type="number")
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-BOOL")
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.i", "value": True, "source_id": "s"},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.n", "value": True, "source_id": "s"},
        headers=admin_headers,
    ).status_code == 422


def test_range_min_gt_max_and_unknown_enum(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_unit(session)
            await _seed_property(
                session,
                definition_id="def.rng",
                key="rng",
                data_type="range",
                unit_dimension="length",
                default_unit="mm",
            )
            await _seed_property(
                session,
                definition_id="def.en",
                key="en",
                data_type="enum",
                enum_values=[{"code": "A", "label_en": "A", "label_fa": "ا"}],
            )
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-BAD")
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.rng", "value": {"min": 5, "max": 1}, "unit": "mm", "source_id": "s"},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.en", "value": "X", "source_id": "s"},
        headers=admin_headers,
    ).status_code == 422


def test_unit_dimension_and_canonicalization(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_unit(session, aliases=["میلی‌متر", "MM"])
            await _seed_property(
                session,
                definition_id="def.u",
                key="u",
                data_type="number",
                unit_dimension="length",
                default_unit="mm",
            )
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-UNIT")
    ok = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.u", "value": 1, "unit": "میلی‌متر", "source_id": "s"},
        headers=admin_headers,
    )
    assert ok.status_code == 201
    assert ok.json()["unit"] == "mm"
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.u", "value": 1, "unit": "deg", "source_id": "s2"},
        headers=admin_headers,
    ).status_code in (409, 422)  # may conflict if first exists; use second product
    product2 = _create_product(admin_headers, valid_product_data, sku="FACT-UNIT2")
    assert client.post(
        f"/api/v1/knowledge/products/{product2['id']}/facts",
        json={"definition_id": "def.u", "value": 1, "unit": "deg", "source_id": "s"},
        headers=admin_headers,
    ).status_code == 422


def test_canonical_and_pt_w2_narrowing_bounds(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_unit(session)
            await _seed_property(
                session,
                definition_id="def.bound",
                key="bound",
                data_type="number",
                validation={"min": 0, "max": 100},
                unit_dimension="length",
                default_unit="mm",
            )
            pt, _, _ = await _seed_type_with_membership(
                session,
                property_definition_id="def.bound",
                validation_overrides={"min": 10, "max": 50},
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-BOUND")
    # without assignment: canonical only — 5 ok
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.bound", "value": 5, "unit": "mm", "source_id": "s"},
        headers=admin_headers,
    ).status_code == 201

    product2 = _create_product(admin_headers, valid_product_data, sku="FACT-BOUND2")

    async def assign():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product2["id"])
            p.product_type_id = pt_id
            await session.commit()

    _run(assign())
    # with PT override: 5 below narrowed min=10
    assert client.post(
        f"/api/v1/knowledge/products/{product2['id']}/facts",
        json={"definition_id": "def.bound", "value": 5, "unit": "mm", "source_id": "s"},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        f"/api/v1/knowledge/products/{product2['id']}/facts",
        json={"definition_id": "def.bound", "value": 20, "unit": "mm", "source_id": "s"},
        headers=admin_headers,
    ).status_code == 201


# --- Product Type applicability / publish gates ---


def test_unassigned_can_assert_cannot_publish(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.ua", key="ua", data_type="string")
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-UA")
    created = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.ua", "value": "x", "source_id": "s"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert created.json()["product_type_definition_id"] is None
    assert client.post(
        f"/api/v1/knowledge/facts/{created.json()['id']}/publish",
        json={"change_reason": "no"},
        headers=admin_headers,
    ).status_code == 422


def test_forbidden_and_missing_membership(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.forb", key="forb", data_type="string")
            await _seed_property(session, definition_id="def.other", key="other", data_type="string")
            pt, _, _ = await _seed_type_with_membership(
                session, property_definition_id="def.forb", requiredness="forbidden"
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-FORB")

    async def assign():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            p.product_type_id = pt_id
            await session.commit()

    _run(assign())
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.forb", "value": "x", "source_id": "s"},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.other", "value": "x", "source_id": "s"},
        headers=admin_headers,
    ).status_code == 422


def test_conditional_unresolved_blocks_publish(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.cond", key="cond", data_type="string")
            pt, _, _ = await _seed_type_with_membership(
                session,
                property_definition_id="def.cond",
                requiredness="conditional",
                applicability_condition={"property": "readout", "equals": "digital"},
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-COND")

    async def assign():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            p.product_type_id = pt_id
            await session.commit()

    _run(assign())
    created = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.cond", "value": "x", "source_id": "s"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    pub = client.post(
        f"/api/v1/knowledge/facts/{created.json()['id']}/publish",
        json={"change_reason": "try"},
        headers=admin_headers,
    )
    assert pub.status_code == 422
    assert pub.json()["error_code"] == "FACT_APPLICABILITY_UNRESOLVED"


def test_evidence_required_blocks_publish(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.ev", key="ev", data_type="string")
            pt, _, _ = await _seed_type_with_membership(
                session,
                property_definition_id="def.ev",
                evidence_requirement_override="required",
            )
            await session.commit()
            return pt.id

    pt_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-EV")

    async def assign():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            p.product_type_id = pt_id
            await session.commit()

    _run(assign())
    created = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.ev", "value": "x", "source_id": "s"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert client.post(
        f"/api/v1/knowledge/facts/{created.json()['id']}/publish",
        json={"change_reason": "need evidence"},
        headers=admin_headers,
    ).status_code == 422


def test_definition_v1_pin_survives_v2_activation(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.pin", key="pin", data_type="string")
            pt, d1, _ = await _seed_type_with_membership(
                session, property_definition_id="def.pin"
            )
            await session.commit()
            return pt.id, d1.id

    pt_id, d1_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-PIN")

    async def assign():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            p.product_type_id = pt_id
            await session.commit()

    _run(assign())
    created = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.pin", "value": "v", "source_id": "s"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    fact_id = created.json()["id"]
    assert client.post(
        f"/api/v1/knowledge/facts/{fact_id}/publish",
        json={"change_reason": "pub"},
        headers=admin_headers,
    ).status_code == 200

    # Activate V2 for same Product Type
    v2 = client.post(
        f"/api/v1/knowledge/product-types/{pt_id}/definitions",
        json={},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{v2['id']}/memberships",
        json={"property_definition_id": "def.pin", "requiredness": "optional"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/knowledge/product-type-definitions/{v2['id']}/activate",
        json={"change_reason": "v2"},
        headers=admin_headers,
    )
    fact = client.get(f"/api/v1/knowledge/facts/{fact_id}", headers=admin_headers).json()
    assert fact["product_type_definition_id"] == d1_id
    assert fact["product_type_definition_id"] != v2["id"]


def test_no_rejected_fact_status_and_db_check():
    async def body():
        async with TestingSessionLocal() as session:
            if not USE_POSTGRES_TESTS:
                await session.execute(text("PRAGMA foreign_keys=ON"))
            from app.db.models.product import Brand, Category

            cat = Category(name="C", slug="c-fact")
            brand = Brand(name="B", slug="b-fact")
            session.add_all([cat, brand])
            await session.flush()
            product = Product(
                name="P",
                sku="FACT-STATUS",
                slug="fact-status",
                category_id=cat.id,
                brand_id=brand.id,
                is_available=True,
                specifications={},
            )
            session.add(product)
            await _seed_property(session, definition_id="def.st", key="st", data_type="string")
            await session.flush()
            from datetime import UTC, datetime

            fact = KnowledgeFact(
                entity_id=product.id,
                definition_id="def.st",
                value="x",
                status="rejected",
                source_id="s",
                recorded_at=datetime.now(UTC),
                recorder="test",
            )
            session.add(fact)
            with pytest.raises(IntegrityError):
                await session.commit()

    if not USE_POSTGRES_TESTS:
        # SQLite may not enforce CHECK the same way depending on pragma; still try
        try:
            _run(body())
        except IntegrityError:
            pass
    else:
        _run(body())


def test_facts_do_not_mutate_legacy_jsonb(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.json", key="json", data_type="string")
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-JSONB")
    product_id = product["id"]

    async def before():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product_id)
            return copy.deepcopy(p.specifications)

    specs_before = _run(before())
    created = client.post(
        f"/api/v1/knowledge/products/{product_id}/facts",
        json={"definition_id": "def.json", "value": "x", "source_id": "s"},
        headers=admin_headers,
    )
    fact_id = created.json()["id"]
    client.put(
        f"/api/v1/knowledge/facts/{fact_id}",
        json={"value": "y"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/knowledge/facts/{fact_id}/deprecate",
        json={"change_reason": "done"},
        headers=admin_headers,
    )

    async def after():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product_id)
            return p.specifications

    assert _run(after()) == specs_before


def test_public_helper_excludes_non_published():
    from app.services.knowledge_fact_service import is_public_fact_status

    assert is_public_fact_status("published") is True
    assert is_public_fact_status("asserted") is False
    assert is_public_fact_status("disputed") is False
    assert is_public_fact_status("deprecated") is False
    assert is_public_fact_status("rejected") is False


def test_revision_rows_not_updated_by_service(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.rev", key="rev", data_type="string")
            await session.commit()

    _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="FACT-REV")
    created = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.rev", "value": "one", "source_id": "s"},
        headers=admin_headers,
    ).json()
    client.put(
        f"/api/v1/knowledge/facts/{created['id']}",
        json={"value": "two"},
        headers=admin_headers,
    )

    async def check():
        async with TestingSessionLocal() as session:
            rows = (
                await session.execute(
                    select(KnowledgeFactRevision)
                    .where(KnowledgeFactRevision.fact_id == created["id"])
                    .order_by(KnowledgeFactRevision.revision_number)
                )
            ).scalars().all()
            assert len(rows) == 2
            assert rows[0].value == "one"
            assert rows[1].value == "two"
            # count never decreases
            total = (
                await session.execute(select(func.count()).select_from(KnowledgeFactRevision))
            ).scalar_one()
            assert total >= 2

    _run(check())
