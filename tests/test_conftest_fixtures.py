"""Regression checks for opt-in database fixtures and session-cached admin hash."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from app.core.security import get_password_hash, verify_password
from app.db.models.product import Brand, Category
from app.db.models.user import User, UserRole
from sqlalchemy import func, select, text

from tests.conftest import (
    ADMIN_PASSWORD,
    ADMIN_PHONE,
    FIXTURE_STATS,
    TestingSessionLocal,
    get_cached_admin_password_hash,
    override_database,
)

SENTINEL_SLUG = "fixture-isolation-sentinel-brand"


def test_override_database_fixture_is_not_autouse():
    fixture_def = override_database._pytestfixturefunction
    assert fixture_def.autouse is False
    assert fixture_def.scope == "function"


def test_pure_regression_does_not_request_database_fixture(request):
    assert "override_database" not in request.fixturenames
    before_setups = FIXTURE_STATS["database_setups"]
    before_resets = FIXTURE_STATS["table_resets"]
    assert FIXTURE_STATS["database_setups"] == before_setups
    assert FIXTURE_STATS["table_resets"] == before_resets


def test_admin_password_hash_is_session_cached_and_really_verified():
    first = get_cached_admin_password_hash()
    hashes_after_first = FIXTURE_STATS["password_hashes"]
    second = get_cached_admin_password_hash()
    third = get_cached_admin_password_hash()

    assert first == second == third
    assert first.startswith("$2b$")
    assert FIXTURE_STATS["password_hashes"] == hashes_after_first
    assert hashes_after_first >= 1
    assert verify_password(ADMIN_PASSWORD, first) is True
    assert verify_password("wrong-password", first) is False
    # Production hasher still produces a distinct fresh salt when called directly.
    fresh = get_password_hash(ADMIN_PASSWORD)
    assert fresh != first
    assert verify_password(ADMIN_PASSWORD, fresh) is True


def test_database_fixture_increments_setup_counter_once_per_request(override_database):
    assert FIXTURE_STATS["database_setups"] >= 1
    assert FIXTURE_STATS["table_resets"] >= 1
    assert FIXTURE_STATS["password_hashes"] == 1
    assert verify_password(ADMIN_PASSWORD, get_cached_admin_password_hash()) is True


@pytest.mark.usefixtures("override_database")
def test_db_isolation_01_write_sentinel_and_mutate_seed():
    """First DB test in this pair leaves rows that the next test must not see."""

    async def body() -> None:
        async with TestingSessionLocal() as session:
            session.add(
                Brand(name="Sentinel Brand", country="XX", slug=SENTINEL_SLUG)
            )
            seed = (
                await session.execute(select(Brand).where(Brand.id == 1))
            ).scalar_one()
            seed.name = "MUTATED-SEED-BRAND"
            await session.commit()

            sentinel = (
                await session.execute(
                    select(Brand).where(Brand.slug == SENTINEL_SLUG)
                )
            ).scalar_one()
            assert sentinel.id > 1
            mutated = (
                await session.execute(select(Brand).where(Brand.id == 1))
            ).scalar_one()
            assert mutated.name == "MUTATED-SEED-BRAND"

    asyncio.run(body())


@pytest.mark.usefixtures("override_database")
def test_db_isolation_02_schema_alive_and_seed_restored():
    """Second DB test: schema still exists, sentinel gone, seed IDs restored."""

    async def body() -> None:
        async with TestingSessionLocal() as session:
            # Schema must still be present after the previous fixture teardown.
            table_probe = await session.execute(text("SELECT COUNT(*) FROM brands"))
            assert table_probe.scalar_one() >= 1

            sentinel_count = (
                await session.execute(
                    select(func.count()).select_from(Brand).where(Brand.slug == SENTINEL_SLUG)
                )
            ).scalar_one()
            assert sentinel_count == 0

            brand = (
                await session.execute(select(Brand).where(Brand.id == 1))
            ).scalar_one()
            assert brand.name == "TestBrand"
            assert brand.slug == "testbrand"

            leaf = (
                await session.execute(select(Category).where(Category.id == 3))
            ).scalar_one()
            assert leaf.slug == "0-150mm-range"
            assert leaf.parent_id == 2

            admin = (
                await session.execute(
                    select(User).where(User.phone_number == ADMIN_PHONE)
                )
            ).scalar_one()
            assert admin.role == UserRole.SUPER_ADMIN
            assert admin.id == 1

    asyncio.run(body())


def _sqlite_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["USE_POSTGRES_TESTS"] = "0"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    env.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    env.setdefault("ADMIN_STEP_UP_PIN", "93827461")
    env.setdefault("DEBUG", "true")
    env["ENABLE_API_DOCS"] = "false"
    env["ALLOW_PUBLIC_REGISTER"] = "true"
    env["OTP_DEV_ECHO"] = "true"
    return env


def test_sqlite_session_survives_two_db_tests_in_one_process():
    """Hard gate: consecutive SQLite DB fixtures must not destroy :memory: schema."""
    suite = Path(__file__).resolve().parent / "_sqlite_lifecycle_ok_probe.py"
    suite.write_text(
        textwrap.dedent(
            """\
            import asyncio
            import pytest
            from app.db.models.product import Brand
            from sqlalchemy import select, text
            from tests.conftest import TestingSessionLocal

            SENTINEL = "subprocess-ok-sentinel"

            @pytest.mark.usefixtures("override_database")
            def test_a_write_sentinel():
                async def body():
                    async with TestingSessionLocal() as session:
                        session.add(Brand(name="S", country="XX", slug=SENTINEL))
                        await session.commit()
                asyncio.run(body())

            @pytest.mark.usefixtures("override_database")
            def test_b_schema_and_isolation():
                async def body():
                    async with TestingSessionLocal() as session:
                        await session.execute(text("SELECT 1 FROM brands LIMIT 1"))
                        rows = (
                            await session.execute(
                                select(Brand).where(Brand.slug == SENTINEL)
                            )
                        ).scalars().all()
                        assert rows == []
                        seed = (
                            await session.execute(select(Brand).where(Brand.id == 1))
                        ).scalar_one()
                        assert seed.slug == "testbrand"
                asyncio.run(body())
            """
        )
    )
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--tb=short",
                str(suite),
            ],
            cwd=str(Path(__file__).resolve().parents[1]),
            env=_sqlite_subprocess_env(),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        suite.unlink(missing_ok=True)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "no such table" not in (result.stdout + result.stderr).lower()
    assert "2 passed" in result.stdout


def test_sqlite_isolation_after_intentional_db_test_failure():
    """Failed DB test must still leave overrides cleared and schema reusable."""
    suite = Path(__file__).resolve().parent / "_sqlite_lifecycle_fail_probe.py"
    suite.write_text(
        textwrap.dedent(
            """\
            import asyncio
            import pytest
            from app.db.database import get_db
            from app.db.models.product import Brand
            from app.main import app
            from sqlalchemy import select, text
            from tests.conftest import TestingSessionLocal

            SENTINEL = "subprocess-fail-sentinel"

            @pytest.mark.usefixtures("override_database")
            def test_a_mutate_then_fail():
                async def body():
                    async with TestingSessionLocal() as session:
                        session.add(Brand(name="S", country="XX", slug=SENTINEL))
                        seed = (
                            await session.execute(select(Brand).where(Brand.id == 1))
                        ).scalar_one()
                        seed.name = "BROKEN"
                        await session.commit()
                asyncio.run(body())
                raise AssertionError("intentional failure after DB mutation")

            @pytest.mark.usefixtures("override_database")
            def test_b_after_failure_is_clean():
                async def body():
                    async with TestingSessionLocal() as session:
                        await session.execute(text("SELECT COUNT(*) FROM brands"))
                        leaked = (
                            await session.execute(
                                select(Brand).where(Brand.slug == SENTINEL)
                            )
                        ).scalars().all()
                        assert leaked == []
                        seed = (
                            await session.execute(select(Brand).where(Brand.id == 1))
                        ).scalar_one()
                        assert seed.name == "TestBrand"
                        assert seed.slug == "testbrand"
                asyncio.run(body())

            def test_c_overrides_cleared_without_db_fixture():
                assert get_db not in app.dependency_overrides
            """
        )
    )
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-v",
                "--tb=line",
                str(suite),
            ],
            cwd=str(Path(__file__).resolve().parents[1]),
            env=_sqlite_subprocess_env(),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        suite.unlink(missing_ok=True)
    combined = result.stdout + "\n" + result.stderr
    assert "test_a_mutate_then_fail FAILED" in combined
    assert "test_b_after_failure_is_clean PASSED" in combined
    assert "test_c_overrides_cleared_without_db_fixture PASSED" in combined
    assert "no such table" not in combined.lower()
    assert "intentional failure after DB mutation" in combined
    # Outer harness succeeds: the intentional inner failure is expected.
    assert result.returncode != 0
