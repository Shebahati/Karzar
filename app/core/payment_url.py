"""Allowlist helpers for payment gateway redirect URLs."""

from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import settings

# Hosts permitted for browser redirects to a payment gateway / mock callback.
ALLOWED_PAYMENT_HOSTS = frozenset(
    {
        "www.zarinpal.com",
        "zarinpal.com",
        "sandbox.zarinpal.com",
        "payment.zarinpal.com",
    }
)


def _host_allowed(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.lower().rstrip(".")
    if host in ALLOWED_PAYMENT_HOSTS:
        return True
    # Local / configured storefront callback hosts (mock provider).
    for candidate in (
        settings.PAYMENT_CALLBACK_URL,
        settings.PAYMENT_SUCCESS_REDIRECT_URL,
        settings.PAYMENT_FAILURE_REDIRECT_URL,
    ):
        if not candidate:
            continue
        try:
            allowed = urlparse(candidate).hostname
        except Exception:
            continue
        if allowed and host == allowed.lower():
            return True
    if host in {"localhost", "127.0.0.1"}:
        return True
    return False


def is_allowed_payment_url(url: str) -> bool:
    """Return True when ``url`` is a safe absolute http(s) payment redirect."""
    if not url or not isinstance(url, str):
        return False
    raw = url.strip()
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        # Production gateways must be HTTPS; allow http only for local mock.
        return False
    return _host_allowed(parsed.hostname)


def assert_allowed_payment_url(url: str) -> str:
    if not is_allowed_payment_url(url):
        raise ValueError("Payment URL host is not allowlisted")
    return url
