"""Unit tests for scripts/ingestion_boundary.py (ADR-012 fail-closed)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "ingestion_boundary.py"


def _load():
    spec = importlib.util.spec_from_file_location("ingestion_boundary", MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ingestion_boundary"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def ib(monkeypatch):
    monkeypatch.delenv("KARZAR_ALLOW_PRODUCTION_WRITE", raising=False)
    monkeypatch.delenv("KARZAR_INGESTION_CATEGORY", raising=False)
    monkeypatch.delenv("KARZAR_API_BASE", raising=False)
    monkeypatch.delenv("PUBLIC_ASSET_BASE", raising=False)
    return _load()


def test_local_default_passes(ib):
    assert ib.resolve_api_base() == "http://127.0.0.1:8000/api/v1"
    assert ib.resolve_asset_base() == "http://127.0.0.1:8000"


def test_production_without_guard_fails(ib, monkeypatch):
    monkeypatch.setenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
    with pytest.raises(SystemExit) as exc:
        ib.resolve_api_base()
    assert exc.value.code == 2


def test_production_with_category_b_passes(ib, monkeypatch):
    monkeypatch.setenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
    monkeypatch.setenv("KARZAR_ALLOW_PRODUCTION_WRITE", "1")
    monkeypatch.setenv("KARZAR_INGESTION_CATEGORY", "B")
    assert ib.resolve_api_base() == "https://api.karzartools.com/api/v1"


def test_production_allow_without_category_fails(ib, monkeypatch):
    monkeypatch.setenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
    monkeypatch.setenv("KARZAR_ALLOW_PRODUCTION_WRITE", "1")
    with pytest.raises(SystemExit) as exc:
        ib.resolve_api_base()
    assert exc.value.code == 2


def test_is_production_base(ib):
    assert ib.is_production_base("https://api.karzartools.com/api/v1")
    assert not ib.is_production_base("http://127.0.0.1:8000/api/v1")
