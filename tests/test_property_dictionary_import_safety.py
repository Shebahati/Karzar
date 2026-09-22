"""Property Dictionary importer data-plane / sentinel safety (P1 readiness)."""

from __future__ import annotations

import pytest
from app.core.data_plane import (
    assert_dictionary_seed_import_allowed,
    identity_from_mapping,
    validate_data_plane,
)


def test_development_identity_allows_dictionary_import():
    identity = validate_data_plane(
        app_env="development",
        data_plane_explicit="development",
        postgres_db="karzar_db",
        postgres_server="127.0.0.1",
    )
    assert_dictionary_seed_import_allowed(identity, sentinel_plane=None)


def test_catalog_staging_with_matching_sentinel_allows():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="catalog_staging",
        postgres_db="karzar_catalog_staging",
        media_plane="catalog_staging",
    )
    assert_dictionary_seed_import_allowed(
        identity, sentinel_plane="catalog_staging"
    )


def test_catalog_staging_sentinel_mismatch_refused():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="catalog_staging",
        postgres_db="karzar_catalog_staging",
        media_plane="catalog_staging",
    )
    with pytest.raises(ValueError, match="marker mismatch"):
        assert_dictionary_seed_import_allowed(identity, sentinel_plane="live")


def test_catalog_staging_missing_sentinel_refused():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="catalog_staging",
        postgres_db="karzar_catalog_staging",
        media_plane="catalog_staging",
    )
    with pytest.raises(ValueError, match="marker mismatch"):
        assert_dictionary_seed_import_allowed(identity, sentinel_plane=None)


def test_historic_live_db_trap_refuses_non_dry_run_import():
    """APP_ENV=staging + POSTGRES_DB=karzar_staging resolves to live → refuse."""
    identity = identity_from_mapping(
        {
            "APP_ENV": "staging",
            "POSTGRES_DB": "karzar_staging",
            "POSTGRES_SERVER": "db",
        }
    )
    assert identity.data_plane == "live"
    with pytest.raises(ValueError, match="classified as LIVE"):
        assert_dictionary_seed_import_allowed(identity, sentinel_plane=None)


def test_explicit_live_plane_refused():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="live",
        postgres_db="karzar_staging",
        media_plane="live",
    )
    with pytest.raises(ValueError, match="classified as LIVE"):
        assert_dictionary_seed_import_allowed(identity, sentinel_plane="live")


def test_development_plane_with_live_db_name_refused():
    """Declared development must not mutate CR-011 live DB name."""
    identity = validate_data_plane(
        app_env="development",
        data_plane_explicit="development",
        postgres_db="karzar_staging",
        postgres_server="127.0.0.1",
    )
    assert identity.data_plane == "development"
    with pytest.raises(ValueError, match="classified as LIVE"):
        assert_dictionary_seed_import_allowed(identity, sentinel_plane=None)


def test_inferred_development_with_live_db_name_refused():
    """APP_ENV=development + unset KARZAR_DATA_PLANE + karzar_staging → refuse."""
    identity = identity_from_mapping(
        {
            "APP_ENV": "development",
            "POSTGRES_DB": "karzar_staging",
            "POSTGRES_SERVER": "127.0.0.1",
        }
    )
    assert identity.data_plane == "development"
    with pytest.raises(ValueError, match="classified as LIVE"):
        assert_dictionary_seed_import_allowed(identity, sentinel_plane=None)


def test_extra_live_denylist_refuses_named_db():
    identity = validate_data_plane(
        app_env="development",
        data_plane_explicit="development",
        postgres_db="prod_catalog_2026",
        postgres_server="127.0.0.1",
    )
    assert identity.data_plane == "development"
    with pytest.raises(ValueError, match="classified as LIVE"):
        assert_dictionary_seed_import_allowed(
            identity,
            sentinel_plane=None,
            extra_live_db_names="prod_catalog_2026",
        )
