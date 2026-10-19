"""Alembic migration d2e3f4a5b6c7 — environment_identity staging plane."""

from __future__ import annotations

import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

MIGRATION = Path(__file__).resolve().parents[1] / (
    "alembic/versions/d2e3f4a5b6c7_application_staging_plane.py"
)


def test_migration_metadata_chain():
    src = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "d2e3f4a5b6c7"' in src
    assert 'down_revision = "c1d2e3f4a5b6"' in src
    assert re.search(r"\bINSERT\b", src, re.I) is None
    assert re.search(r"\bUPDATE\b", src, re.I) is None
    assert "'staging'" in src
    assert "plane = 'staging'" in src


def test_single_alembic_head_includes_application_staging():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert heads == ["d2e3f4a5b6c7"]


def test_downgrade_refuses_when_staging_plane_present():
    """Downgrade must not silently relabel staging sentinels (source contract)."""
    src = MIGRATION.read_text(encoding="utf-8")
    assert "plane = 'staging'" in src
    assert "Cannot downgrade" in src
    assert "RuntimeError" in src
