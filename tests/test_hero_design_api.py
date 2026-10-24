"""Hero Studio PR1 API tests (Issue #550)."""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import pytest
from app.api.deps import get_current_super_admin
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.schemas.hero_design import EXPECTED_R0_SHA256
from app.services import hero_design_service as hero_svc
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal, override_super_admin

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("override_database")

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "hero_design_r0.json"


def _run(coro):
    return asyncio.run(coro)


async def _seed_r0():
    async with TestingSessionLocal() as session:
        await hero_svc.seed_r0_if_absent(session)
        await session.commit()


@pytest.fixture
def admin_headers():
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    headers = {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}
    yield headers
    app.dependency_overrides.pop(get_current_super_admin, None)


@pytest.fixture
def hero_seeded():
    _run(_seed_r0())
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_r0_fixture_sha_matches_storefront_baseline():
    assert hero_svc.pack_file_sha256(FIXTURE) == EXPECTED_R0_SHA256


def test_public_get_published_after_seed(hero_seeded):
    res = client.get("/api/v1/storefront/hero-design")
    assert res.status_code == 200
    body = res.json()
    assert body["etag"] == EXPECTED_R0_SHA256
    assert len(body["pack"]["slides"]) >= 5
    assert res.headers.get("etag")


def test_publish_disabled_by_default(hero_seeded, step_up_headers):
    res = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": None, "publish_comment": "t"},
        headers=step_up_headers,
    )
    assert res.status_code == 403
    assert res.json()["error_code"] == "FORBIDDEN"


def test_publish_requires_step_up(hero_seeded, admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "HERO_STUDIO_API_PUBLISH", True)
    res = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": None},
        headers=admin_headers,
    )
    assert res.status_code == 403
    assert res.json()["error_code"] == "STEP_UP_REQUIRED"


def test_publish_parent_mismatch(hero_seeded, step_up_headers, monkeypatch):
    monkeypatch.setattr(settings, "HERO_STUDIO_API_PUBLISH", True)
    pub = client.get("/api/v1/cms/hero-design/published", headers=step_up_headers)
    res = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": "00000000-0000-0000-0000-000000000000"},
        headers=step_up_headers,
    )
    assert res.status_code == 409
    assert pub.json()["revision_id"]


def test_publish_success_and_rollback(hero_seeded, step_up_headers, monkeypatch):
    monkeypatch.setattr(settings, "HERO_STUDIO_API_PUBLISH", True)
    pub = client.get("/api/v1/cms/hero-design/published", headers=step_up_headers)
    parent = pub.json()["revision_id"]
    pack = copy.deepcopy(pub.json()["pack"])
    pack["publishedAt"] = "2099-01-01T00:00:00.000Z"

    async def _update_draft():
        from app.db.models.hero_design import HeroDesignDraft

        async with TestingSessionLocal() as session:
            draft = await session.get(HeroDesignDraft, 1)
            assert draft is not None
            draft.draft_json = pack
            await session.commit()

    _run(_update_draft())

    pin = client.post(
        "/api/v1/auth/verify-pin",
        json={"pin": settings.ADMIN_STEP_UP_PIN},
        headers={"Authorization": step_up_headers["Authorization"]},
    )
    headers2 = {
        **step_up_headers,
        "X-Step-Up-Token": pin.json()["secure_token"],
    }
    publish = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": parent, "publish_comment": "test"},
        headers=headers2,
    )
    assert publish.status_code == 200
    new_id = publish.json()["revision_id"]
    assert new_id != parent

    pin2 = client.post(
        "/api/v1/auth/verify-pin",
        json={"pin": settings.ADMIN_STEP_UP_PIN},
        headers={"Authorization": step_up_headers["Authorization"]},
    )
    headers3 = {
        **step_up_headers,
        "X-Step-Up-Token": pin2.json()["secure_token"],
    }
    rollback = client.post(
        "/api/v1/cms/hero-design/rollback",
        json={"revision_id": parent},
        headers=headers3,
    )
    assert rollback.status_code == 200
    assert rollback.json()["revision_id"] == parent


def test_step_up_replay_rejected(hero_seeded, step_up_headers, monkeypatch):
    monkeypatch.setattr(settings, "HERO_STUDIO_API_PUBLISH", True)
    pub = client.get("/api/v1/cms/hero-design/published", headers=step_up_headers)
    parent = pub.json()["revision_id"]
    token = step_up_headers["X-Step-Up-Token"]
    first = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": parent},
        headers=step_up_headers,
    )
    assert first.status_code in (200, 409)
    replay = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": parent},
        headers={**step_up_headers, "X-Step-Up-Token": token},
    )
    assert replay.status_code == 403
    assert replay.json()["error_code"] == "STEP_UP_INVALID"


def test_validate_rejects_bad_pack(admin_headers):
    res = client.post(
        "/api/v1/cms/hero-design/validate",
        json={"pack_json": {"version": 1, "slides": []}},
        headers=admin_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is False
    assert body["errors"]


def test_draft_get_read_only(hero_seeded, admin_headers):
    res = client.get("/api/v1/cms/hero-design/draft", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["lock_version"] >= 1


def test_draft_put_deferred(admin_headers):
    res = client.put(
        "/api/v1/cms/hero-design/draft",
        json={"draft_json": {}},
        headers=admin_headers,
    )
    assert res.status_code == 501


def test_revision_history(hero_seeded, admin_headers):
    res = client.get("/api/v1/cms/hero-design/revisions", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_publish_persists_across_sessions(hero_seeded, step_up_headers, monkeypatch):
    monkeypatch.setattr(settings, "HERO_STUDIO_API_PUBLISH", True)
    pub = client.get("/api/v1/cms/hero-design/published", headers=step_up_headers)
    parent = pub.json()["revision_id"]
    publish = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": parent},
        headers=step_up_headers,
    )
    assert publish.status_code == 200
    new_id = publish.json()["revision_id"]

    async def _read_pointer():
        async with TestingSessionLocal() as session:
            pointer = await hero_svc.get_published_pointer(session)
            return pointer.revision_id if pointer else None

    assert _run(_read_pointer()) == new_id


def test_publish_parent_mismatch_after_successful_publish(hero_seeded, step_up_headers, monkeypatch):
    monkeypatch.setattr(settings, "HERO_STUDIO_API_PUBLISH", True)
    pub = client.get("/api/v1/cms/hero-design/published", headers=step_up_headers)
    stale_parent = pub.json()["revision_id"]
    first = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": stale_parent},
        headers=step_up_headers,
    )
    assert first.status_code == 200

    pin = client.post(
        "/api/v1/auth/verify-pin",
        json={"pin": settings.ADMIN_STEP_UP_PIN},
        headers={"Authorization": step_up_headers["Authorization"]},
    )
    headers2 = {**step_up_headers, "X-Step-Up-Token": pin.json()["secure_token"]}
    second = client.post(
        "/api/v1/cms/hero-design/publish",
        json={"expected_parent_revision_id": stale_parent},
        headers=headers2,
    )
    assert second.status_code == 409
