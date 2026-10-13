"""Alembic migration d2e3f4a5b6c7 — environment_identity staging plane."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
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


@pytest.mark.skipif(
    not __import__("os").environ.get("USE_POSTGRES_TESTS"),
    reason="Postgres migration integration requires USE_POSTGRES_TESTS=1",
)
def test_upgrade_downgrade_staging_plane_constraint():
    import os

    url = (
        f"postgresql://{os.environ['POSTGRES_USER']}:"
        f"{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_SERVER']}:"
        f"{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS environment_identity (
                    id INTEGER PRIMARY KEY,
                    plane VARCHAR(32) NOT NULL,
                    label VARCHAR(64) NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
                    CONSTRAINT ck_environment_identity_singleton CHECK (id = 1),
                    CONSTRAINT ck_environment_identity_plane CHECK (
                        plane IN ('live', 'catalog_staging', 'development')
                    )
                )
                """
            )
        )
        conn.execute(sa.text("DELETE FROM environment_identity"))
        conn.execute(
            sa.text(
                "INSERT INTO environment_identity (id, plane, label) VALUES (1, 'live', 'test-live')"
            )
        )
        conn.commit()

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url.replace("+asyncpg", ""))
    command.upgrade(cfg, "d2e3f4a5b6c7")
    with engine.connect() as conn:
        plane = conn.execute(
            sa.text("SELECT plane FROM environment_identity WHERE id = 1")
        ).scalar()
        assert plane == "live"
        conn.execute(
            sa.text(
                "UPDATE environment_identity SET plane = 'staging', label = 'app' WHERE id = 1"
            )
        )
        conn.commit()
    with pytest.raises(RuntimeError, match="Cannot downgrade"):
        command.downgrade(cfg, "c1d2e3f4a5b6")
    with engine.connect() as conn:
        conn.execute(
            sa.text(
                "UPDATE environment_identity SET plane = 'live', label = 'test-live' WHERE id = 1"
            )
        )
        conn.commit()
    command.downgrade(cfg, "c1d2e3f4a5b6")
    command.upgrade(cfg, "d2e3f4a5b6c7")
