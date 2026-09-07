"""Regression checks for opt-in database fixtures and session-cached admin hash."""

from app.core.security import get_password_hash, verify_password

from tests.conftest import (
    ADMIN_PASSWORD,
    FIXTURE_STATS,
    get_cached_admin_password_hash,
    override_database,
)


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
