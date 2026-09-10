"""Recursive redaction of secret-like keys from nested provider payloads."""

from __future__ import annotations

from typing import Any

_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "x-api-key",
    "authorization",
    "authorization",
    "token",
    "password",
    "secret",
    "login_token",
    "logintoken",
)

_REDACTED = "***REDACTED***"


def _is_secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS)


def redact_secrets(value: Any) -> Any:
    """Return a copy of *value* with secret-like keys replaced."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, inner in value.items():
            if _is_secret_key(str(key)):
                out[str(key)] = _REDACTED
            else:
                out[str(key)] = redact_secrets(inner)
        return out
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value
