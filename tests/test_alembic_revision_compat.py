"""Alembic sealed-pin lineage compatibility (Prompt 107)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from app.services.alembic_revision_compat import (
    get_alembic_script_directory,
    is_runtime_revision_compatible,
)
from app.services.knowledge_batch_assert_service import assert_environment_gates
from fastapi import HTTPException

from tests.conftest import TestingSessionLocal
from tests.test_knowledge_waves_prompt68 import _ensure_gates

pytestmark = pytest.mark.usefixtures("override_database")


def _run(coro):
    return asyncio.run(coro)


class _FakeScript:
    """Minimal ScriptDirectory double: revision_id -> down_revision."""

    def __init__(self, edges: dict[str, str | tuple[str, ...] | None]) -> None:
        self._edges = edges

    def get_revision(self, id_: str) -> SimpleNamespace:
        if id_ not in self._edges:
            raise KeyError(id_)
        return SimpleNamespace(revision=id_, down_revision=self._edges[id_])


def test_equal_revisions_pass():
    script = _FakeScript({"a": None})
    assert is_runtime_revision_compatible("a", "a", script_directory=script)


def test_direct_child_passes():
    script = _FakeScript({"parent": None, "child": "parent"})
    assert is_runtime_revision_compatible(
        "parent", "child", script_directory=script
    )


def test_multi_descendant_passes():
    script = _FakeScript({"root": None, "mid": "root", "leaf": "mid"})
    assert is_runtime_revision_compatible(
        "root", "leaf", script_directory=script
    )


def test_runtime_older_than_sealed_fails():
    script = _FakeScript({"root": None, "mid": "root", "leaf": "mid"})
    assert not is_runtime_revision_compatible(
        "leaf", "root", script_directory=script
    )


def test_divergent_branches_fail():
    script = _FakeScript(
        {
            "base": None,
            "left": "base",
            "right": "base",
        }
    )
    assert not is_runtime_revision_compatible(
        "left", "right", script_directory=script
    )


def test_unknown_sealed_fails():
    script = _FakeScript({"a": None})
    assert not is_runtime_revision_compatible(
        "missing", "a", script_directory=script
    )


def test_unknown_runtime_fails():
    script = _FakeScript({"a": None})
    assert not is_runtime_revision_compatible(
        "a", "missing", script_directory=script
    )


def test_blank_revisions_fail_closed():
    script = _FakeScript({"a": None})
    assert not is_runtime_revision_compatible("", "a", script_directory=script)
    assert not is_runtime_revision_compatible("a", "  ", script_directory=script)


def test_real_graph_pr3b1_descendant_of_r1():
    """Production Prompt 106 condition: sealed r1…, runtime s2… (direct child)."""
    script = get_alembic_script_directory()
    assert is_runtime_revision_compatible(
        "r1s2t3u4v5w6",
        "s2t3u4v5w6x7",
        script_directory=script,
    )
    assert not is_runtime_revision_compatible(
        "s2t3u4v5w6x7",
        "r1s2t3u4v5w6",
        script_directory=script,
    )


def test_environment_gate_allows_descendant(monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "true")

    async def _go():
        async with TestingSessionLocal() as session:
            await _ensure_gates(session, plane="live", alembic="s2t3u4v5w6x7")
            await session.commit()
            await assert_environment_gates(
                session,
                pins={
                    "plane": "live",
                    "alembic": "r1s2t3u4v5w6",
                    "freeze_required": True,
                },
            )

    _run(_go())


def test_environment_gate_rejects_older_runtime(monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "true")

    async def _go():
        async with TestingSessionLocal() as session:
            await _ensure_gates(session, plane="live", alembic="r1s2t3u4v5w6")
            await session.commit()
            with pytest.raises(HTTPException) as exc:
                await assert_environment_gates(
                    session,
                    pins={
                        "plane": "live",
                        "alembic": "s2t3u4v5w6x7",
                        "freeze_required": True,
                    },
                )
            assert exc.value.status_code == 409
            detail = str(exc.value.detail).lower()
            assert "alembic_version" in detail or "compatible" in detail

    _run(_go())


def test_environment_gate_plane_still_exact(monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "true")

    async def _go():
        async with TestingSessionLocal() as session:
            # Allowed by ck_environment_identity_plane, but not the sealed pin.
            await _ensure_gates(
                session, plane="catalog_staging", alembic="s2t3u4v5w6x7"
            )
            await session.commit()
            with pytest.raises(HTTPException) as exc:
                await assert_environment_gates(
                    session,
                    pins={
                        "plane": "live",
                        "alembic": "r1s2t3u4v5w6",
                        "freeze_required": True,
                    },
                )
            assert exc.value.status_code == 409
            assert "plane" in str(exc.value.detail).lower()

    _run(_go())


def test_environment_gate_freeze_still_required(monkeypatch):
    monkeypatch.setenv("KARZAR_DEPLOY_FREEZE", "false")

    async def _go():
        async with TestingSessionLocal() as session:
            await _ensure_gates(session, plane="live", alembic="s2t3u4v5w6x7")
            await session.commit()
            with pytest.raises(HTTPException) as exc:
                await assert_environment_gates(
                    session,
                    pins={
                        "plane": "live",
                        "alembic": "r1s2t3u4v5w6",
                        "freeze_required": True,
                    },
                )
            assert exc.value.status_code == 409
            assert "KARZAR_DEPLOY_FREEZE" in str(exc.value.detail)

    _run(_go())
