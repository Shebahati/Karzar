"""PT-W3A — minimal Product Type stewardship + manual assignment."""

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
from app.db.models.platform import AdminAuditLog, ProductChangeLog
from app.db.models.product_type import (
    ProductType,
    ProductTypeStatus,
)
from app.db.models.user import User
from app.main import app
from app.services import product_type_service as pts
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql

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


async def _seed_unit(session, *, dimension="length", code="mm"):
    unit = KnowledgeUnit(
        dimension=dimension,
        canonical_code=code,
        aliases=["میلی‌متر", "mm"],
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
        version="1.0.0",
        status="active",
        comparable=False,
        filterable=False,
        customer_facing=False,
    )
    session.add(prop)
    await session.flush()
    return prop


def _create_product(admin_headers, valid_product_data, sku="PTW3A-1"):
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


async def _db_specs(product_id: int) -> dict:
    async with TestingSessionLocal() as session:
        p = await session.get(Product, product_id)
        return copy.deepcopy(p.specifications)


def _create_draft_type(admin_headers, *, code="GEN_CAL", slug="gen-cal", name_fa="کولیس"):
    resp = client.post(
        "/api/v1/knowledge/product-types",
        json={"code": code, "slug": slug, "name_fa": name_fa, "name_en": "Caliper"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _activate_definition_path(admin_headers, product_type_id: int, property_id: str, **membership_kw):
    created = client.post(
        f"/api/v1/knowledge/product-types/{product_type_id}/definitions",
        json={},
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    defn = created.json()
    body = {
        "property_definition_id": property_id,
        "requiredness": membership_kw.get("requiredness", "optional"),
        "validation_overrides": membership_kw.get("validation_overrides") or {},
    }
    if "evidence_requirement_override" in membership_kw:
        body["evidence_requirement_override"] = membership_kw[
            "evidence_requirement_override"
        ]
    if "applicability_condition" in membership_kw:
        body["applicability_condition"] = membership_kw["applicability_condition"]
    mem = client.post(
        f"/api/v1/knowledge/product-type-definitions/{defn['id']}/memberships",
        json=body,
        headers=admin_headers,
    )
    assert mem.status_code == 201, mem.text
    act = client.post(
        f"/api/v1/knowledge/product-type-definitions/{defn['id']}/activate",
        json={"change_reason": "activate definition for PT-W3A"},
        headers=admin_headers,
    )
    assert act.status_code == 200, act.text
    return act.json()


# --- Auth ---


def test_product_type_routes_anonymous_401():
    assert client.post("/api/v1/knowledge/product-types", json={}).status_code == 401
    assert client.get("/api/v1/knowledge/product-types").status_code == 401
    assert client.get("/api/v1/knowledge/product-types/1").status_code == 401
    assert client.patch("/api/v1/knowledge/product-types/1", json={}).status_code == 401
    assert (
        client.post(
            "/api/v1/knowledge/product-types/1/activate",
            json={"change_reason": "x"},
        ).status_code
        == 401
    )
    assert (
        client.get("/api/v1/knowledge/products/1/product-type-assignment").status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/knowledge/products/1/product-type-assignment",
            json={"product_type_id": 1, "change_reason": "x"},
        ).status_code
        == 401
    )


def test_product_type_routes_non_admin_403(admin_headers):
    app.dependency_overrides.pop(get_current_super_admin, None)
    customer = customer_auth_headers("09126660011")
    assert (
        client.get("/api/v1/knowledge/product-types", headers=customer).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/knowledge/products/1/product-type-assignment",
            json={"product_type_id": 1, "change_reason": "x"},
            headers=customer,
        ).status_code
        == 403
    )


# --- Stewardship ---


def test_create_product_type_starts_draft(admin_headers):
    pt = _create_draft_type(admin_headers, code="DRAFT_A", slug="draft-a")
    assert pt["status"] == "draft"
    assert pt["code"] == "DRAFT_A"
    listed = client.get("/api/v1/knowledge/product-types", headers=admin_headers)
    assert listed.status_code == 200
    assert any(i["id"] == pt["id"] for i in listed.json()["items"])


def test_duplicate_code_rejected(admin_headers):
    _create_draft_type(admin_headers, code="DUP_C", slug="dup-c-1")
    resp = client.post(
        "/api/v1/knowledge/product-types",
        json={"code": "DUP_C", "slug": "dup-c-2", "name_fa": "ب"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_duplicate_slug_rejected(admin_headers):
    _create_draft_type(admin_headers, code="DUP_S1", slug="same-slug")
    resp = client.post(
        "/api/v1/knowledge/product-types",
        json={"code": "DUP_S2", "slug": "same-slug", "name_fa": "ب"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_code_immutable_and_draft_metadata_editable(admin_headers):
    pt = _create_draft_type(admin_headers, code="IMM_CODE", slug="imm-slug")
    # status not in schema → ignored; row stays draft
    status_patch = client.patch(
        f"/api/v1/knowledge/product-types/{pt['id']}",
        json={"status": "active"},
        headers=admin_headers,
    )
    assert status_patch.status_code == 200
    assert status_patch.json()["status"] == "draft"
    assert status_patch.json()["code"] == "IMM_CODE"

    ok = client.patch(
        f"/api/v1/knowledge/product-types/{pt['id']}",
        json={"slug": "imm-slug-2", "name_fa": "نام جدید", "name_en": "New"},
        headers=admin_headers,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["slug"] == "imm-slug-2"
    assert ok.json()["name_fa"] == "نام جدید"
    assert ok.json()["code"] == "IMM_CODE"

    # Service-level: code in patch is rejected
    async def try_code():
        async with TestingSessionLocal() as session:
            actor = (
                await session.execute(
                    select(User).where(User.phone_number == "09120000001")
                )
            ).scalar_one()
            try:
                await pts.update_draft_product_type(
                    session,
                    product_type_id=pt["id"],
                    patch={"code": "OTHER"},
                    actor=actor,
                )
            except Exception as exc:
                assert getattr(exc, "status_code", None) == 422
                return
            raise AssertionError("expected code mutation rejection")

    _run(try_code())


def test_activation_without_active_definition_rejected(admin_headers):
    pt = _create_draft_type(admin_headers, code="NO_DEF", slug="no-def")
    resp = client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "try"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_activation_requires_change_reason(admin_headers):
    pt = _create_draft_type(admin_headers, code="NEED_R", slug="need-r")
    resp = client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "   "},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_activation_with_active_definition_succeeds(admin_headers):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.act", key="act")
            await session.commit()

    _run(seed())
    pt = _create_draft_type(admin_headers, code="ACT_OK", slug="act-ok")
    _activate_definition_path(admin_headers, pt["id"], "def.act")
    resp = client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "ready for pilot"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "active"

    # active metadata mutation blocked
    blocked = client.patch(
        f"/api/v1/knowledge/product-types/{pt['id']}",
        json={"name_fa": "تغییر"},
        headers=admin_headers,
    )
    assert blocked.status_code == 409


# --- Assignment ---


def test_assignment_success_updates_and_audits(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.assign", key="assign")
            await session.commit()

    _run(seed())
    pt = _create_draft_type(admin_headers, code="ASG", slug="asg")
    defn = _activate_definition_path(admin_headers, pt["id"], "def.assign")
    act = client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "activate"},
        headers=admin_headers,
    )
    assert act.status_code == 200
    product = _create_product(admin_headers, valid_product_data, sku="ASG-P1")
    specs_before = _run(_db_specs(product["id"]))

    assign = client.post(
        f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
        json={"product_type_id": pt["id"], "change_reason": "manual reviewed"},
        headers=admin_headers,
    )
    assert assign.status_code == 200, assign.text
    body = assign.json()
    assert body["current_product_type_id"] == pt["id"]
    assert body["product_type"]["code"] == "ASG"
    assert body["active_definition_id"] == defn["id"]

    got = client.get(
        f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
        headers=admin_headers,
    )
    assert got.status_code == 200
    assert got.json()["current_product_type_id"] == pt["id"]

    async def verify():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            assert p.product_type_id == pt["id"]
            assert p.specifications == specs_before
            changes = (
                await session.execute(
                    select(ProductChangeLog).where(
                        ProductChangeLog.product_id == product["id"],
                        ProductChangeLog.field_name == "product_type_id",
                    )
                )
            ).scalars().all()
            assert len(changes) == 1
            assert changes[0].old_value is None
            assert changes[0].new_value == str(pt["id"])
            assert changes[0].reason == "manual reviewed"
            audits = (
                await session.execute(
                    select(AdminAuditLog).where(
                        AdminAuditLog.action == "product_type.assign",
                        AdminAuditLog.entity_id == str(product["id"]),
                    )
                )
            ).scalars().all()
            assert len(audits) == 1

    _run(verify())

    # idempotent same-type: no new audit
    again = client.post(
        f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
        json={"product_type_id": pt["id"], "change_reason": "again"},
        headers=admin_headers,
    )
    assert again.status_code == 200

    async def verify_noop():
        async with TestingSessionLocal() as session:
            count = (
                await session.execute(
                    select(func.count()).select_from(ProductChangeLog).where(
                        ProductChangeLog.product_id == product["id"],
                        ProductChangeLog.field_name == "product_type_id",
                    )
                )
            ).scalar_one()
            assert count == 1

    _run(verify_noop())


def test_reject_draft_retired_missing_and_no_definition(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.badtgt", key="badtgt")
            draft = ProductType(
                code="DRAFT_T",
                slug="draft-t",
                name_fa="د",
                status=ProductTypeStatus.DRAFT.value,
            )
            retired = ProductType(
                code="RET_T",
                slug="ret-t",
                name_fa="ر",
                status=ProductTypeStatus.RETIRED.value,
            )
            active_no_def = ProductType(
                code="ACT_ND",
                slug="act-nd",
                name_fa="ف",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add_all([draft, retired, active_no_def])
            await session.commit()
            return draft.id, retired.id, active_no_def.id

    draft_id, retired_id, active_nd_id = _run(seed())
    product = _create_product(admin_headers, valid_product_data, sku="BAD-TGT")

    for tid, expect in [
        (999999, 422),
        (draft_id, 422),
        (retired_id, 422),
        (active_nd_id, 422),
    ]:
        resp = client.post(
            f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
            json={"product_type_id": tid, "change_reason": "try"},
            headers=admin_headers,
        )
        assert resp.status_code == expect, (tid, resp.text)


def test_no_category_or_title_auto_assign(admin_headers, valid_product_data):
    """Same category / matching title must not write product_type_id."""
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(session, definition_id="def.heur", key="heur")
            await session.commit()

    _run(seed())
    pt = _create_draft_type(
        admin_headers, code="HEUR", slug="heur-caliper", name_fa="کولیس"
    )
    _activate_definition_path(admin_headers, pt["id"], "def.heur")
    client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "activate"},
        headers=admin_headers,
    )
    product = _create_product(
        admin_headers,
        {**valid_product_data, "name": "General-purpose Caliper HEUR"},
        sku="HEUR-P",
    )
    # create another product in same category — still unassigned
    other = _create_product(admin_headers, valid_product_data, sku="HEUR-P2")

    async def verify():
        async with TestingSessionLocal() as session:
            for pid in (product["id"], other["id"]):
                p = await session.get(Product, pid)
                assert p.product_type_id is None

    _run(verify())


# --- Fact compatibility ---


def test_compatible_asserted_fact_allows_assignment(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_unit(session)
            await _seed_property(
                session,
                definition_id="def.compat",
                key="compat",
                validation={"min": 0, "max": 100},
                unit_dimension="length",
                default_unit="mm",
            )
            await session.commit()

    _run(seed())
    pt = _create_draft_type(admin_headers, code="COMPAT", slug="compat")
    defn = _activate_definition_path(
        admin_headers,
        pt["id"],
        "def.compat",
        validation_overrides={"min": 10},
    )
    client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "activate"},
        headers=admin_headers,
    )
    product = _create_product(admin_headers, valid_product_data, sku="COMPAT-P")

    # asserted Fact while unassigned
    created = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={
            "definition_id": "def.compat",
            "value": 15,
            "unit": "mm",
            "source_id": "manual:compat",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text

    assign = client.post(
        f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
        json={"product_type_id": pt["id"], "change_reason": "ok"},
        headers=admin_headers,
    )
    assert assign.status_code == 200, assign.text
    assert assign.json()["active_definition_id"] == defn["id"]


def test_missing_membership_blocks_assignment(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(
                session, definition_id="def.miss", key="miss", data_type="string"
            )
            await _seed_property(
                session, definition_id="def.other", key="other", data_type="string"
            )
            await session.commit()

    _run(seed())
    pt = _create_draft_type(admin_headers, code="MISS", slug="miss")
    _activate_definition_path(admin_headers, pt["id"], "def.miss")
    client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "activate"},
        headers=admin_headers,
    )
    product = _create_product(admin_headers, valid_product_data, sku="MISS-P")
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/facts",
            json={
                "definition_id": "def.other",
                "value": "x",
                "source_id": "s",
            },
            headers=admin_headers,
        ).status_code
        == 201
    )
    resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
        json={"product_type_id": pt["id"], "change_reason": "no"},
        headers=admin_headers,
    )
    assert resp.status_code == 409
    async def verify():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            assert p.product_type_id is None

    _run(verify())


def test_forbidden_membership_blocks_assignment(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(
                session, definition_id="def.forb", key="forb", data_type="string"
            )
            await session.commit()

    _run(seed())
    pt = _create_draft_type(admin_headers, code="FORB", slug="forb")
    _activate_definition_path(
        admin_headers, pt["id"], "def.forb", requiredness="forbidden"
    )
    client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "activate"},
        headers=admin_headers,
    )
    product = _create_product(admin_headers, valid_product_data, sku="FORB-P")
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/facts",
            json={"definition_id": "def.forb", "value": "x", "source_id": "s"},
            headers=admin_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
            json={"product_type_id": pt["id"], "change_reason": "no"},
            headers=admin_headers,
        ).status_code
        == 409
    )


def test_narrowing_violation_blocks_assignment(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(
                session,
                definition_id="def.narr",
                key="narr",
                data_type="number",
                validation={"min": 0, "max": 100},
            )
            await session.commit()

    _run(seed())
    pt = _create_draft_type(admin_headers, code="NARR", slug="narr")
    _activate_definition_path(
        admin_headers,
        pt["id"],
        "def.narr",
        validation_overrides={"min": 10},
    )
    client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "activate"},
        headers=admin_headers,
    )
    product = _create_product(admin_headers, valid_product_data, sku="NARR-P")
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/facts",
            json={"definition_id": "def.narr", "value": 5, "source_id": "s"},
            headers=admin_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
            json={"product_type_id": pt["id"], "change_reason": "no"},
            headers=admin_headers,
        ).status_code
        == 409
    )


def test_deprecated_incompatible_fact_does_not_block(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_property(
                session, definition_id="def.depok", key="depok", data_type="string"
            )
            await _seed_property(
                session, definition_id="def.depbad", key="depbad", data_type="string"
            )
            await session.commit()

    _run(seed())
    pt = _create_draft_type(admin_headers, code="DEPOK", slug="depok")
    _activate_definition_path(admin_headers, pt["id"], "def.depok")
    client.post(
        f"/api/v1/knowledge/product-types/{pt['id']}/activate",
        json={"change_reason": "activate"},
        headers=admin_headers,
    )
    product = _create_product(admin_headers, valid_product_data, sku="DEPOK-P")
    fact_resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={"definition_id": "def.depbad", "value": "x", "source_id": "s"},
        headers=admin_headers,
    )
    assert fact_resp.status_code == 201, fact_resp.text
    fact = fact_resp.json()
    dep = client.post(
        f"/api/v1/knowledge/facts/{fact['id']}/deprecate",
        json={"change_reason": "obsolete"},
        headers=admin_headers,
    )
    assert dep.status_code == 200, dep.text
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
            json={"product_type_id": pt["id"], "change_reason": "ok"},
            headers=admin_headers,
        ).status_code
        == 200
    )


# --- Published Fact safety ---


def test_published_fact_blocks_reassign_and_clear(admin_headers, valid_product_data):
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_unit(session)
            await _seed_property(
                session,
                definition_id="def.pubsafe",
                key="pubsafe",
                validation={"min": 0},
                unit_dimension="length",
                default_unit="mm",
            )
            await _seed_property(
                session,
                definition_id="def.pubsafe2",
                key="pubsafe2",
                validation={"min": 0},
                unit_dimension="length",
                default_unit="mm",
            )
            await session.commit()

    _run(seed())
    pt_a = _create_draft_type(admin_headers, code="PUB_A", slug="pub-a")
    _activate_definition_path(admin_headers, pt_a["id"], "def.pubsafe")
    client.post(
        f"/api/v1/knowledge/product-types/{pt_a['id']}/activate",
        json={"change_reason": "a"},
        headers=admin_headers,
    )
    pt_b = _create_draft_type(admin_headers, code="PUB_B", slug="pub-b")
    _activate_definition_path(admin_headers, pt_b["id"], "def.pubsafe2")
    client.post(
        f"/api/v1/knowledge/product-types/{pt_b['id']}/activate",
        json={"change_reason": "b"},
        headers=admin_headers,
    )
    product = _create_product(admin_headers, valid_product_data, sku="PUBSAFE-P")
    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
            json={"product_type_id": pt_a["id"], "change_reason": "assign A"},
            headers=admin_headers,
        ).status_code
        == 200
    )
    fact = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={
            "definition_id": "def.pubsafe",
            "value": 1,
            "unit": "mm",
            "source_id": "s",
        },
        headers=admin_headers,
    ).json()
    assert (
        client.post(
            f"/api/v1/knowledge/facts/{fact['id']}/publish",
            json={"change_reason": "publish"},
            headers=admin_headers,
        ).status_code
        == 200
    )

    async def snapshot():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            f = await session.get(KnowledgeFact, fact["id"])
            rev_count = (
                await session.execute(
                    select(func.count()).select_from(KnowledgeFactRevision).where(
                        KnowledgeFactRevision.fact_id == fact["id"]
                    )
                )
            ).scalar_one()
            change_count = (
                await session.execute(
                    select(func.count()).select_from(ProductChangeLog).where(
                        ProductChangeLog.product_id == product["id"],
                        ProductChangeLog.field_name == "product_type_id",
                    )
                )
            ).scalar_one()
            return p.product_type_id, f.status, f.value, rev_count, change_count

    before = _run(snapshot())

    reassign = client.post(
        f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
        json={"product_type_id": pt_b["id"], "change_reason": "to B"},
        headers=admin_headers,
    )
    assert reassign.status_code == 409
    clear = client.post(
        f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
        json={"product_type_id": None, "change_reason": "clear"},
        headers=admin_headers,
    )
    assert clear.status_code == 409
    assert _run(snapshot()) == before


# --- Concurrency / FOR UPDATE ---


def test_assignment_emits_for_update_sql():
    stmt = select(Product).where(Product.id == 1).with_for_update()
    sql = str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )
    assert "FOR UPDATE" in sql.upper()


# --- Critical E2E ---


def test_e2e_type_definition_assign_assert_publish(admin_headers, valid_product_data):
    """PT-W1 → 11A → PT-W2 → Prompt 12 → PT-W3A structured-spec path."""
    async def seed():
        async with TestingSessionLocal() as session:
            await _seed_unit(session)
            await _seed_property(
                session,
                definition_id="def.e2e",
                key="resolution",
                data_type="number",
                validation={"min": 0, "max": 10},
                unit_dimension="length",
                default_unit="mm",
            )
            await session.commit()

    _run(seed())

    pt = _create_draft_type(admin_headers, code="E2E_CAL", slug="e2e-cal")
    defn = _activate_definition_path(
        admin_headers,
        pt["id"],
        "def.e2e",
        evidence_requirement_override="not_required",
    )
    assert (
        client.post(
            f"/api/v1/knowledge/product-types/{pt['id']}/activate",
            json={"change_reason": "e2e activate type"},
            headers=admin_headers,
        ).status_code
        == 200
    )

    product = _create_product(admin_headers, valid_product_data, sku="E2E-PTW3A")
    specs_before = _run(_db_specs(product["id"]))

    assert (
        client.post(
            f"/api/v1/knowledge/products/{product['id']}/product-type-assignment",
            json={"product_type_id": pt["id"], "change_reason": "e2e assign"},
            headers=admin_headers,
        ).status_code
        == 200
    )

    fact_resp = client.post(
        f"/api/v1/knowledge/products/{product['id']}/facts",
        json={
            "definition_id": "def.e2e",
            "value": 0.01,
            "unit": "mm",
            "source_id": "manual:e2e",
        },
        headers=admin_headers,
    )
    assert fact_resp.status_code == 201, fact_resp.text
    fact_id = fact_resp.json()["id"]

    pub = client.post(
        f"/api/v1/knowledge/facts/{fact_id}/publish",
        json={"change_reason": "e2e publish"},
        headers=admin_headers,
    )
    assert pub.status_code == 200, pub.text
    published = pub.json()
    assert published["status"] == "published"
    assert published["product_type_definition_id"] == defn["id"]

    async def verify_jsonb():
        async with TestingSessionLocal() as session:
            p = await session.get(Product, product["id"])
            assert p.specifications == specs_before
            assert p.product_type_id == pt["id"]

    _run(verify_jsonb())
