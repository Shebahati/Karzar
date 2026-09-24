"""Prompt 104 — PR3-B.2 Wave evidence validation (Asserted → EvidenceValidated)."""

from __future__ import annotations

import asyncio

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models.knowledge import KnowledgeEvidenceLink, KnowledgeFact
from app.db.models.knowledge_wave import KnowledgeWave
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import TestingSessionLocal, customer_auth_headers, override_super_admin
from tests.test_knowledge_waves_prompt68 import (
    _create_product,
    _seal_wave,
    _seed,
    _sku_unit,
)

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("override_database")


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def admin_headers(monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "true")
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    headers = {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}
    yield headers
    app.dependency_overrides.pop(get_current_super_admin, None)


def _assert_wave(admin_headers, *, wave_id: str, product: dict) -> dict:
    _seal_wave(admin_headers, wave_id=wave_id, product=product)
    executed = client.post(
        f"/api/v1/knowledge/waves/{wave_id}/execute",
        json={
            "change_reason": "assert for evidence validate",
            "sku_units": [_sku_unit(product["sku"], product["id"])],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["wave_status"] == "Asserted"
    return executed.json()


def test_asserted_to_evidence_validated_happy_path(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W104-OK")
    _assert_wave(admin_headers, wave_id="EV-OK-001", product=product)

    resp = client.post(
        "/api/v1/knowledge/waves/EV-OK-001/validate-evidence",
        json={"change_reason": "PROMPT 104 happy path"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["previous_status"] == "Asserted"
    assert body["new_status"] == "EvidenceValidated"
    assert body["wave"]["status"] == "EvidenceValidated"
    assert body["wave_id"] == "EV-OK-001"
    assert body["manifest_sha256"]
    assert body["stats"]["facts_checked"] == 3
    assert body["stats"]["evidence_links_checked"] == 3
    assert body["issues"] == []


def test_wrong_status_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W104-ST")
    sealed = _seal_wave(admin_headers, wave_id="EV-ST-001", product=product)
    assert sealed["status"] == "Sealed"

    resp = client.post(
        "/api/v1/knowledge/waves/EV-ST-001/validate-evidence",
        json={"change_reason": "too early"},
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text


def test_sha_mismatch_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W104-SHA")
    executed = _assert_wave(admin_headers, wave_id="EV-SHA-001", product=product)

    async def _corrupt():
        async with TestingSessionLocal() as session:
            wave = await session.get(KnowledgeWave, executed["wave_pk"])
            assert wave is not None
            wave.manifest_sha256 = "b" * 64
            await session.commit()

    _run(_corrupt())

    resp = client.post(
        "/api/v1/knowledge/waves/EV-SHA-001/validate-evidence",
        json={"change_reason": "sha drift"},
        headers=admin_headers,
    )
    assert resp.status_code == 422, resp.text
    assert "manifest" in resp.text.lower() or "sha" in resp.text.lower()

    async def _still_asserted():
        async with TestingSessionLocal() as session:
            wave = await session.get(KnowledgeWave, executed["wave_pk"])
            assert wave is not None
            return wave.status

    assert _run(_still_asserted()) == "Asserted"


def test_missing_evidence_link_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W104-EL")
    executed = _assert_wave(admin_headers, wave_id="EV-EL-001", product=product)

    async def _drop_links():
        async with TestingSessionLocal() as session:
            facts = (
                await session.execute(
                    select(KnowledgeFact).where(
                        KnowledgeFact.entity_id == product["id"]
                    )
                )
            ).scalars().all()
            for fact in facts:
                links = (
                    await session.execute(
                        select(KnowledgeEvidenceLink).where(
                            KnowledgeEvidenceLink.fact_id == fact.id
                        )
                    )
                ).scalars().all()
                for link in links:
                    await session.delete(link)
            await session.commit()

    _run(_drop_links())

    resp = client.post(
        "/api/v1/knowledge/waves/EV-EL-001/validate-evidence",
        json={"change_reason": "missing links"},
        headers=admin_headers,
    )
    assert resp.status_code == 422, resp.text
    assert "FACT_SUPPORTED_BY" in resp.text or "evidence" in resp.text.lower()
    assert _run(_status(executed["wave_pk"])) == "Asserted"


def test_incomplete_locator_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W104-LOC")
    executed = _assert_wave(admin_headers, wave_id="EV-LOC-001", product=product)

    async def _break_locator():
        async with TestingSessionLocal() as session:
            fact = (
                await session.execute(
                    select(KnowledgeFact)
                    .where(KnowledgeFact.entity_id == product["id"])
                    .limit(1)
                )
            ).scalar_one()
            link = (
                await session.execute(
                    select(KnowledgeEvidenceLink).where(
                        KnowledgeEvidenceLink.fact_id == fact.id
                    )
                )
            ).scalar_one()
            link.locator = {"model": product["sku"], "property": "measurement_range"}
            await session.commit()

    _run(_break_locator())

    resp = client.post(
        "/api/v1/knowledge/waves/EV-LOC-001/validate-evidence",
        json={"change_reason": "bad locator"},
        headers=admin_headers,
    )
    assert resp.status_code == 422, resp.text
    assert "locator" in resp.text.lower() or "pdf_page" in resp.text
    assert _run(_status(executed["wave_pk"])) == "Asserted"


def test_duplicate_fact_rejected():
    """Duplicate product×definition Facts are rejected (unit; SQLite enforces UNIQUE)."""
    from types import SimpleNamespace

    from app.services.knowledge_wave_evidence_service import fact_definition_match_issues

    a = SimpleNamespace(
        id=1,
        status="asserted",
        product_type_definition_id=10,
    )
    b = SimpleNamespace(
        id=2,
        status="asserted",
        product_type_definition_id=10,
    )
    issues = fact_definition_match_issues(
        sku_snapshot="W104-DUP",
        def_id="def.resolution",
        matches=[a, b],  # type: ignore[arg-type]
        wave_definition_id=10,
    )
    assert len(issues) == 1
    assert "duplicate" in issues[0]["message"]


def test_invalid_fact_status_rejected():
    from types import SimpleNamespace

    from app.services.knowledge_wave_evidence_service import fact_definition_match_issues

    fact = SimpleNamespace(
        id=9,
        status="deprecated",
        product_type_definition_id=10,
    )
    issues = fact_definition_match_issues(
        sku_snapshot="W104-STF",
        def_id="def.accuracy",
        matches=[fact],  # type: ignore[arg-type]
        wave_definition_id=10,
    )
    assert any(i["field"] == "facts.status" for i in issues)


def test_missing_artifact_checksum_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W104-ART")
    executed = _assert_wave(admin_headers, wave_id="EV-ART-001", product=product)

    async def _corrupt_checksum():
        from app.db.models.knowledge import KnowledgeEvidenceArtifact

        async with TestingSessionLocal() as session:
            art = await session.get(KnowledgeEvidenceArtifact, 1)
            assert art is not None
            art.checksum_sha256 = "0" * 64
            await session.commit()

    _run(_corrupt_checksum())

    resp = client.post(
        "/api/v1/knowledge/waves/EV-ART-001/validate-evidence",
        json={"change_reason": "bad artifact"},
        headers=admin_headers,
    )
    assert resp.status_code == 422, resp.text
    assert "checksum" in resp.text.lower() or "artifact" in resp.text.lower()
    assert _run(_status(executed["wave_pk"])) == "Asserted"


def test_non_admin_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W104-AUTH")
    _assert_wave(admin_headers, wave_id="EV-AUTH-001", product=product)

    # Drop super-admin override so Bearer customer token is not treated as admin.
    app.dependency_overrides.pop(get_current_super_admin, None)
    resp = client.post(
        "/api/v1/knowledge/waves/EV-AUTH-001/validate-evidence",
        json={"change_reason": "nope"},
        headers=customer_auth_headers(),
    )
    assert resp.status_code in (401, 403), resp.text


async def _status(wave_pk: int) -> str:
    async with TestingSessionLocal() as session:
        wave = await session.get(KnowledgeWave, wave_pk)
        assert wave is not None
        return wave.status
