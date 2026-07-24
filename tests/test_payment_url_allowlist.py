"""Unit tests for payment URL allowlist."""

from app.core.payment_url import is_allowed_payment_url


def test_zarinpal_startpay_allowed():
    assert is_allowed_payment_url("https://www.zarinpal.com/pg/StartPay/A000111")


def test_evil_host_rejected():
    assert not is_allowed_payment_url("https://evil.example/phish")


def test_localhost_mock_callback_allowed():
    assert is_allowed_payment_url(
        "http://localhost:8000/api/v1/payments/callback?Authority=MOCK-1&Status=OK"
    )


def test_javascript_rejected():
    assert not is_allowed_payment_url("javascript:alert(1)")
