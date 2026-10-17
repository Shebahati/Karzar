"""Application-staging identity (250B) — validation, sentinel, import gates."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.core.data_plane import (
    assert_catalog_mutate_allowed,
    assert_db_sentinel_matches_plane,
    format_identity_report,
    infer_data_plane,
    validate_data_plane,
)
from pydantic import ValidationError


def _app_staging_identity(**overrides):
    base = {
        "app_env": "staging",
        "data_plane_explicit": "staging",
        "postgres_db": "karzar_app_staging",
        "postgres_server": "db",
        "media_plane": "staging",
    }
    base.update(overrides)
    return validate_data_plane(**base)


def test_explicit_app_staging_valid():
    identity = _app_staging_identity()
    assert identity.data_plane == "staging"
    assert identity.media_plane == "staging"
    assert identity.write_policy == "staging_writes_isolated"


def test_app_staging_media_inferred_when_unset():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="staging",
        postgres_db="karzar_app_staging",
        media_plane=None,
    )
    assert identity.media_plane == "staging"


def test_app_staging_live_db_refused():
    with pytest.raises(ValueError, match="cannot use a live database name"):
        _app_staging_identity(postgres_db="karzar_staging")


def test_app_staging_catalog_db_refused():
    with pytest.raises(ValueError, match="cannot use the catalog-staging database"):
        _app_staging_identity(postgres_db="karzar_catalog_staging")


def test_app_staging_wrong_db_refused():
    with pytest.raises(ValueError, match="requires POSTGRES_DB='karzar_app_staging'"):
        _app_staging_identity(postgres_db="something_else")


def test_app_staging_media_mismatch_refused():
    with pytest.raises(ValueError, match="KARZAR_MEDIA_PLANE must be 'staging'"):
        _app_staging_identity(media_plane="live")


def test_sentinel_staging_match():
    assert_db_sentinel_matches_plane(declared_plane="staging", sentinel_plane="staging")


def test_sentinel_staging_live_mismatch():
    with pytest.raises(ValueError, match="application-staging sentinel mismatch"):
        assert_db_sentinel_matches_plane(declared_plane="staging", sentinel_plane="live")


def test_sentinel_staging_catalog_mismatch():
    with pytest.raises(ValueError, match="application-staging sentinel mismatch"):
        assert_db_sentinel_matches_plane(
            declared_plane="staging", sentinel_plane="catalog_staging"
        )


def test_sentinel_staging_missing():
    with pytest.raises(ValueError, match="requires plane='staging'"):
        assert_db_sentinel_matches_plane(declared_plane="staging", sentinel_plane=None)


def test_cr011_legacy_inference_preserved():
    plane, inferred = infer_data_plane("staging", None)
    assert plane == "live"
    assert inferred is True
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit=None,
        postgres_db="karzar_staging",
    )
    assert identity.data_plane == "live"


def test_catalog_mutate_refused_on_app_staging_plane():
    identity = _app_staging_identity()
    with pytest.raises(ValueError, match="Catalog mutation refused"):
        assert_catalog_mutate_allowed(identity)


def test_format_identity_report_app_staging():
    identity = _app_staging_identity()
    report = format_identity_report(identity)
    assert "DB ENV:       staging" in report
    assert "DB NAME:      karzar_app_staging" in report
    assert "MEDIA ENV:    staging" in report
    assert "WRITE POLICY: staging_writes_isolated" in report


def test_settings_app_staging_allows_mock_console():
    Settings(
        _env_file=None,
        POSTGRES_USER="test",
        POSTGRES_PASSWORD="test",
        POSTGRES_SERVER="db",
        POSTGRES_DB="karzar_app_staging",
        SECRET_KEY="x" * 40,
        ADMIN_STEP_UP_PIN="9382746150",
        APP_ENV="staging",
        KARZAR_DATA_PLANE="staging",
        KARZAR_MEDIA_PLANE="staging",
        DEBUG=False,
        REDIS_HOST="redis",
        OTP_DEV_ECHO=False,
        CORS_ORIGINS="http://127.0.0.1:8020",
        PAYMENT_PROVIDER="mock",
        SMS_PROVIDER="console",
    )


def test_production_with_staging_plane_refused():
    with pytest.raises(ValidationError, match="APP_ENV=production requires KARZAR_DATA_PLANE=live"):
        Settings(
            _env_file=None,
            POSTGRES_USER="test",
            POSTGRES_PASSWORD="test",
            POSTGRES_SERVER="db",
            POSTGRES_DB="karzar_app_staging",
            SECRET_KEY="x" * 40,
            ADMIN_STEP_UP_PIN="9382746150",
            APP_ENV="production",
            KARZAR_DATA_PLANE="staging",
            KARZAR_MEDIA_PLANE="staging",
            DEBUG=False,
            REDIS_HOST="redis",
            TRUSTED_HOSTS="api.example.com",
            ENFORCE_HTTPS=True,
            ENABLE_API_DOCS=False,
            PAYMENT_PROVIDER="mock",
            SMS_PROVIDER="console",
        )
