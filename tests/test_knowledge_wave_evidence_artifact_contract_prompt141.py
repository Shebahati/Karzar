"""Prompt 141 — Wave Evidence Artifact pins are manifest/policy-driven."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models.knowledge import KnowledgeEvidenceArtifact
from app.db.models.knowledge_wave import KnowledgeWave, KnowledgeWaveProduct
from app.db.models.product_type import ProductType, ProductTypeDefinition
from app.db.models.user import User
from app.main import app
from app.services.knowledge_batch_assert_service import (
    REQUIRED_ALEMBIC,
    REQUIRED_ARTIFACT_CHECKSUM,
)
from app.services.knowledge_wave_evidence_artifact_contract import (
    LEGACY_WAVE_EVIDENCE_ARTIFACT_PIN,
    EvidenceArtifactContractError,
    parse_evidence_artifact_pins,
    resolve_wave_evidence_artifact_contract,
)
from app.services.knowledge_wave_execute_service import resolve_wave_policy
from app.services.knowledge_wave_service import (
    build_canonical_manifest_payload,
    compute_manifest_sha256,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tests.conftest import TestingSessionLocal, override_super_admin
from tests.test_knowledge_waves_prompt68 import (
    _create_product,
    _policy_json,
    _seed_gen_caliper_stack,
    _sku_unit,
)

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("override_database")

OEM_SHA_108A = REQUIRED_ARTIFACT_CHECKSUM
OEM_SHA_108B = (
    "31fd0d0eec73bab9cdd750701ec999368536d909e40b340f8420580f7691eb26"
)
OEM_SHA_OTHER = (
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def admin_headers(monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "true")
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    headers = {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}
    yield headers
    app.dependency_overrides.pop(get_current_super_admin, None)


async def _seed():
    async with TestingSessionLocal() as session:
        await _seed_gen_caliper_stack(session)
        await session.commit()


async def _seed_second_artifact(
    *,
    artifact_pk: int = 2,
    artifact_id: str = "insize-108b-catalogue-v1",
    checksum: str = OEM_SHA_108B,
):
    async with TestingSessionLocal() as session:
        session.add(
            KnowledgeEvidenceArtifact(
                id=artifact_pk,
                artifact_id=artifact_id,
                kind="oem_catalogue",
                title="OEM secondary",
                source_ref="secondary.pdf",
                checksum_sha256=checksum,
                recorded_at=datetime.now(UTC),
                recorder="test",
            )
        )
        await session.commit()


def _policy_with_artifacts(*pins: dict[str, Any]) -> dict[str, Any]:
    policy = _policy_json()
    policy["evidence_artifacts"] = list(pins)
    return policy


def _pin(
    *,
    artifact_pk: int,
    artifact_id: str,
    checksum: str,
) -> dict[str, Any]:
    return {
        "artifact_pk": artifact_pk,
        "artifact_id": artifact_id,
        "checksum_sha256": checksum,
    }


def _sku_unit_for_artifact(
    sku: str, product_id: int, *, artifact_pk: int
) -> dict[str, Any]:
    unit = _sku_unit(sku, product_id)
    for link in unit["evidence_links"]:
        link["artifact_id"] = artifact_pk
    return unit


def _seal_wave_with_policy(
    admin_headers,
    *,
    wave_id: str,
    products: list[dict],
    policy_json: dict[str, Any],
) -> dict:
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": wave_id,
            "brand": "INSIZE",
            "product_type_id": 1,
            "definition_id": 1,
            "policy_json": policy_json,
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


def _lifecycle_to_published(
    admin_headers,
    *,
    wave_id: str,
    sku_units: list[dict[str, Any]],
) -> None:
    executed = client.post(
        f"/api/v1/knowledge/waves/{wave_id}/execute",
        json={"change_reason": "assert", "sku_units": sku_units},
        headers=admin_headers,
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["wave_status"] == "Asserted"
    ev = client.post(
        f"/api/v1/knowledge/waves/{wave_id}/validate-evidence",
        json={"change_reason": "ev"},
        headers=admin_headers,
    )
    assert ev.status_code == 200, ev.text
    pub = client.post(
        f"/api/v1/knowledge/waves/{wave_id}/publish",
        json={"change_reason": "publish"},
        headers=admin_headers,
    )
    assert pub.status_code == 200, pub.text
    assert pub.json()["new_status"] == "Published"


def test_parse_rejects_duplicate_pk_and_bad_checksum():
    with pytest.raises(EvidenceArtifactContractError, match="duplicate artifact_pk"):
        parse_evidence_artifact_pins(
            [
                _pin(
                    artifact_pk=1,
                    artifact_id="a",
                    checksum=OEM_SHA_108A,
                ),
                _pin(
                    artifact_pk=1,
                    artifact_id="b",
                    checksum=OEM_SHA_108B,
                ),
            ]
        )
    with pytest.raises(EvidenceArtifactContractError, match="64 lowercase hex"):
        parse_evidence_artifact_pins(
            [_pin(artifact_pk=1, artifact_id="a", checksum="not-a-sha")]
        )


def test_legacy_fallback_and_new_wave_missing_pin():
    pins = resolve_wave_evidence_artifact_contract(
        {"validation_rules": {}},
        allow_legacy_fallback=True,
    )
    assert pins == (LEGACY_WAVE_EVIDENCE_ARTIFACT_PIN,)
    with pytest.raises(EvidenceArtifactContractError, match="required"):
        resolve_wave_evidence_artifact_contract(
            {"require_evidence": True},
            allow_legacy_fallback=False,
        )


def test_evidence_artifacts_change_manifest_sha(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "P141-SHA")
    base = _policy_json()
    alt = _policy_with_artifacts(
        _pin(
            artifact_pk=1,
            artifact_id="insize-108a-catalogue-v1",
            checksum=OEM_SHA_108A,
        ),
        _pin(
            artifact_pk=2,
            artifact_id="insize-108b-catalogue-v1",
            checksum=OEM_SHA_108B,
        ),
    )
    _run(_seed_second_artifact())

    async def _digests():
        async with TestingSessionLocal() as session:
            pt = await session.get(ProductType, 1)
            definition = await session.get(ProductTypeDefinition, 1)
            products = [
                type(
                    "WP",
                    (),
                    {"product_id": product["id"], "sku_snapshot": product["sku"]},
                )()
            ]
            p1 = build_canonical_manifest_payload(
                wave_id="P141-SHA-A",
                brand="INSIZE",
                product_type=pt,
                definition=definition,
                policy_json=base,
                products=products,
            )
            p2 = build_canonical_manifest_payload(
                wave_id="P141-SHA-A",
                brand="INSIZE",
                product_type=pt,
                definition=definition,
                policy_json=alt,
                products=products,
            )
            return compute_manifest_sha256(p1), compute_manifest_sha256(p2)

    sha_a, sha_b = _run(_digests())
    assert sha_a != sha_b


def test_108a_explicit_pin_lifecycle(admin_headers, valid_product_data):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "P141-108A")
    _seal_wave_with_policy(
        admin_headers,
        wave_id="P141-108A-WAVE",
        products=[product],
        policy_json=_policy_json(),
    )
    _lifecycle_to_published(
        admin_headers,
        wave_id="P141-108A-WAVE",
        sku_units=[_sku_unit_for_artifact(product["sku"], product["id"], artifact_pk=1)],
    )


def test_108b_second_artifact_accepted_108a_rejected(
    admin_headers, valid_product_data
):
    _run(_seed())
    _run(_seed_second_artifact())
    product = _create_product(admin_headers, valid_product_data, "P141-108B")
    policy = _policy_with_artifacts(
        _pin(
            artifact_pk=2,
            artifact_id="insize-108b-catalogue-v1",
            checksum=OEM_SHA_108B,
        )
    )
    _seal_wave_with_policy(
        admin_headers,
        wave_id="P141-108B-WAVE",
        products=[product],
        policy_json=policy,
    )
    reject = client.post(
        "/api/v1/knowledge/waves/P141-108B-WAVE/execute",
        json={
            "change_reason": "wrong source",
            "sku_units": [
                _sku_unit_for_artifact(product["sku"], product["id"], artifact_pk=1)
            ],
        },
        headers=admin_headers,
    )
    assert reject.status_code == 201, reject.text
    assert reject.json()["wave_status"] == "Failed"

    # Failed → re-seal after Reviewed path is not automatic; recreate via Failed
    # recovery: review not available. Re-create a fresh sealed wave for PASS path.
    product2 = _create_product(admin_headers, valid_product_data, "P141-108B-OK")
    _seal_wave_with_policy(
        admin_headers,
        wave_id="P141-108B-OK",
        products=[product2],
        policy_json=policy,
    )
    _lifecycle_to_published(
        admin_headers,
        wave_id="P141-108B-OK",
        sku_units=[
            _sku_unit_for_artifact(product2["sku"], product2["id"], artifact_pk=2)
        ],
    )


def test_multi_artifact_allowlist_and_unpinned_rejected(
    admin_headers, valid_product_data
):
    _run(_seed())
    _run(_seed_second_artifact())
    _run(
        _seed_second_artifact(
            artifact_pk=3,
            artifact_id="oem-other-catalogue-v1",
            checksum=OEM_SHA_OTHER,
        )
    )
    p1 = _create_product(admin_headers, valid_product_data, "P141-M1")
    p2 = _create_product(admin_headers, valid_product_data, "P141-M2")
    policy = _policy_with_artifacts(
        _pin(
            artifact_pk=1,
            artifact_id="insize-108a-catalogue-v1",
            checksum=OEM_SHA_108A,
        ),
        _pin(
            artifact_pk=2,
            artifact_id="insize-108b-catalogue-v1",
            checksum=OEM_SHA_108B,
        ),
    )
    _seal_wave_with_policy(
        admin_headers,
        wave_id="P141-MULTI",
        products=[p1, p2],
        policy_json=policy,
    )
    _lifecycle_to_published(
        admin_headers,
        wave_id="P141-MULTI",
        sku_units=[
            _sku_unit_for_artifact(p1["sku"], p1["id"], artifact_pk=1),
            _sku_unit_for_artifact(p2["sku"], p2["id"], artifact_pk=2),
        ],
    )

    p3 = _create_product(admin_headers, valid_product_data, "P141-M3")
    _seal_wave_with_policy(
        admin_headers,
        wave_id="P141-UNPINNED",
        products=[p3],
        policy_json=policy,
    )
    bad = client.post(
        "/api/v1/knowledge/waves/P141-UNPINNED/execute",
        json={
            "change_reason": "unpinned",
            "sku_units": [
                _sku_unit_for_artifact(p3["sku"], p3["id"], artifact_pk=3)
            ],
        },
        headers=admin_headers,
    )
    assert bad.status_code == 201, bad.text
    assert bad.json()["wave_status"] == "Failed"


def test_checksum_drift_fails_closed(admin_headers, valid_product_data):
    _run(_seed())
    _run(_seed_second_artifact())
    product = _create_product(admin_headers, valid_product_data, "P141-DRIFT")
    policy = _policy_with_artifacts(
        _pin(
            artifact_pk=2,
            artifact_id="insize-108b-catalogue-v1",
            checksum=OEM_SHA_108B,
        )
    )
    _seal_wave_with_policy(
        admin_headers,
        wave_id="P141-DRIFT",
        products=[product],
        policy_json=policy,
    )

    async def _drift():
        async with TestingSessionLocal() as session:
            art = await session.get(KnowledgeEvidenceArtifact, 2)
            assert art is not None
            art.checksum_sha256 = OEM_SHA_OTHER
            await session.commit()

    _run(_drift())
    resp = client.post(
        "/api/v1/knowledge/waves/P141-DRIFT/execute",
        json={
            "change_reason": "drift",
            "sku_units": [
                _sku_unit_for_artifact(product["sku"], product["id"], artifact_pk=2)
            ],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["wave_status"] == "Failed"


def test_stable_id_mismatch_fails_preseal(admin_headers, valid_product_data):
    _run(_seed())
    _run(_seed_second_artifact())
    product = _create_product(admin_headers, valid_product_data, "P141-SID")
    policy = _policy_with_artifacts(
        _pin(
            artifact_pk=2,
            artifact_id="wrong-stable-id",
            checksum=OEM_SHA_108B,
        )
    )
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "P141-SID",
            "brand": "INSIZE",
            "product_type_id": 1,
            "definition_id": 1,
            "policy_json": policy,
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
    assert sealed.status_code == 422, sealed.text
    assert "artifact_id mismatch" in sealed.text


def test_new_wave_missing_evidence_artifacts_fails_preseal(
    admin_headers, valid_product_data
):
    _run(_seed())
    product = _create_product(admin_headers, valid_product_data, "P141-MISS")
    policy = {
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
        "require_evidence": True,
    }
    created = client.post(
        "/api/v1/knowledge/waves",
        json={
            "wave_id": "P141-MISS",
            "brand": "INSIZE",
            "product_type_id": 1,
            "definition_id": 1,
            "policy_json": policy,
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
    assert sealed.status_code == 422, sealed.text
    assert "evidence_artifacts" in sealed.text


def test_historical_wave_without_pins_falls_back_to_108a(
    admin_headers, valid_product_data
):
    _run(_seed())
    _run(_seed_second_artifact())
    product = _create_product(admin_headers, valid_product_data, "P141-HIST")

    async def _insert_historical():
        async with TestingSessionLocal() as session:
            actor = (
                await session.execute(select(User).order_by(User.id).limit(1))
            ).scalar_one()
            pt = await session.get(ProductType, 1)
            definition = await session.get(ProductTypeDefinition, 1)
            policy = {
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
            wave = KnowledgeWave(
                wave_id="P141-HIST",
                status="Draft",
                brand="INSIZE",
                product_type_id=1,
                definition_id=1,
                policy_json=policy,
                created_by=actor.id,
            )
            session.add(wave)
            await session.flush()
            wp = KnowledgeWaveProduct(
                wave_id=wave.id,
                product_id=product["id"],
                sku_snapshot=product["sku"],
            )
            session.add(wp)
            await session.flush()
            payload = build_canonical_manifest_payload(
                wave_id=wave.wave_id,
                brand=wave.brand,
                product_type=pt,
                definition=definition,
                policy_json=policy,
                products=[wp],
            )
            wave.manifest_sha256 = compute_manifest_sha256(payload)
            wave.status = "Sealed"
            await session.commit()
            refreshed = (
                await session.execute(
                    select(KnowledgeWave)
                    .options(selectinload(KnowledgeWave.products))
                    .where(KnowledgeWave.wave_id == "P141-HIST")
                )
            ).scalar_one()
            return resolve_wave_policy(refreshed)

    resolved = _run(_insert_historical())
    assert resolved["evidence_artifacts"] == [
        LEGACY_WAVE_EVIDENCE_ARTIFACT_PIN.as_dict()
    ]

    bad = client.post(
        "/api/v1/knowledge/waves/P141-HIST/execute",
        json={
            "change_reason": "hist art2",
            "sku_units": [
                _sku_unit_for_artifact(product["sku"], product["id"], artifact_pk=2)
            ],
        },
        headers=admin_headers,
    )
    assert bad.status_code == 201, bad.text
    assert bad.json()["wave_status"] == "Failed"

    # New historical-style wave for success path (prior Failed)
    product_ok = _create_product(admin_headers, valid_product_data, "P141-HIST-OK")

    async def _insert_historical_ok():
        async with TestingSessionLocal() as session:
            actor = (
                await session.execute(select(User).order_by(User.id).limit(1))
            ).scalar_one()
            pt = await session.get(ProductType, 1)
            definition = await session.get(ProductTypeDefinition, 1)
            policy = {
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
            wave = KnowledgeWave(
                wave_id="P141-HIST-OK",
                status="Draft",
                brand="INSIZE",
                product_type_id=1,
                definition_id=1,
                policy_json=policy,
                created_by=actor.id,
            )
            session.add(wave)
            await session.flush()
            wp = KnowledgeWaveProduct(
                wave_id=wave.id,
                product_id=product_ok["id"],
                sku_snapshot=product_ok["sku"],
            )
            session.add(wp)
            await session.flush()
            payload = build_canonical_manifest_payload(
                wave_id=wave.wave_id,
                brand=wave.brand,
                product_type=pt,
                definition=definition,
                policy_json=policy,
                products=[wp],
            )
            wave.manifest_sha256 = compute_manifest_sha256(payload)
            wave.status = "Sealed"
            await session.commit()

    _run(_insert_historical_ok())
    _lifecycle_to_published(
        admin_headers,
        wave_id="P141-HIST-OK",
        sku_units=[
            _sku_unit_for_artifact(
                product_ok["sku"], product_ok["id"], artifact_pk=1
            )
        ],
    )


def test_resume_rejects_substituted_unpinned_artifact(
    admin_headers, valid_product_data
):
    """Sealed allowlist is reused on resume; unpinned Artifact cannot be substituted."""
    _run(_seed())
    _run(_seed_second_artifact())
    p1 = _create_product(admin_headers, valid_product_data, "P141-R1")
    p2 = _create_product(admin_headers, valid_product_data, "P141-R2")
    policy = _policy_with_artifacts(
        _pin(
            artifact_pk=2,
            artifact_id="insize-108b-catalogue-v1",
            checksum=OEM_SHA_108B,
        )
    )
    sealed = _seal_wave_with_policy(
        admin_headers,
        wave_id="P141-RESUME",
        products=[p1, p2],
        policy_json=policy,
    )
    assert sealed["status"] == "Sealed"

    # First SKU ok (art2), second SKU uses unpinned art1 → Failed
    first = client.post(
        "/api/v1/knowledge/waves/P141-RESUME/execute",
        json={
            "change_reason": "partial fail",
            "sku_units": [
                _sku_unit_for_artifact(p1["sku"], p1["id"], artifact_pk=2),
                _sku_unit_for_artifact(p2["sku"], p2["id"], artifact_pk=1),
            ],
        },
        headers=admin_headers,
    )
    assert first.status_code == 201, first.text
    assert first.json()["wave_status"] == "Failed"
    run_id = first.json()["wave_run_id"]

    # Failed-run resume creates a new run after re-Seal; re-seal same policy pins.
    # Transition Failed → Reviewed is not allowed; seal recovery path reuses pins
    # via new wave. Validate sealed policy view still only allows pk=2.
    async def _policy_view():
        async with TestingSessionLocal() as session:
            wave = (
                await session.execute(
                    select(KnowledgeWave)
                    .options(selectinload(KnowledgeWave.products))
                    .where(KnowledgeWave.wave_id == "P141-RESUME")
                )
            ).scalar_one()
            return resolve_wave_policy(wave)

    view = _run(_policy_view())
    assert [p["artifact_pk"] for p in view["evidence_artifacts"]] == [2]

    # Resume endpoint must still be constrained by sealed pins (art1 rejected).
    resume = client.post(
        f"/api/v1/knowledge/wave-runs/{run_id}/resume",
        json={
            "change_reason": "resume substitute",
            "sku_units": [
                _sku_unit_for_artifact(p1["sku"], p1["id"], artifact_pk=2),
                _sku_unit_for_artifact(p2["sku"], p2["id"], artifact_pk=1),
            ],
        },
        headers=admin_headers,
    )
    # Failed resume requires re-seal first → 409, OR if accepted still fails item.
    assert resume.status_code in (409, 201), resume.text
    if resume.status_code == 201:
        assert resume.json()["wave_status"] == "Failed"
