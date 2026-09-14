"""Settings bootstrap: manual_portal requires receiver_due without global settings."""

from __future__ import annotations

import subprocess
import sys

import pytest
from app.core.config import Settings
from app.services.logistics.shipping_payment import (
    ShippingPaymentMode,
    effective_shipping_payment_mode,
)
from pydantic import ValidationError


def _settings(**overrides) -> Settings:
    values = {
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_DB": "test",
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "ADMIN_STEP_UP_PIN": "93827461",
        "DEBUG": True,
        "REDIS_HOST": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_effective_mode_explicit_receiver_due():
    assert (
        effective_shipping_payment_mode(
            postex_shipping_payment_mode="receiver_due",
            postex_default_payment_type="SENDER",
        )
        == ShippingPaymentMode.RECEIVER_DUE
    )


def test_effective_mode_legacy_receiver_fallback():
    assert (
        effective_shipping_payment_mode(
            postex_shipping_payment_mode="",
            postex_default_payment_type="RECEIVER",
        )
        == ShippingPaymentMode.RECEIVER_DUE
    )


def test_settings_accepts_manual_portal_with_receiver_due():
    s = _settings(
        POSTEX_FULFILLMENT_MODE="manual_portal",
        POSTEX_SHIPPING_PAYMENT_MODE="receiver_due",
    )
    assert s.POSTEX_FULFILLMENT_MODE == "manual_portal"


def test_settings_accepts_manual_portal_with_legacy_receiver():
    s = _settings(
        POSTEX_FULFILLMENT_MODE="manual_portal",
        POSTEX_SHIPPING_PAYMENT_MODE="",
        POSTEX_DEFAULT_PAYMENT_TYPE="RECEIVER",
    )
    assert s.POSTEX_FULFILLMENT_MODE == "manual_portal"


def test_settings_rejects_manual_portal_with_sender_prepaid():
    with pytest.raises(ValidationError):
        _settings(
            POSTEX_FULFILLMENT_MODE="manual_portal",
            POSTEX_SHIPPING_PAYMENT_MODE="sender_prepaid",
        )


def test_settings_rejects_manual_portal_with_legacy_sender():
    with pytest.raises(ValidationError):
        _settings(
            POSTEX_FULFILLMENT_MODE="manual_portal",
            POSTEX_SHIPPING_PAYMENT_MODE="",
            POSTEX_DEFAULT_PAYMENT_TYPE="SENDER",
        )


def test_fresh_process_module_settings_manual_portal_receiver_due():
    """First import of app.core.config.settings with manual_portal env already set."""
    repo_root = __import__("pathlib").Path(__file__).resolve().parents[1]
    env = {
        **__import__("os").environ,
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test",
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "ADMIN_STEP_UP_PIN": "93827461",
        "DEBUG": "true",
        "REDIS_HOST": "",
        "LOG_TO_FILE": "false",
        "POSTEX_FULFILLMENT_MODE": "manual_portal",
        "POSTEX_SHIPPING_PAYMENT_MODE": "receiver_due",
    }
    script = """
from app.core.config import settings
assert settings.POSTEX_FULFILLMENT_MODE == "manual_portal"
assert settings.POSTEX_SHIPPING_PAYMENT_MODE == "receiver_due"
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_fresh_process_settings_construct_manual_portal_receiver_due():
    """Simulate first Settings() during app bootstrap (no reliance on module global)."""
    script = """
from app.core.config import Settings
s = Settings(
    _env_file=None,
    POSTGRES_USER="test",
    POSTGRES_PASSWORD="test",
    POSTGRES_SERVER="localhost",
    POSTGRES_DB="test",
    SECRET_KEY="test-secret-key-with-at-least-32-characters",
    ADMIN_STEP_UP_PIN="93827461",
    DEBUG=True,
    REDIS_HOST=None,
    POSTEX_FULFILLMENT_MODE="manual_portal",
    POSTEX_SHIPPING_PAYMENT_MODE="receiver_due",
)
assert s.POSTEX_FULFILLMENT_MODE == "manual_portal"
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
    )
    assert completed.returncode == 0, completed.stderr
