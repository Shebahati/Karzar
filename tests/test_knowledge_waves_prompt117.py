"""Prompt 117 — Wave execute failure harden + inactive KB eligibility + interrupted resume."""

from __future__ import annotations

import asyncio
import copy
from datetime import UTC, datetime
from typing import Any

import pytest
from app.api.deps import get_current_super_admin
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
from app.db.models.knowledge_wave import (
    KnowledgeWave,
    KnowledgeWaveRun,
    KnowledgeWaveRunItem,
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
    REQUIRED_ALEMBIC,
    REQUIRED_ARTIFACT_CHECKSUM,
)
from app.services.knowledge_wave_execute_service import (
    ITEM_PENDING,
    ITEM_SUCCESS,
    RUN_RUNNING,
    RUN_TYPE_ASSERT,
    WAVE_STATUS_EXECUTING,
)
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
            "VALUES (1, :plane, 'test', 'prompt117')"
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


async def _seed():
    async with TestingSessionLocal() as session:
        await _seed_gen_caliper_stack(session)
        await session.commit()


def _create_product(admin_headers, valid_product_data, sku: str, **overrides):
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
        **overrides,
    }
    resp = client.post("/api/v1/products/", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _sku_unit(sku: str, product_id: int, *, omit_fact: str | None = None) -> dict[str, Any]:
    facts = [
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
    ]
    if omit_fact:
        facts = [f for f in facts if f["definition_id"] != omit_fact]
    return {
        "product_id": product_id,
        "sku": sku,
        "facts": facts,
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


def _seal_wave(
    admin_headers, *, wave_id: str, products: list[dict]
) -> dict:
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": wave_id,
            "brand": "INSIZE",
            "product_type_id": 1,
            "definition_id": 1,
            "policy_json": _policy_json(),
            "products": [
                {"product_id": p["id"], "sku_snapshot": p["sku"]} for p in products
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


def test_inactive_product_wave_execute_succeeds(admin_headers, valid_product_data):
    """Phase 5 — is_active=false must not block KB assert; commercial fields unchanged."""
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W117-INACTIVE")
    pid = product["id"]

    async def _snapshot_and_deactivate():
        async with TestingSessionLocal() as session:
            row = await session.get(Product, pid)
            assert row is not None
            snapshot = {
                "is_active": bool(row.is_active),
                "is_available": bool(row.is_available),
                "base_price": str(row.base_price),
                "specifications": copy.deepcopy(row.specifications),
            }
            row.is_active = False
            await session.commit()
            return snapshot

    before = _run(_snapshot_and_deactivate())
    assert before["is_active"] is True

    sealed = _seal_wave(admin_headers, wave_id="W117-INACTIVE-001", products=[product])
    executed = client.post(
        f"/api/v1/knowledge/waves/{sealed['wave_id']}/execute",
        json={
            "change_reason": "assert inactive SKU",
            "sku_units": [_sku_unit(product["sku"], pid)],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "completed"
    assert body["wave_status"] == "Asserted"
    assert body["progress"]["success"] == 1
    assert body["progress"]["failed"] == 0

    async def _verify():
        async with TestingSessionLocal() as session:
            row = await session.get(Product, pid)
            assert row is not None
            assert row.is_active is False
            assert bool(row.is_available) == before["is_available"]
            assert str(row.base_price) == before["base_price"]
            assert row.specifications == before["specifications"]
            facts = (
                await session.execute(
                    select(func.count())
                    .select_from(KnowledgeFact)
                    .where(KnowledgeFact.entity_id == pid)
                )
            ).scalar_one()
            assert facts == 3

    _run(_verify())


def test_deleted_product_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W117-DEL")
    pid = product["id"]

    async def _soft_delete():
        async with TestingSessionLocal() as session:
            row = await session.get(Product, pid)
            assert row is not None
            row.deleted_at = datetime.now(UTC)
            await session.commit()

    _run(_soft_delete())
    sealed = _seal_wave(admin_headers, wave_id="W117-DEL-001", products=[product])
    executed = client.post(
        f"/api/v1/knowledge/waves/{sealed['wave_id']}/execute",
        json={
            "change_reason": "deleted should fail",
            "sku_units": [_sku_unit(product["sku"], pid)],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "failed"
    assert body["wave_status"] == "Failed"
    assert body["progress"]["failed"] == 1


def test_wrong_product_type_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W117-WRONGPT")
    pid = product["id"]

    async def _assign_wrong_pt():
        async with TestingSessionLocal() as session:
            other = ProductType(
                id=99,
                code="OTHER_TYPE",
                slug="other-type",
                name_fa="دیگر",
                name_en="Other",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add(other)
            await session.flush()
            row = await session.get(Product, pid)
            assert row is not None
            row.product_type_id = 99
            await session.commit()

    _run(_assign_wrong_pt())
    sealed = _seal_wave(admin_headers, wave_id="W117-WRONGPT-001", products=[product])
    executed = client.post(
        f"/api/v1/knowledge/waves/{sealed['wave_id']}/execute",
        json={
            "change_reason": "wrong PT should fail",
            "sku_units": [_sku_unit(product["sku"], pid)],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "failed"
    assert body["wave_status"] == "Failed"


def test_sku_snapshot_mismatch_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W117-SKUOK")
    sealed = _seal_wave(admin_headers, wave_id="W117-SKU-001", products=[product])

    # Drift product.sku after seal while unit still matches allowlist snapshot
    async def _drift_sku():
        async with TestingSessionLocal() as session:
            row = await session.get(Product, product["id"])
            assert row is not None
            row.sku = "W117-DRIFTED"
            await session.commit()

    _run(_drift_sku())
    executed = client.post(
        f"/api/v1/knowledge/waves/{sealed['wave_id']}/execute",
        json={
            "change_reason": "sku mismatch",
            "sku_units": [_sku_unit("W117-SKUOK", product["id"])],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "failed"
    assert body["wave_status"] == "Failed"
    assert body["progress"]["failed"] == 1
    assert "SKU" in (body.get("stop_reason") or "") or "sku" in (
        body.get("stop_reason") or ""
    ).lower()


def test_genuine_invalid_assertion_finalizes_failed(admin_headers, valid_product_data):
    """Phase 9 — real assert error → item/run/Wave Failed; no stranded Executing/running."""
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W117-MISSFACT")
    sealed = _seal_wave(admin_headers, wave_id="W117-MISS-001", products=[product])
    unit = _sku_unit(product["sku"], product["id"], omit_fact="def.accuracy")
    executed = client.post(
        f"/api/v1/knowledge/waves/{sealed['wave_id']}/execute",
        json={"change_reason": "missing required fact", "sku_units": [unit]},
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "failed"
    assert body["wave_status"] == "Failed"
    assert body["progress"]["failed"] == 1
    assert body["progress"]["pending"] == 0
    run_id = body["wave_run_id"]

    ledger = client.get(
        f"/api/v1/knowledge/wave-runs/{run_id}",
        headers=admin_headers,
    )
    assert ledger.status_code == 200, ledger.text
    led = ledger.json()
    assert led["status"] == "failed"
    assert led["wave"]["status"] == "Failed"
    assert led["progress"]["running"] == 0


def test_failure_after_rollback_does_not_strand(
    admin_headers, valid_product_data, monkeypatch
):
    """Regression: assert exception + rollback must still finalize Failed (no MissingGreenlet)."""
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W117-GREENLET")
    sealed = _seal_wave(admin_headers, wave_id="W117-GREENLET-001", products=[product])

    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated assert crash")

    monkeypatch.setattr(batch_service, "execute_kb_batch_assert", _boom)
    executed = client.post(
        f"/api/v1/knowledge/waves/{sealed['wave_id']}/execute",
        json={
            "change_reason": "greenlet regression",
            "sku_units": [_sku_unit(product["sku"], product["id"])],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "failed"
    assert body["wave_status"] == "Failed"
    assert "MissingGreenlet" not in (body.get("stop_reason") or "")


def test_interrupted_partial_run_resume_idempotent(admin_headers, valid_product_data):
    """Phase 8 — Executing+running with 2/14 success → governed resume → Asserted, no dupes."""
    _run(_seed())
    products = [
        _create_product(admin_headers, valid_product_data, f"W117-P{i:02d}")
        for i in range(14)
    ]
    sealed = _seal_wave(admin_headers, wave_id="W117-PARTIAL-001", products=products)
    sku_units = [_sku_unit(p["sku"], p["id"]) for p in products]
    wave_id = sealed["wave_id"]
    manifest = sealed["manifest_sha256"]

    # Seed interrupted incident state: Wave Executing, run running, 2 success + facts
    async def _seed_interrupted():
        async with TestingSessionLocal() as session:
            wave = (
                await session.execute(
                    select(KnowledgeWave).where(KnowledgeWave.wave_id == wave_id)
                )
            ).scalar_one()
            wave.status = WAVE_STATUS_EXECUTING
            run = KnowledgeWaveRun(
                wave_id=wave.id,
                run_type=RUN_TYPE_ASSERT,
                status=RUN_RUNNING,
                created_by=1,
                manifest_sha256_snapshot=manifest,
                request_snapshot_json={
                    "sku_units": sku_units,
                    "change_reason": "partial seed",
                },
                started_at=datetime.now(UTC),
            )
            session.add(run)
            await session.flush()
            for p in products:
                session.add(
                    KnowledgeWaveRunItem(
                        run_id=run.id,
                        product_id=p["id"],
                        sku_snapshot=p["sku"],
                        status=ITEM_PENDING,
                        resumed=False,
                    )
                )
            await session.flush()
            await session.commit()
            return run.id, wave.id

    run_id, wave_pk = _run(_seed_interrupted())

    # Assert first two products (6 facts + 6 links) as prior successes
    from app.db.models.user import User
    from app.services import knowledge_batch_assert_service as bas
    from app.services.knowledge_wave_execute_service import resolve_wave_policy
    from sqlalchemy.orm import selectinload

    async def _assert_first_two():
        async with TestingSessionLocal() as session:
            actor = (
                await session.execute(select(User).order_by(User.id).limit(1))
            ).scalar_one()
            wave = (
                await session.execute(
                    select(KnowledgeWave)
                    .options(selectinload(KnowledgeWave.products))
                    .where(KnowledgeWave.id == wave_pk)
                )
            ).scalar_one()
            real_policy = resolve_wave_policy(wave)
            for p in products[:2]:
                unit = _sku_unit(p["sku"], p["id"])
                await bas.execute_kb_batch_assert(
                    session,
                    product_id=p["id"],
                    manifest_sha256=manifest,
                    sku=p["sku"],
                    product_type_id=1,
                    definition_id=1,
                    facts=unit["facts"],
                    evidence_links=unit["evidence_links"],
                    change_reason="seed success",
                    actor=actor,
                    wave_context=real_policy,
                )
            run = (
                await session.execute(
                    select(KnowledgeWaveRun)
                    .options(selectinload(KnowledgeWaveRun.items))
                    .where(KnowledgeWaveRun.id == run_id)
                )
            ).scalar_one()
            success_ids = {products[0]["id"], products[1]["id"]}
            for item in list(run.items):
                if item.product_id in success_ids:
                    item.status = ITEM_SUCCESS
                    item.finished_at = datetime.now(UTC)
                    item.result_json = {"seeded": True}
            await session.commit()

            facts = (
                await session.execute(select(func.count()).select_from(KnowledgeFact))
            ).scalar_one()
            revs = (
                await session.execute(
                    select(func.count()).select_from(KnowledgeFactRevision)
                )
            ).scalar_one()
            links = (
                await session.execute(
                    select(func.count()).select_from(KnowledgeEvidenceLink)
                )
            ).scalar_one()
            return int(facts), int(revs), int(links)

    facts_before, revs_before, links_before = _run(_assert_first_two())
    assert facts_before == 6
    assert revs_before == 6
    assert links_before == 6

    resumed = client.post(
        f"/api/v1/knowledge/wave-runs/{run_id}/resume",
        json={"change_reason": "governed interrupted resume"},
        headers=admin_headers,
    )
    assert resumed.status_code == 201, resumed.text
    body = resumed.json()
    assert body["wave_run_id"] == run_id  # same run continued
    assert body["status"] == "completed"
    assert body["wave_status"] == "Asserted"
    assert body["progress"]["success"] + body["progress"]["skipped"] == 14
    assert body["progress"]["failed"] == 0
    assert body["progress"]["pending"] == 0
    assert body["progress"]["running"] == 0

    async def _end():
        async with TestingSessionLocal() as session:
            facts = (
                await session.execute(select(func.count()).select_from(KnowledgeFact))
            ).scalar_one()
            revs = (
                await session.execute(
                    select(func.count()).select_from(KnowledgeFactRevision)
                )
            ).scalar_one()
            links = (
                await session.execute(
                    select(func.count()).select_from(KnowledgeEvidenceLink)
                )
            ).scalar_one()
            run = await session.get(KnowledgeWaveRun, run_id)
            wave = (
                await session.execute(
                    select(KnowledgeWave).where(KnowledgeWave.wave_id == wave_id)
                )
            ).scalar_one()
            running = (
                await session.execute(
                    select(func.count())
                    .select_from(KnowledgeWaveRun)
                    .where(KnowledgeWaveRun.status == RUN_RUNNING)
                )
            ).scalar_one()
            return (
                int(facts),
                int(revs),
                int(links),
                run.status if run else None,
                wave.status,
                int(running),
            )

    facts_after, revs_after, links_after, run_status, wave_status, running = _run(
        _end()
    )
    assert facts_after == 42
    assert revs_after == 42
    assert links_after == 42
    assert facts_after - facts_before == 36
    assert revs_after - revs_before == 36
    assert links_after - links_before == 36
    assert run_status == "completed"
    assert wave_status == "Asserted"
    assert running == 0
