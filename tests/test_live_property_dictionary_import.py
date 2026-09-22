"""Governed LIVE Property Dictionary import gates (fail-closed)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.data_plane import (
    assert_category_b_production_write,
    assert_db_sentinel_matches_plane,
    assert_dictionary_seed_import_allowed,
    assert_live_db_sentinel,
    assert_live_dictionary_seed_import_allowed,
    validate_data_plane,
)
from app.services.property_dictionary_service import DEFAULT_SEED_PATH, file_checksum

ROOT = Path(__file__).resolve().parents[1]
LIVE_SCRIPT = ROOT / "scripts" / "seed_property_dictionary_live.py"


def _load_live_script():
    spec = importlib.util.spec_from_file_location("seed_property_dictionary_live", LIVE_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def live_mod():
    return _load_live_script()


def _live_identity(**overrides):
    kwargs = {
        "app_env": "staging",
        "data_plane_explicit": "live",
        "postgres_db": "karzar_staging",
        "postgres_server": "db",
        "media_plane": "live",
    }
    kwargs.update(overrides)
    return validate_data_plane(**kwargs)


# --- Identity ---


def test_live_known_db_full_auth_eligible():
    identity = _live_identity()
    assert identity.data_plane == "live"
    assert identity.inferred_data_plane is False
    assert_live_dictionary_seed_import_allowed(
        identity,
        sentinel_plane="live",
        allow_production_write="1",
        ingestion_category="B",
    )


def test_live_import_refuses_development_plane():
    identity = validate_data_plane(
        app_env="development",
        data_plane_explicit="development",
        postgres_db="karzar_db",
        postgres_server="127.0.0.1",
    )
    with pytest.raises(ValueError, match="must be 'live'"):
        assert_live_dictionary_seed_import_allowed(
            identity,
            sentinel_plane="live",
            allow_production_write="1",
            ingestion_category="B",
        )


def test_live_import_refuses_catalog_staging_plane():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="catalog_staging",
        postgres_db="karzar_catalog_staging",
        media_plane="catalog_staging",
    )
    with pytest.raises(ValueError, match="must be 'live'"):
        assert_live_dictionary_seed_import_allowed(
            identity,
            sentinel_plane="live",
            allow_production_write="1",
            ingestion_category="B",
        )


def test_live_import_refuses_unknown_db_name():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="live",
        postgres_db="some_other_db",
        media_plane="live",
    )
    with pytest.raises(ValueError, match="not a recognized LIVE database"):
        assert_live_dictionary_seed_import_allowed(
            identity,
            sentinel_plane="live",
            allow_production_write="1",
            ingestion_category="B",
        )


def test_live_import_refuses_inferred_live_plane():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit=None,
        postgres_db="karzar_staging",
        media_plane="live",
    )
    assert identity.data_plane == "live"
    assert identity.inferred_data_plane is True
    with pytest.raises(ValueError, match="explicitly"):
        assert_live_dictionary_seed_import_allowed(
            identity,
            sentinel_plane="live",
            allow_production_write="1",
            ingestion_category="B",
        )


def test_live_import_accepts_extra_denylist_live_db():
    identity = validate_data_plane(
        app_env="staging",
        data_plane_explicit="live",
        postgres_db="prod_catalog_2026",
        media_plane="live",
        extra_live_db_names="prod_catalog_2026",
    )
    assert_live_dictionary_seed_import_allowed(
        identity,
        sentinel_plane="live",
        allow_production_write="1",
        ingestion_category="B",
        extra_live_db_names="prod_catalog_2026",
    )


# --- Category B ---


def test_live_import_refuses_missing_category_b():
    identity = _live_identity()
    with pytest.raises(ValueError, match="KARZAR_INGESTION_CATEGORY=B"):
        assert_live_dictionary_seed_import_allowed(
            identity,
            sentinel_plane="live",
            allow_production_write="1",
            ingestion_category=None,
        )


def test_live_import_refuses_missing_production_write_flag():
    identity = _live_identity()
    with pytest.raises(ValueError, match="KARZAR_ALLOW_PRODUCTION_WRITE=1"):
        assert_live_dictionary_seed_import_allowed(
            identity,
            sentinel_plane="live",
            allow_production_write=None,
            ingestion_category="B",
        )


def test_category_b_helper_rejects_wrong_values():
    with pytest.raises(ValueError, match="Category B incomplete"):
        assert_category_b_production_write(
            allow_production_write="true",
            ingestion_category="b",
        )


# --- Sentinel ---


def test_live_sentinel_live_eligible():
    assert_live_db_sentinel(sentinel_plane="live")
    assert_db_sentinel_matches_plane(
        declared_plane="live",
        sentinel_plane="live",
        require_match=True,
    )


def test_live_sentinel_missing_refused():
    with pytest.raises(ValueError, match="missing/absent"):
        assert_live_db_sentinel(sentinel_plane=None)


def test_live_sentinel_catalog_staging_refused():
    with pytest.raises(ValueError, match="mismatch"):
        assert_live_db_sentinel(sentinel_plane="catalog_staging")


def test_require_match_false_still_skips_live_for_ordinary_helper():
    # Ordinary catalog helper: live declared does not require sentinel.
    assert_db_sentinel_matches_plane(
        declared_plane="live",
        sentinel_plane=None,
        require_match=False,
    )


# --- Checksum / operator refs (script helpers) ---


def test_checksum_mismatch_refused(live_mod):
    with pytest.raises(ValueError, match="seed SHA256 mismatch"):
        live_mod.assert_seed_sha_authorization(
            actual_sha256="aa" * 32,
            expected_sha256="bb" * 32,
            confirm_seed_sha256="aa" * 32,
        )


def test_confirmation_mismatch_refused(live_mod):
    sha = "cc" * 32
    with pytest.raises(ValueError, match="confirmation SHA256 mismatch"):
        live_mod.assert_seed_sha_authorization(
            actual_sha256=sha,
            expected_sha256=sha,
            confirm_seed_sha256="dd" * 32,
        )


def test_checksum_exact_match_passes(live_mod):
    sha = file_checksum(DEFAULT_SEED_PATH)
    live_mod.assert_seed_sha_authorization(
        actual_sha256=sha,
        expected_sha256=sha,
        confirm_seed_sha256=sha,
    )


def test_missing_backup_reference_refused(live_mod):
    with pytest.raises(ValueError, match="--backup-reference"):
        live_mod.assert_operator_references(
            backup_reference="",
            restore_drill_reference="drill-1",
        )


def test_missing_restore_drill_reference_refused(live_mod):
    with pytest.raises(ValueError, match="--restore-drill-reference"):
        live_mod.assert_operator_references(
            backup_reference="karzar_20260922_031501.sql.gz",
            restore_drill_reference=None,
        )


# --- Dry-run ---


def test_dry_run_seed_only_no_category_b_no_commit(live_mod):
    """Dry-run validates seed without Category B or DB mutation."""
    report = live_mod._seed_only_dry_run_report(DEFAULT_SEED_PATH)
    assert report["ok"] is True
    assert report["dry_run"] is True
    assert report["writes"] == 0
    assert report["units_scanned"] == 2
    assert report["properties_scanned"] == 9
    assert report["aliases_scanned"] == 36
    assert len(report["actual_sha256"]) == 64


def test_dry_run_cli_path_never_opens_mutate_session(live_mod):
    with patch("app.db.database.async_session_maker") as session_maker:
        code = asyncio.run(
            live_mod._run(
                seed=DEFAULT_SEED_PATH,
                dry_run=True,
                expected_sha256=None,
                confirm_seed_sha256=None,
                backup_reference=None,
                restore_drill_reference=None,
            )
        )
        assert code == 0
        session_maker.assert_not_called()


def test_import_failure_rolls_back(live_mod):
    sha = file_checksum(DEFAULT_SEED_PATH)
    session = MagicMock()
    session.rollback = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(first=MagicMock(return_value=("live",)))
    )

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)

    env = {
        "APP_ENV": "staging",
        "KARZAR_DATA_PLANE": "live",
        "KARZAR_MEDIA_PLANE": "live",
        "POSTGRES_DB": "karzar_staging",
        "POSTGRES_SERVER": "db",
        "KARZAR_ALLOW_PRODUCTION_WRITE": "1",
        "KARZAR_INGESTION_CATEGORY": "B",
    }
    with (
        patch.object(live_mod.os, "environ", env),
        patch("app.db.database.async_session_maker", return_value=cm),
        patch(
            "app.services.property_dictionary_service.import_property_dictionary",
            AsyncMock(side_effect=live_mod.PropertyDictionaryImportError("boom")),
        ),
    ):
        with pytest.raises(live_mod.PropertyDictionaryImportError, match="boom"):
            asyncio.run(
                live_mod._run_live_import(
                    seed=DEFAULT_SEED_PATH,
                    expected_sha256=sha,
                    confirm_seed_sha256=sha,
                    backup_reference="karzar_20260922_031501.sql.gz",
                    restore_drill_reference="restore-drill-reviewed-2026-09-22",
                )
            )
    session.rollback.assert_awaited()
    session.commit.assert_not_awaited()


# --- Ordinary importer regression (#364) ---


def test_ordinary_importer_still_refuses_live_db():
    identity = _live_identity()
    with pytest.raises(ValueError, match="classified as LIVE"):
        assert_dictionary_seed_import_allowed(identity, sentinel_plane="live")


def test_ordinary_importer_still_allows_development():
    identity = validate_data_plane(
        app_env="development",
        data_plane_explicit="development",
        postgres_db="karzar_db",
    )
    assert_dictionary_seed_import_allowed(identity, sentinel_plane=None)
