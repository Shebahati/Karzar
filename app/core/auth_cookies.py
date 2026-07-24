"""HttpOnly auth cookie helpers (access + refresh).

Dual-support: JSON body tokens remain for older clients; cookies are the
preferred browser transport. See frontend/docs/auth-cookie-httponly-contract.md.
"""

from __future__ import annotations

from typing import Any

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE_NAME = "karzar_access"
REFRESH_COOKIE_NAME = "karzar_refresh"
ACCESS_COOKIE_PATH = "/api/v1"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _cookie_secure() -> bool:
    if settings.AUTH_COOKIE_SECURE is not None:
        return settings.AUTH_COOKIE_SECURE
    return settings.ENFORCE_HTTPS or settings.APP_ENV == "production"


def _cookie_samesite() -> str:
    value = (settings.AUTH_COOKIE_SAMESITE or "lax").lower()
    if value not in {"lax", "strict", "none"}:
        return "lax"
    return value


def _common_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "httponly": True,
        "secure": _cookie_secure(),
        "samesite": _cookie_samesite(),
    }
    domain = (settings.AUTH_COOKIE_DOMAIN or "").strip()
    if domain:
        kwargs["domain"] = domain
    return kwargs


def set_auth_cookies(response: Response, tokens: dict[str, Any]) -> None:
    """Attach access + refresh HttpOnly cookies from an issue/rotate payload."""
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    expires_in = int(tokens.get("expires_in") or settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    common = _common_kwargs()

    if isinstance(access, str) and access:
        response.set_cookie(
            key=ACCESS_COOKIE_NAME,
            value=access,
            max_age=expires_in,
            path=ACCESS_COOKIE_PATH,
            **common,
        )
    if isinstance(refresh, str) and refresh:
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path=REFRESH_COOKIE_PATH,
            **common,
        )


def clear_auth_cookies(response: Response) -> None:
    """Expire auth cookies (logout)."""
    common = _common_kwargs()
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path=ACCESS_COOKIE_PATH, **_delete_kwargs(common))
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH, **_delete_kwargs(common))


def _delete_kwargs(common: dict[str, Any]) -> dict[str, Any]:
    # Starlette delete_cookie accepts httponly/secure/samesite/domain
    return {
        k: common[k]
        for k in ("httponly", "secure", "samesite", "domain")
        if k in common
    }
