"""u6v7w8x9y0z1 brands.logo_url drift guard — disposable PostgreSQL only."""

from __future__ import annotations

import asyncio
import importlib.util
import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.conftest import USE_POSTGRES_TESTS
from tests.migration_disposable_db import connect_disposable, disposable_migration_database

requires_postgres = pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL")


def _load_guard():
    path = Path(__file__).resolve().parents[1] / "alembic" / "brand_logo_url_guard.py"
    spec = importlib.util.spec_from_file_location("brand_logo_url_guard", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _async_url(db_name: str) -> str:
    return (
        f"postgresql+asyncpg://{os.environ['POSTGRES_USER']}:"
        f"{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_SERVER']}:"
        f"{os.environ['POSTGRES_PORT']}/{db_name}"
    )


def _with_ops(sync_conn, fn) -> None:
    ctx = MigrationContext.configure(sync_conn)
    with Operations.context(ctx):
        fn()


async def _run_guard_op(db_name: str, fn) -> None:
    engine = create_async_engine(_async_url(db_name), poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: _with_ops(sync_conn, fn))
    finally:
        await engine.dispose()


def test_assert_compatible_accepts_expected_spec():
    guard = _load_guard()
    spec = guard.LogoUrlColumnSpec(nullable=True, varchar_length=500, has_server_default=False)
    guard.assert_logo_url_compatible(spec)


def test_assert_compatible_rejects_short_varchar():
    guard = _load_guard()
    spec = guard.LogoUrlColumnSpec(nullable=True, varchar_length=100, has_server_default=False)
    with pytest.raises(guard.BrandLogoUrlSchemaError, match="VARCHAR\\(500\\)"):
        guard.assert_logo_url_compatible(spec)


def test_assert_compatible_rejects_not_nullable():
    guard = _load_guard()
    spec = guard.LogoUrlColumnSpec(nullable=False, varchar_length=500, has_server_default=False)
    with pytest.raises(guard.BrandLogoUrlSchemaError, match="nullable"):
        guard.assert_logo_url_compatible(spec)


def test_column_spec_from_inspector_varchar_500():
    guard = _load_guard()
    col = {"type": sa.String(length=500), "nullable": True, "default": None}
    spec = guard.column_spec_from_inspector(col)
    assert spec.varchar_length == 500
    assert spec.nullable is True


def test_column_spec_from_inspector_rejects_non_string():
    guard = _load_guard()
    col = {"type": sa.Integer(), "nullable": True, "default": None}
    with pytest.raises(guard.BrandLogoUrlSchemaError, match="VARCHAR"):
        guard.column_spec_from_inspector(col)


@requires_postgres
def test_upgrade_adds_column_when_missing(monkeypatch):
    guard = _load_guard()
    with disposable_migration_database() as db_name:
        table = f"brands_u6_isolated_{uuid.uuid4().hex[:10]}"
        monkeypatch.setattr(guard, "TABLE_NAME", table)

        async def work() -> None:
            conn = await connect_disposable(db_name)
            try:
                await conn.execute(
                    f"""
                    CREATE TABLE {table} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL
                    )
                    """,
                )
                await _run_guard_op(db_name, guard.upgrade_brands_logo_url)
                row = await conn.fetchrow(
                    """
                    SELECT character_maximum_length, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = $1 AND column_name = 'logo_url'
                    """,
                    table,
                )
                assert row is not None
                assert row["character_maximum_length"] == 500
                assert row["is_nullable"] == "YES"
            finally:
                await conn.execute(f"DROP TABLE IF EXISTS {table}")
                await conn.close()

        asyncio.run(work())


@requires_postgres
def test_upgrade_preserves_existing_compatible_values(monkeypatch):
    guard = _load_guard()
    with disposable_migration_database() as db_name:
        table = f"brands_u6_isolated_{uuid.uuid4().hex[:10]}"
        slug = f"u6-keep-{uuid.uuid4().hex[:8]}"
        logo = "/uploads/brands/synthetic-u6.webp"
        monkeypatch.setattr(guard, "TABLE_NAME", table)

        async def work() -> None:
            conn = await connect_disposable(db_name)
            try:
                await conn.execute(
                    f"""
                    CREATE TABLE {table} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        slug VARCHAR(255) NOT NULL,
                        logo_url VARCHAR(500)
                    )
                    """,
                )
                await conn.execute(
                    f"INSERT INTO {table} (name, slug, logo_url) VALUES ($1, $2, $3)",
                    "Synthetic",
                    slug,
                    logo,
                )
                await _run_guard_op(db_name, guard.upgrade_brands_logo_url)
                after = await conn.fetchval(f"SELECT logo_url FROM {table} WHERE slug = $1", slug)
                assert after == logo
            finally:
                await conn.execute(f"DROP TABLE IF EXISTS {table}")
                await conn.close()

        asyncio.run(work())


@requires_postgres
def test_upgrade_refuses_incompatible_column(monkeypatch):
    guard = _load_guard()
    with disposable_migration_database() as db_name:
        table = f"brands_u6_isolated_{uuid.uuid4().hex[:10]}"
        monkeypatch.setattr(guard, "TABLE_NAME", table)

        async def work() -> None:
            conn = await connect_disposable(db_name)
            try:
                await conn.execute(
                    f"""
                    CREATE TABLE {table} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        logo_url VARCHAR(100)
                    )
                    """,
                )
                with pytest.raises(guard.BrandLogoUrlSchemaError):
                    await _run_guard_op(db_name, guard.upgrade_brands_logo_url)
            finally:
                await conn.execute(f"DROP TABLE IF EXISTS {table}")
                await conn.close()

        asyncio.run(work())


@requires_postgres
def test_downgrade_refuses_when_column_exists(monkeypatch):
    guard = _load_guard()
    with disposable_migration_database() as db_name:
        table = f"brands_u6_isolated_{uuid.uuid4().hex[:10]}"
        monkeypatch.setattr(guard, "TABLE_NAME", table)

        async def work() -> None:
            conn = await connect_disposable(db_name)
            try:
                await conn.execute(
                    f"""
                    CREATE TABLE {table} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        logo_url VARCHAR(500)
                    )
                    """,
                )
                with pytest.raises(guard.BrandLogoUrlDowngradeRefused):
                    await _run_guard_op(db_name, guard.downgrade_brands_logo_url)
            finally:
                await conn.execute(f"DROP TABLE IF EXISTS {table}")
                await conn.close()

        asyncio.run(work())


@requires_postgres
def test_downgrade_refuses_when_column_exists_all_null(monkeypatch):
    guard = _load_guard()
    with disposable_migration_database() as db_name:
        table = f"brands_u6_isolated_{uuid.uuid4().hex[:10]}"
        monkeypatch.setattr(guard, "TABLE_NAME", table)

        async def work() -> None:
            conn = await connect_disposable(db_name)
            try:
                await conn.execute(
                    f"""
                    CREATE TABLE {table} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        logo_url VARCHAR(500)
                    )
                    """,
                )
                await conn.execute(f"INSERT INTO {table} (name, logo_url) VALUES ('x', NULL)")
                with pytest.raises(guard.BrandLogoUrlDowngradeRefused):
                    await _run_guard_op(db_name, guard.downgrade_brands_logo_url)
            finally:
                await conn.execute(f"DROP TABLE IF EXISTS {table}")
                await conn.close()

        asyncio.run(work())


@requires_postgres
def test_downgrade_noop_when_column_missing(monkeypatch):
    guard = _load_guard()
    with disposable_migration_database() as db_name:
        table = f"brands_u6_isolated_{uuid.uuid4().hex[:10]}"
        monkeypatch.setattr(guard, "TABLE_NAME", table)

        async def work() -> None:
            conn = await connect_disposable(db_name)
            try:
                await conn.execute(
                    f"""
                    CREATE TABLE {table} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL
                    )
                    """,
                )
                await _run_guard_op(db_name, guard.downgrade_brands_logo_url)
                row = await conn.fetchrow(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = $1 AND column_name = 'logo_url'
                    """,
                    table,
                )
                assert row is None
            finally:
                await conn.execute(f"DROP TABLE IF EXISTS {table}")
                await conn.close()

        asyncio.run(work())
