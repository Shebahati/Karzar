"""Prompt 138 — Definition-driven Wave Fact contract (non-triad lifecycle)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models.knowledge import (
    KnowledgeEvidenceArtifact,
    KnowledgeFact,
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
from app.services.knowledge_batch_assert_service import (
    REQUIRED_ALEMBIC,
    REQUIRED_ARTIFACT_CHECKSUM,
)
from app.services.knowledge_wave_fact_contract import resolve_definition_fact_contract
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from tests.conftest import TestingSessionLocal, override_super_admin
from tests.test_knowledge_waves_prompt68 import _create_product, _policy_json

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
            "VALUES (1, 'live', 'test', 'prompt138')"
        )
    )
    await session.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
        {"v": REQUIRED_ALEMBIC},
    )


async def _seed_string_prop(session, *, definition_id: str, key: str):
    session.add(
        KnowledgePropertyDefinition(
            definition_id=definition_id,
            key=key,
            data_type="string",
            label_en=key,
            label_fa=key,
            validation={"type": "string", "min_length": 1, "max_length": 64},
            version="1.0.0",
            status="active",
            unit_dimension=None,
            default_unit=None,
            comparable=False,
            filterable=False,
            customer_facing=False,
        )
    )


async def _seed_thread_gauge_two_fact() -> dict[str, int]:
    """PT with exactly two required memberships (Wave038 class)."""
    async with TestingSessionLocal() as session:
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
        await _seed_string_prop(session, definition_id="def.nominal_size", key="nominal_size")
        await _seed_string_prop(session, definition_id="def.grade", key="grade")
        await session.flush()

        pt = ProductType(
            id=90,
            code="THREAD_PLUG_GAUGE_P138",
            slug="thread-plug-gauge-p138",
            name_fa="گیج پیچ",
            name_en="Thread Plug Gauge P138",
            status=ProductTypeStatus.ACTIVE.value,
        )
        session.add(pt)
        await session.flush()
        definition = ProductTypeDefinition(
            id=90,
            product_type_id=90,
            version=1,
            status=ProductTypeDefinitionStatus.ACTIVE.value,
        )
        session.add(definition)
        await session.flush()
        # Deliberate non-alphabetic display_order: grade before nominal_size
        session.add(
            ProductTypeAttributeMembership(
                product_type_definition_id=90,
                property_definition_id="def.grade",
                requiredness="required",
                applicability_condition={},
                validation_overrides={},
                evidence_requirement_override="required",
                display_order=5,
            )
        )
        session.add(
            ProductTypeAttributeMembership(
                product_type_definition_id=90,
                property_definition_id="def.nominal_size",
                requiredness="required",
                applicability_condition={},
                validation_overrides={},
                evidence_requirement_override="required",
                display_order=40,
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
        await session.commit()
        return {"product_type_id": 90, "definition_id": 90}


async def _seed_four_fact_pt() -> dict[str, int]:
    async with TestingSessionLocal() as session:
        await _ensure_gates(session)
        for definition_id, key in (
            ("def.p138_a", "p138_a"),
            ("def.p138_b", "p138_b"),
            ("def.p138_c", "p138_c"),
            ("def.p138_d", "p138_d"),
        ):
            await _seed_string_prop(session, definition_id=definition_id, key=key)
        await session.flush()
        session.add(
            ProductType(
                id=91,
                code="P138_FOUR_FACT",
                slug="p138-four-fact",
                name_fa="چهار فکت",
                name_en="Four Fact PT",
                status=ProductTypeStatus.ACTIVE.value,
            )
        )
        await session.flush()
        session.add(
            ProductTypeDefinition(
                id=91,
                product_type_id=91,
                version=1,
                status=ProductTypeDefinitionStatus.ACTIVE.value,
            )
        )
        await session.flush()
        for prop_id, order in (
            ("def.p138_a", 10),
            ("def.p138_b", 20),
            ("def.p138_c", 30),
            ("def.p138_d", 40),
        ):
            session.add(
                ProductTypeAttributeMembership(
                    product_type_definition_id=91,
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
        await session.commit()
        return {"product_type_id": 91, "definition_id": 91}


async def _seed_optional_membership_pt() -> dict[str, int]:
    async with TestingSessionLocal() as session:
        await _ensure_gates(session)
        for definition_id, key in (
            ("def.p138_r1", "p138_r1"),
            ("def.p138_r2", "p138_r2"),
            ("def.p138_r3", "p138_r3"),
            ("def.p138_opt", "p138_opt"),
        ):
            await _seed_string_prop(session, definition_id=definition_id, key=key)
        await session.flush()
        session.add(
            ProductType(
                id=92,
                code="P138_OPTIONAL",
                slug="p138-optional",
                name_fa="اختیاری",
                name_en="Optional Membership PT",
                status=ProductTypeStatus.ACTIVE.value,
            )
        )
        await session.flush()
        session.add(
            ProductTypeDefinition(
                id=92,
                product_type_id=92,
                version=1,
                status=ProductTypeDefinitionStatus.ACTIVE.value,
            )
        )
        await session.flush()
        for prop_id, order, req in (
            ("def.p138_r1", 10, "required"),
            ("def.p138_r2", 20, "required"),
            ("def.p138_r3", 30, "required"),
            ("def.p138_opt", 40, "optional"),
        ):
            session.add(
                ProductTypeAttributeMembership(
                    product_type_definition_id=92,
                    property_definition_id=prop_id,
                    requiredness=req,
                    applicability_condition={},
                    validation_overrides={},
                    evidence_requirement_override="required" if req == "required" else None,
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
        await session.commit()
        return {"product_type_id": 92, "definition_id": 92}


def _string_sku_unit(
    sku: str,
    product_id: int,
    *,
    facts: list[tuple[str, str]],
) -> dict[str, Any]:
    fact_items = [
        {
            "definition_id": def_id,
            "value": value,
            "source_id": f"catalog:insize:p138:{sku}:{def_id}",
        }
        for def_id, value in facts
    ]
    links = [
        {
            "artifact_id": 1,
            "locator": {
                "pdf_page": 400,
                "printed_page": 392,
                "model": sku,
                "property": def_id.removeprefix("def."),
            },
        }
        for def_id, _ in facts
    ]
    return {
        "product_id": product_id,
        "sku": sku,
        "facts": fact_items,
        "evidence_links": links,
    }


def _seal_custom_wave(
    admin_headers,
    *,
    wave_id: str,
    product: dict,
    product_type_id: int,
    definition_id: int,
) -> dict:
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": wave_id,
            "brand": "INSIZE",
            "product_type_id": product_type_id,
            "definition_id": definition_id,
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


def test_contract_resolver_ordering_display_order(admin_headers):
    ids = _run(_seed_thread_gauge_two_fact())

    async def _resolve():
        async with TestingSessionLocal() as session:
            return await resolve_definition_fact_contract(
                session, ids["definition_id"], require_evidence=True
            )

    contract = _run(_resolve())
    assert contract.required_definition_ids == (
        "def.grade",
        "def.nominal_size",
    )
    assert contract.property_key_by_definition_id["def.grade"] == "grade"
    assert contract.required_count == 2


def test_wave038_two_fact_lifecycle_no_exactly_three_error(
    admin_headers, valid_product_data
):
    """Wave038 class: Definition with 2 required Facts must assert/EV/publish."""
    ids = _run(_seed_thread_gauge_two_fact())
    product = _create_product(admin_headers, valid_product_data, "P138-2F-01")
    _seal_custom_wave(
        admin_headers,
        wave_id="P138-2F-WAVE",
        product=product,
        product_type_id=ids["product_type_id"],
        definition_id=ids["definition_id"],
    )
    unit = _string_sku_unit(
        product["sku"],
        product["id"],
        facts=[
            ("def.grade", "6H"),
            ("def.nominal_size", "M8x1.25"),
        ],
    )
    # Payload order differs from membership order — normalizer must reorder.
    executed = client.post(
        "/api/v1/knowledge/waves/P138-2F-WAVE/execute",
        json={"change_reason": "P138 two-fact assert", "sku_units": [unit]},
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["wave_status"] == "Asserted"
    assert "Exactly 3 Facts are required" not in executed.text

    async def _fact_count():
        async with TestingSessionLocal() as session:
            facts = (
                await session.execute(
                    select(KnowledgeFact).where(
                        KnowledgeFact.entity_id == product["id"]
                    )
                )
            ).scalars().all()
            return sorted(f.definition_id for f in facts), len(facts)

    defs, n = _run(_fact_count())
    assert n == 2
    assert defs == ["def.grade", "def.nominal_size"]

    ev = client.post(
        "/api/v1/knowledge/waves/P138-2F-WAVE/validate-evidence",
        json={"change_reason": "P138 two-fact evidence"},
        headers=admin_headers,
    )
    assert ev.status_code == 200, ev.text
    assert ev.json()["stats"]["facts_checked"] == 2
    assert ev.json()["stats"]["evidence_links_checked"] == 2
    assert ev.json()["stats"]["property_definitions"] == [
        "def.grade",
        "def.nominal_size",
    ]

    pub = client.post(
        "/api/v1/knowledge/waves/P138-2F-WAVE/publish",
        json={"change_reason": "P138 two-fact publish"},
        headers=admin_headers,
    )
    assert pub.status_code == 200, pub.text
    assert pub.json()["new_status"] == "Published"
    assert pub.json()["total"] == 2
    assert pub.json()["published"] == 2


def test_two_fact_rejects_one_and_three(admin_headers, valid_product_data):
    ids = _run(_seed_thread_gauge_two_fact())
    product = _create_product(admin_headers, valid_product_data, "P138-2F-BAD")
    _seal_custom_wave(
        admin_headers,
        wave_id="P138-2F-BAD",
        product=product,
        product_type_id=ids["product_type_id"],
        definition_id=ids["definition_id"],
    )
    one = _string_sku_unit(
        product["sku"],
        product["id"],
        facts=[("def.grade", "6H")],
    )
    bad1 = client.post(
        "/api/v1/knowledge/waves/P138-2F-BAD/execute",
        json={"change_reason": "too few", "sku_units": [one]},
        headers=admin_headers,
    )
    assert bad1.status_code == 201, bad1.text
    assert bad1.json()["wave_status"] == "Failed"
    stop = str(bad1.json().get("stop_reason") or "")
    assert "Exactly 3 Facts are required" not in stop
    assert "Exactly 2 Facts are required" in stop or "missing" in stop.lower()

    # Fresh wave for unexpected third Fact
    product2 = _create_product(admin_headers, valid_product_data, "P138-2F-BAD3")
    _seal_custom_wave(
        admin_headers,
        wave_id="P138-2F-BAD3",
        product=product2,
        product_type_id=ids["product_type_id"],
        definition_id=ids["definition_id"],
    )
    three = _string_sku_unit(
        product2["sku"],
        product2["id"],
        facts=[
            ("def.grade", "6H"),
            ("def.nominal_size", "M8"),
        ],
    )
    three["facts"].append(
        {
            "definition_id": "def.grade",
            "value": "dup",
            "source_id": "dup",
        }
    )
    three["evidence_links"].append(
        {
            "artifact_id": 1,
            "locator": {
                "pdf_page": 1,
                "printed_page": 1,
                "model": product2["sku"],
                "property": "grade",
            },
        }
    )
    bad3 = client.post(
        "/api/v1/knowledge/waves/P138-2F-BAD3/execute",
        json={"change_reason": "too many", "sku_units": [three]},
        headers=admin_headers,
    )
    assert bad3.status_code == 201, bad3.text
    assert bad3.json()["wave_status"] == "Failed"


def test_four_fact_lifecycle(admin_headers, valid_product_data):
    ids = _run(_seed_four_fact_pt())
    product = _create_product(admin_headers, valid_product_data, "P138-4F-01")
    _seal_custom_wave(
        admin_headers,
        wave_id="P138-4F-WAVE",
        product=product,
        product_type_id=ids["product_type_id"],
        definition_id=ids["definition_id"],
    )
    unit = _string_sku_unit(
        product["sku"],
        product["id"],
        facts=[
            ("def.p138_a", "a"),
            ("def.p138_b", "b"),
            ("def.p138_c", "c"),
            ("def.p138_d", "d"),
        ],
    )
    executed = client.post(
        "/api/v1/knowledge/waves/P138-4F-WAVE/execute",
        json={"change_reason": "four-fact assert", "sku_units": [unit]},
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["wave_status"] == "Asserted"

    async def _n():
        async with TestingSessionLocal() as session:
            return (
                await session.execute(
                    select(KnowledgeFact).where(
                        KnowledgeFact.entity_id == product["id"]
                    )
                )
            ).scalars().all()

    facts = _run(_n())
    assert len(facts) == 4

    ev = client.post(
        "/api/v1/knowledge/waves/P138-4F-WAVE/validate-evidence",
        json={"change_reason": "four-fact evidence"},
        headers=admin_headers,
    )
    assert ev.status_code == 200, ev.text
    assert ev.json()["stats"]["facts_checked"] == 4
    assert ev.json()["stats"]["evidence_links_checked"] == 4

    pub = client.post(
        "/api/v1/knowledge/waves/P138-4F-WAVE/publish",
        json={"change_reason": "four-fact publish"},
        headers=admin_headers,
    )
    assert pub.status_code == 200, pub.text
    assert pub.json()["total"] == 4
    assert pub.json()["published"] == 4
    assert pub.json()["new_status"] == "Published"


def test_optional_membership_excluded_from_wave_payload(
    admin_headers, valid_product_data
):
    ids = _run(_seed_optional_membership_pt())
    product = _create_product(admin_headers, valid_product_data, "P138-OPT-01")
    _seal_custom_wave(
        admin_headers,
        wave_id="P138-OPT-WAVE",
        product=product,
        product_type_id=ids["product_type_id"],
        definition_id=ids["definition_id"],
    )
    ok_unit = _string_sku_unit(
        product["sku"],
        product["id"],
        facts=[
            ("def.p138_r1", "1"),
            ("def.p138_r2", "2"),
            ("def.p138_r3", "3"),
        ],
    )
    executed = client.post(
        "/api/v1/knowledge/waves/P138-OPT-WAVE/execute",
        json={"change_reason": "optional absent ok", "sku_units": [ok_unit]},
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["wave_status"] == "Asserted"

    product2 = _create_product(admin_headers, valid_product_data, "P138-OPT-02")
    _seal_custom_wave(
        admin_headers,
        wave_id="P138-OPT-WAVE2",
        product=product2,
        product_type_id=ids["product_type_id"],
        definition_id=ids["definition_id"],
    )
    with_opt = _string_sku_unit(
        product2["sku"],
        product2["id"],
        facts=[
            ("def.p138_r1", "1"),
            ("def.p138_r2", "2"),
            ("def.p138_r3", "3"),
            ("def.p138_opt", "x"),
        ],
    )
    bad = client.post(
        "/api/v1/knowledge/waves/P138-OPT-WAVE2/execute",
        json={"change_reason": "optional in payload rejected", "sku_units": [with_opt]},
        headers=admin_headers,
    )
    assert bad.status_code == 201, bad.text
    assert bad.json()["wave_status"] == "Failed"
    stop = str(bad.json().get("stop_reason") or "")
    assert "Unexpected" in stop or "Exactly 3 Facts are required" in stop


def test_wrong_locator_property_rejected(admin_headers, valid_product_data):
    ids = _run(_seed_thread_gauge_two_fact())
    product = _create_product(admin_headers, valid_product_data, "P138-LOC")
    _seal_custom_wave(
        admin_headers,
        wave_id="P138-LOC-WAVE",
        product=product,
        product_type_id=ids["product_type_id"],
        definition_id=ids["definition_id"],
    )
    unit = _string_sku_unit(
        product["sku"],
        product["id"],
        facts=[
            ("def.grade", "6H"),
            ("def.nominal_size", "M8"),
        ],
    )
    unit["evidence_links"][0]["locator"]["property"] = "measurement_range"
    executed = client.post(
        "/api/v1/knowledge/waves/P138-LOC-WAVE/execute",
        json={"change_reason": "bad locator property", "sku_units": [unit]},
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["wave_status"] == "Failed"
    stop = str(executed.json().get("stop_reason") or "")
    assert "locator.property" in stop or "Unsupported" in stop
