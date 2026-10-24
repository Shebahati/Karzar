"""Full Alembic graph checks on disposable PostgreSQL (not karzar_ci / live)."""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from app.services.alembic_revision_compat import get_alembic_script_directory

from tests.conftest import USE_POSTGRES_TESTS
from tests.migration_disposable_db import connect_disposable, disposable_migration_database

requires_postgres = pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL")

REPO_ROOT = Path(__file__).resolve().parents[1]


def _alembic_env(db_name: str) -> dict[str, str]:
    env = os.environ.copy()
    env["POSTGRES_DB"] = db_name
    env.setdefault("APP_ENV", "development")
    env.setdefault("KARZAR_DATA_PLANE", "development")
    env.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    return env


def _run_alembic(db_name: str, *args: str) -> None:
    subprocess.run(
        ["alembic", *args],
        cwd=REPO_ROOT,
        env=_alembic_env(db_name),
        check=True,
        capture_output=True,
        text=True,
    )


def test_alembic_single_head_is_brand_bulk_pricing():
    heads = get_alembic_script_directory().get_heads()
    assert heads == ["a1b2c3d4e5f6"]


@requires_postgres
def test_c1_drift_upgrade_to_head_creates_bestseller_without_seeding():
    """
    Synthetic c1 + manual logo_url drift → upgrade head.

    Restored-backup migration drill on live remains a separate owner release gate.
    """
    slug = f"u6-int-{uuid.uuid4().hex[:8]}"
    logo = "/uploads/brands/integration-u6.webp"
    with disposable_migration_database() as db_name:

        async def assert_after() -> None:
            conn = await connect_disposable(db_name)
            try:
                rev = await conn.fetchval("SELECT version_num FROM alembic_version")
                assert rev == "a3f410b5c6d7"
                preserved = await conn.fetchval(
                    "SELECT logo_url FROM brands WHERE slug = $1",
                    slug,
                )
                assert preserved == logo
                exists = await conn.fetchval(
                    "SELECT to_regclass('public.home_bestseller_selection')",
                )
                assert exists is not None
                count = await conn.fetchval("SELECT COUNT(*) FROM home_bestseller_selection")
                assert count == 0
            finally:
                await conn.close()

        _run_alembic(db_name, "upgrade", "c1d2e3f4a5b6")

        async def seed_drift() -> None:
            conn = await connect_disposable(db_name)
            try:
                await conn.execute(
                    "ALTER TABLE brands ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)",
                )
                await conn.execute(
                    "INSERT INTO brands (name, slug, country, logo_url) "
                    "VALUES ($1, $2, 'IR', $3)",
                    "Integration",
                    slug,
                    logo,
                )
            finally:
                await conn.close()

        asyncio.run(seed_drift())
        _run_alembic(db_name, "upgrade", "head")
        asyncio.run(assert_after())
