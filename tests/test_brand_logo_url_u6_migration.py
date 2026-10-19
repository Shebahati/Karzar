"""u6v7w8x9y0z1 brands.logo_url drift guard — disposable PostgreSQL only."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

_ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"
if str(_ALEMBIC_DIR) not in sys.path:
    sys.path.insert(0, str(_ALEMBIC_DIR))

from brand_logo_url_guard import (  # noqa: E402
    BrandLogoUrlSchemaError,
    LogoUrlColumnSpec,
    assert_logo_url_compatible,
    column_spec_from_inspector,
    downgrade_brands_logo_url,
    upgrade_brands_logo_url,
)
from tests.conftest import USE_POSTGRES_TESTS

requires_postgres = pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL")


def _sync_url() -> str:
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ["POSTGRES_SERVER"]
    port = os.environ["POSTGRES_PORT"]
    db = os.environ["POSTGRES_DB"]
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def _with_ops(conn, fn) -> None:
    ctx = MigrationContext.configure(conn)
    with Operations.context(ctx):
        fn()


def _create_brand(conn, slug: str, logo: str | None) -> None:
    conn.execute(
        text(
            "INSERT INTO brands (name, slug, country, logo_url) "
            "VALUES (:name, :slug, 'IR', :logo)",
        ),
        {"name": f"U6 Test {slug}", "slug": slug, "logo": logo},
    )


def test_assert_compatible_accepts_expected_spec():
    spec = LogoUrlColumnSpec(nullable=True, varchar_length=500, has_server_default=False)
    assert_logo_url_compatible(spec)


def test_assert_compatible_rejects_short_varchar():
    spec = LogoUrlColumnSpec(nullable=True, varchar_length=100, has_server_default=False)
    with pytest.raises(BrandLogoUrlSchemaError, match="VARCHAR\\(500\\)"):
        assert_logo_url_compatible(spec)


def test_assert_compatible_rejects_not_nullable():
    spec = LogoUrlColumnSpec(nullable=False, varchar_length=500, has_server_default=False)
    with pytest.raises(BrandLogoUrlSchemaError, match="nullable"):
        assert_logo_url_compatible(spec)


def test_column_spec_from_inspector_varchar_500():
    col = {"type": sa.String(length=500), "nullable": True, "default": None}
    spec = column_spec_from_inspector(col)
    assert spec.varchar_length == 500
    assert spec.nullable is True


def test_column_spec_from_inspector_rejects_non_string():
    col = {"type": sa.Integer(), "nullable": True, "default": None}
    with pytest.raises(BrandLogoUrlSchemaError, match="VARCHAR"):
        column_spec_from_inspector(col)


@requires_postgres
def test_upgrade_preserves_existing_compatible_values():
    engine = create_engine(_sync_url())
    slug = f"u6-test-keep-{uuid.uuid4().hex[:8]}"
    logo = "/uploads/brands/synthetic-u6.webp"
    with engine.begin() as conn:
        cols = {c["name"] for c in inspect(conn).get_columns("brands")}
        assert "logo_url" in cols, "CI schema must include brands.logo_url for drift simulation"
        _create_brand(conn, slug, logo)
        before = conn.execute(
            text("SELECT logo_url FROM brands WHERE slug = :slug"),
            {"slug": slug},
        ).scalar()
        _with_ops(conn, upgrade_brands_logo_url)
        after = conn.execute(
            text("SELECT logo_url FROM brands WHERE slug = :slug"),
            {"slug": slug},
        ).scalar()
    assert before == logo
    assert after == logo


@requires_postgres
def test_downgrade_preserves_non_null_logos():
    engine = create_engine(_sync_url())
    slug = f"u6-test-down-{uuid.uuid4().hex[:8]}"
    logo = "/uploads/brands/downgrade-u6.webp"
    with engine.begin() as conn:
        _create_brand(conn, slug, logo)
        _with_ops(conn, upgrade_brands_logo_url)
        _with_ops(conn, downgrade_brands_logo_url)
        after = conn.execute(
            text("SELECT logo_url FROM brands WHERE slug = :slug"),
            {"slug": slug},
        ).scalar()
    assert after == logo


@requires_postgres
def test_upgrade_adds_column_when_missing(monkeypatch):
    import brand_logo_url_guard as guard

    engine = create_engine(_sync_url(), isolation_level="AUTOCOMMIT")
    table = f"brands_u6_isolated_{uuid.uuid4().hex[:10]}"
    monkeypatch.setattr(guard, "TABLE_NAME", table)
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                CREATE TABLE {table} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                )
                """,
            ),
        )
        _with_ops(conn, upgrade_brands_logo_url)
        cols = {c["name"] for c in inspect(conn).get_columns(table)}
        assert "logo_url" in cols
        conn.execute(text(f"DROP TABLE {table}"))


@requires_postgres
def test_downgrade_drops_column_when_all_null(monkeypatch):
    import brand_logo_url_guard as guard

    engine = create_engine(_sync_url(), isolation_level="AUTOCOMMIT")
    table = f"brands_u6_isolated_{uuid.uuid4().hex[:10]}"
    monkeypatch.setattr(guard, "TABLE_NAME", table)
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                CREATE TABLE {table} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                )
                """,
            ),
        )
        _with_ops(conn, upgrade_brands_logo_url)
        _with_ops(conn, downgrade_brands_logo_url)
        cols = {c["name"] for c in inspect(conn).get_columns(table)}
        assert "logo_url" not in cols
        conn.execute(text(f"DROP TABLE {table}"))
