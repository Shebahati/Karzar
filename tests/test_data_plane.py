"""Unit tests for app.core.data_plane fail-closed isolation."""

from __future__ import annotations

import pytest
from app.core.data_plane import (
    assert_catalog_mutate_allowed,
    infer_data_plane,
    validate_data_plane,
)


def test_infer_staging_defaults_to_live():
    plane, inferred = infer_data_plane("staging", None)
    assert plane == "live"
    assert inferred is True


def test_infer_development_defaults():
    plane, inferred = infer_data_plane("development", None)
    assert plane == "development"
    assert inferred is True


def test_explicit_catalog_staging_with_matching_db_allows():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="catalog_staging",
        postgres_db="karzar_catalog_staging",
        postgres_server="db",
        media_plane="catalog_staging",
    )
    assert identity.data_plane == "catalog_staging"
    assert identity.postgres_db == "karzar_catalog_staging"
    assert_catalog_mutate_allowed(identity)


def test_app_env_staging_plus_live_db_plus_catalog_plane_fails():
    """Threat class: APP_ENV=staging + production/live DATABASE + claimed staging plane."""
    with pytest.raises(ValueError, match="cannot use a live database name"):
        validate_data_plane(
            app_env="staging",
            data_plane_explicit="catalog_staging",
            postgres_db="karzar_staging",
            media_plane="catalog_staging",
        )


def test_catalog_staging_wrong_db_name_fails():
    with pytest.raises(ValueError, match="requires POSTGRES_DB"):
        validate_data_plane(
            app_env="staging",
            data_plane_explicit="catalog_staging",
            postgres_db="something_else",
            media_plane="catalog_staging",
        )


def test_live_plane_with_historic_live_db_allows_start():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="live",
        postgres_db="karzar_staging",
        media_plane="live",
    )
    assert identity.data_plane == "live"
    with pytest.raises(ValueError, match="Catalog mutation refused"):
        assert_catalog_mutate_allowed(identity)


def test_live_mutate_allowed_with_confirmation():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit=None,
        postgres_db="karzar_staging",
    )
    assert identity.data_plane == "live"
    assert_catalog_mutate_allowed(identity, allow_live_catalog_writes=True)


def test_media_plane_mismatch_fails():
    with pytest.raises(ValueError, match="KARZAR_MEDIA_PLANE"):
        validate_data_plane(
            app_env="staging",
            data_plane_explicit="catalog_staging",
            postgres_db="karzar_catalog_staging",
            media_plane="live",
        )


def test_sentinel_mismatch_fails_for_catalog_staging():
    from app.core.data_plane import assert_db_sentinel_matches_plane

    with pytest.raises(ValueError, match="marker mismatch"):
        assert_db_sentinel_matches_plane(
            declared_plane="catalog_staging",
            sentinel_plane="live",
        )


def test_sentinel_match_allows_catalog_staging():
    from app.core.data_plane import assert_db_sentinel_matches_plane

    assert_db_sentinel_matches_plane(
        declared_plane="catalog_staging",
        sentinel_plane="catalog_staging",
    )


def test_live_declared_skips_staging_sentinel_requirement():
    from app.core.data_plane import assert_db_sentinel_matches_plane

    assert_db_sentinel_matches_plane(declared_plane="live", sentinel_plane="live")
    assert_db_sentinel_matches_plane(declared_plane="live", sentinel_plane=None)


def test_production_mutate_without_authorization_fails():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="live",
        postgres_db="karzar_staging",
        media_plane="live",
    )
    with pytest.raises(ValueError, match="Catalog mutation refused"):
        assert_catalog_mutate_allowed(identity, allow_live_catalog_writes=False)
