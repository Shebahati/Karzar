"""Prompt 109 — PR3-B.3 Wave publish orchestration."""

from __future__ import annotations

import asyncio
import copy

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models.knowledge import KnowledgeEvidenceLink, KnowledgeFact, KnowledgeFactRevision
from app.db.models.knowledge_wave import KnowledgeWave, KnowledgeWaveRun
from app.db.models.product import Product
from app.db.models.user import User
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text

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


async def _delete_fact_with_deps(session, fact: KnowledgeFact) -> None:
    """Postgres-safe Fact removal for test setup (revisions + evidence links).

    Use bulk DELETE + flush so SQLAlchemy does not emit DELETE on
    knowledge_facts before dependent revisions/links (UoW ordering).
    """
    fact_id = int(fact.id)
    await session.execute(
        delete(KnowledgeEvidenceLink).where(KnowledgeEvidenceLink.fact_id == fact_id)
    )
    await session.execute(
        delete(KnowledgeFactRevision).where(KnowledgeFactRevision.fact_id == fact_id)
    )
    await session.flush()
    await session.execute(delete(KnowledgeFact).where(KnowledgeFact.id == fact_id))


@pytest.fixture
def admin_headers(monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "true")
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    headers = {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}
    yield headers
    app.dependency_overrides.pop(get_current_super_admin, None)


def _assert_and_evidence(admin_headers, *, wave_id: str, product: dict) -> dict:
    _seal_wave(admin_headers, wave_id=wave_id, product=product)
    executed = client.post(
        f"/api/v1/knowledge/waves/{wave_id}/execute",
        json={
            "change_reason": "assert for publish",
            "sku_units": [_sku_unit(product["sku"], product["id"])],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["wave_status"] == "Asserted"
    ev = client.post(
        f"/api/v1/knowledge/waves/{wave_id}/validate-evidence",
        json={"change_reason": "evidence for publish"},
        headers=admin_headers,
    )
    assert ev.status_code == 200, ev.text
    assert ev.json()["new_status"] == "EvidenceValidated"
    return ev.json()


async def _revision_count() -> int:
    async with TestingSessionLocal() as session:
        return int(
            (
                await session.execute(select(func.count()).select_from(KnowledgeFactRevision))
            ).scalar_one()
        )


async def _fact_ids_for_product(product_id: int) -> list[int]:
    async with TestingSessionLocal() as session:
        rows = (
            await session.execute(
                select(KnowledgeFact.id).where(
                    KnowledgeFact.entity_id == product_id,
                    KnowledgeFact.definition_id.in_(
                        [
                            "def.measurement_range",
                            "def.resolution",
                            "def.accuracy",
                        ]
                    ),
                )
            )
        ).scalars().all()
        return [int(i) for i in rows]


async def _publish_all_facts(admin_headers, product_id: int) -> None:
    ids = await _fact_ids_for_product(product_id)
    assert len(ids) == 3
    for fid in ids:
        resp = client.post(
            f"/api/v1/knowledge/facts/{fid}/publish",
            json={"change_reason": "pre-publish before wave"},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "published"


async def _wave_status(wave_id: str) -> str:
    async with TestingSessionLocal() as session:
        wave = (
            await session.execute(
                select(KnowledgeWave).where(KnowledgeWave.wave_id == wave_id)
            )
        ).scalar_one()
        return wave.status


async def _spec_md5(product_id: int) -> str | None:
    async with TestingSessionLocal() as session:
        # SQLite: hash via Python
        product = await session.get(Product, product_id)
        if product is None:
            return None
        import hashlib
        import json

        payload = json.dumps(
            product.specifications,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        return hashlib.md5(payload.encode()).hexdigest()


async def _evidence_counts() -> tuple[int, int]:
    async with TestingSessionLocal() as session:
        arts = (
            await session.execute(
                text("SELECT count(*) FROM knowledge_evidence_artifacts")
            )
        ).scalar_one()
        links = (
            await session.execute(select(func.count()).select_from(KnowledgeEvidenceLink))
        ).scalar_one()
        return int(arts), int(links)


def test_historical_already_published_facts_skip_without_new_revisions(
    admin_headers, valid_product_data
):
    """INSIZE production shape: Wave EvidenceValidated, Facts already published."""
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-HIST")
    _assert_and_evidence(admin_headers, wave_id="PUB-HIST-001", product=product)
    _run(_publish_all_facts(admin_headers, product["id"]))

    before_rev = _run(_revision_count())
    before_ev = _run(_evidence_counts())
    before_spec = _run(_spec_md5(product["id"]))

    resp = client.post(
        "/api/v1/knowledge/waves/PUB-HIST-001/publish",
        json={"change_reason": "PROMPT 109 historical published Facts"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["previous_status"] == "EvidenceValidated"
    assert body["new_status"] == "Published"
    assert body["wave"]["status"] == "Published"
    assert body["total"] == 3
    assert body["published"] == 0
    assert body["skipped"] == 3
    assert body["failed"] == 0

    assert _run(_revision_count()) == before_rev
    assert _run(_evidence_counts()) == before_ev
    assert _run(_spec_md5(product["id"])) == before_spec
    assert _run(_wave_status("PUB-HIST-001")) == "Published"


def test_mixed_asserted_and_published(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-MIX")
    _assert_and_evidence(admin_headers, wave_id="PUB-MIX-001", product=product)

    async def _publish_two():
        ids = await _fact_ids_for_product(product["id"])
        # Publish first two; leave accuracy asserted
        for fid in ids[:2]:
            resp = client.post(
                f"/api/v1/knowledge/facts/{fid}/publish",
                json={"change_reason": "partial pre-publish"},
                headers=admin_headers,
            )
            assert resp.status_code == 200, resp.text

    _run(_publish_two())
    before_rev = _run(_revision_count())

    resp = client.post(
        "/api/v1/knowledge/waves/PUB-MIX-001/publish",
        json={"change_reason": "PROMPT 109 mixed state"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["new_status"] == "Published"
    assert body["published"] == 1
    assert body["skipped"] == 2
    assert body["failed"] == 0
    # Exactly one new Fact revision for the newly published Fact
    assert _run(_revision_count()) == before_rev + 1


def test_wrong_status_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-ST")
    sealed = _seal_wave(admin_headers, wave_id="PUB-ST-001", product=product)
    assert sealed["status"] == "Sealed"
    resp = client.post(
        "/api/v1/knowledge/waves/PUB-ST-001/publish",
        json={"change_reason": "too early"},
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text


def test_asserted_status_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-AS")
    _seal_wave(admin_headers, wave_id="PUB-AS-001", product=product)
    executed = client.post(
        "/api/v1/knowledge/waves/PUB-AS-001/execute",
        json={
            "change_reason": "assert only",
            "sku_units": [_sku_unit(product["sku"], product["id"])],
        },
        headers=admin_headers,
    )
    assert executed.status_code == 201
    resp = client.post(
        "/api/v1/knowledge/waves/PUB-AS-001/publish",
        json={"change_reason": "skip evidence"},
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text


def test_manifest_mismatch_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-SHA")
    body = _assert_and_evidence(admin_headers, wave_id="PUB-SHA-001", product=product)

    async def _corrupt():
        async with TestingSessionLocal() as session:
            wave = await session.get(KnowledgeWave, body["wave"]["id"])
            assert wave is not None
            wave.manifest_sha256 = "a" * 64
            await session.commit()

    _run(_corrupt())
    resp = client.post(
        "/api/v1/knowledge/waves/PUB-SHA-001/publish",
        json={"change_reason": "sha drift"},
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text
    assert _run(_wave_status("PUB-SHA-001")) == "EvidenceValidated"


def test_freeze_gate_rejected(admin_headers, valid_product_data, monkeypatch):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-FZ")
    _assert_and_evidence(admin_headers, wave_id="PUB-FZ-001", product=product)
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "false")
    resp = client.post(
        "/api/v1/knowledge/waves/PUB-FZ-001/publish",
        json={"change_reason": "freeze off"},
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text


def test_missing_fact_fails_closed(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-MF")
    _assert_and_evidence(admin_headers, wave_id="PUB-MF-001", product=product)

    async def _drop_one():
        async with TestingSessionLocal() as session:
            fact = (
                await session.execute(
                    select(KnowledgeFact).where(
                        KnowledgeFact.entity_id == product["id"],
                        KnowledgeFact.definition_id == "def.accuracy",
                    )
                )
            ).scalar_one()
            await _delete_fact_with_deps(session, fact)
            await session.commit()

    _run(_drop_one())
    resp = client.post(
        "/api/v1/knowledge/waves/PUB-MF-001/publish",
        json={"change_reason": "missing fact"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is False
    assert body["new_status"] == "Failed"
    assert body["failed"] >= 1


def test_assert_failed_cannot_publish_resume_when_latest_run_is_assert(
    admin_headers, valid_product_data
):
    """Failed after assert re-execute must not enter publish (even with old publish run)."""
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-AF")
    _assert_and_evidence(admin_headers, wave_id="PUB-AF-001", product=product)

    async def _drop_accuracy():
        async with TestingSessionLocal() as session:
            fact = (
                await session.execute(
                    select(KnowledgeFact).where(
                        KnowledgeFact.entity_id == product["id"],
                        KnowledgeFact.definition_id == "def.accuracy",
                    )
                )
            ).scalar_one()
            await _delete_fact_with_deps(session, fact)
            await session.commit()

    _run(_drop_accuracy())
    fail = client.post(
        "/api/v1/knowledge/waves/PUB-AF-001/publish",
        json={"change_reason": "first publish fail"},
        headers=admin_headers,
    )
    assert fail.status_code == 200, fail.text
    assert fail.json()["new_status"] == "Failed"

    async def _inject_newer_assert_failed_run():
        async with TestingSessionLocal() as session:
            wave = (
                await session.execute(
                    select(KnowledgeWave).where(KnowledgeWave.wave_id == "PUB-AF-001")
                )
            ).scalar_one()
            actor = (await session.execute(select(User).limit(1))).scalar_one()
            session.add(
                KnowledgeWaveRun(
                    wave_id=wave.id,
                    run_type="assert",
                    status="failed",
                    created_by=actor.id,
                    manifest_sha256_snapshot=wave.manifest_sha256,
                    request_snapshot_json={},
                )
            )
            await session.commit()

    _run(_inject_newer_assert_failed_run())
    resp = client.post(
        "/api/v1/knowledge/waves/PUB-AF-001/publish",
        json={"change_reason": "should reject"},
        headers=admin_headers,
    )
    assert resp.status_code == 409, resp.text
    assert _run(_wave_status("PUB-AF-001")) == "Failed"


def test_resume_after_partial_does_not_duplicate_revisions(
    admin_headers, valid_product_data
):
    """Fail mid-publish via missing Fact, restore Fact, resume publish."""
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-RS")
    _assert_and_evidence(admin_headers, wave_id="PUB-RS-001", product=product)

    # Pre-publish two facts so first product handling would skip them;
    # remove accuracy to force failure after skips.
    async def _prep():
        by_def: dict[str, int] = {}
        async with TestingSessionLocal() as session:
            facts = (
                await session.execute(
                    select(KnowledgeFact).where(KnowledgeFact.entity_id == product["id"])
                )
            ).scalars().all()
            for f in facts:
                by_def[f.definition_id] = f.id
        for def_id in ("def.measurement_range", "def.resolution"):
            r = client.post(
                f"/api/v1/knowledge/facts/{by_def[def_id]}/publish",
                json={"change_reason": "pre"},
                headers=admin_headers,
            )
            assert r.status_code == 200
        # Delete accuracy fact to force failure
        async with TestingSessionLocal() as session:
            fact = await session.get(KnowledgeFact, by_def["def.accuracy"])
            assert fact is not None
            snap = {
                "entity_id": fact.entity_id,
                "definition_id": fact.definition_id,
                "product_type_definition_id": fact.product_type_definition_id,
                "value": copy.deepcopy(fact.value),
                "unit": fact.unit,
                "qualifier": fact.qualifier,
                "source_id": fact.source_id,
                "confidence": fact.confidence,
                "recorded_at": fact.recorded_at,
                "recorder": fact.recorder,
            }
            await _delete_fact_with_deps(session, fact)
            await session.commit()
            return snap

    snap = _run(_prep())
    before_fail_rev = _run(_revision_count())

    fail_resp = client.post(
        "/api/v1/knowledge/waves/PUB-RS-001/publish",
        json={"change_reason": "expect fail"},
        headers=admin_headers,
    )
    assert fail_resp.status_code == 200, fail_resp.text
    assert fail_resp.json()["new_status"] == "Failed"
    # Skipped publishes should have been committed before failure path —
    # but we pre-published those two already; no new revisions for skips.
    assert _run(_revision_count()) == before_fail_rev

    async def _restore():
        from datetime import UTC, datetime

        from app.db.models.user import User
        from app.services import knowledge_evidence_service as evidence_service

        async with TestingSessionLocal() as session:
            fact = KnowledgeFact(
                entity_id=snap["entity_id"],
                definition_id=snap["definition_id"],
                product_type_definition_id=snap["product_type_definition_id"],
                value=snap["value"],
                unit=snap["unit"],
                qualifier=snap["qualifier"],
                status="asserted",
                source_id=snap["source_id"],
                confidence=snap["confidence"],
                recorded_at=snap["recorded_at"] or datetime.now(UTC),
                recorder=snap["recorder"],
            )
            session.add(fact)
            await session.flush()
            actor = (await session.execute(select(User).limit(1))).scalar_one()
            await evidence_service.link_artifact_to_fact(
                session,
                artifact_pk=1,
                fact_id=fact.id,
                locator={
                    "pdf_page": 36,
                    "printed_page": 28,
                    "model": product["sku"],
                    "property": "accuracy",
                },
                notes=None,
                actor=actor,
            )
            await session.commit()

    _run(_restore())
    before_resume_rev = _run(_revision_count())

    resume = client.post(
        "/api/v1/knowledge/waves/PUB-RS-001/publish",
        json={"change_reason": "resume after restore"},
        headers=admin_headers,
    )
    assert resume.status_code == 200, resume.text
    body = resume.json()
    assert body["new_status"] == "Published"
    assert body["published"] == 1
    assert body["skipped"] == 2
    assert _run(_revision_count()) == before_resume_rev + 1


def test_unrelated_product_facts_untouched(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-UR")
    other = _create_product(admin_headers, valid_product_data, "W109-OTHER")
    _assert_and_evidence(admin_headers, wave_id="PUB-UR-001", product=product)

    # Create an asserted Fact on the unrelated product (same defs) via batch is heavy;
    # just ensure wave publish doesn't change other product's fact count.
    async def _other_fact_count():
        async with TestingSessionLocal() as session:
            return int(
                (
                    await session.execute(
                        select(func.count()).select_from(KnowledgeFact).where(
                            KnowledgeFact.entity_id == other["id"]
                        )
                    )
                ).scalar_one()
            )

    before = _run(_other_fact_count())
    resp = client.post(
        "/api/v1/knowledge/waves/PUB-UR-001/publish",
        json={"change_reason": "scope check"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["new_status"] == "Published"
    assert _run(_other_fact_count()) == before


def test_non_admin_rejected(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "W109-AUTH")
    _assert_and_evidence(admin_headers, wave_id="PUB-AUTH-001", product=product)
    app.dependency_overrides.pop(get_current_super_admin, None)
    resp = client.post(
        "/api/v1/knowledge/waves/PUB-AUTH-001/publish",
        json={"change_reason": "nope"},
        headers=customer_auth_headers(),
    )
    assert resp.status_code in (401, 403), resp.text
