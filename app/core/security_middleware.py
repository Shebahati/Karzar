"""Security-oriented ASGI middleware (body size, HTTPS redirect, CSRF Origin)."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.status import (
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_403_FORBIDDEN,
    HTTP_413_CONTENT_TOO_LARGE,
)

from app.core.auth_cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from app.core.config import settings
from app.core.errors import ErrorCode, build_error_payload

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Gateway callbacks / public webhooks that are not browser cookie sessions.
_CSRF_EXEMPT_PREFIXES = (
    "/api/v1/payments/callback",
    "/api/v1/payments/verify",
    "/health",
    "/ready",
    "/metrics",
)


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies before they reach route handlers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
            except ValueError:
                size = 0
            if size > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=HTTP_413_CONTENT_TOO_LARGE,
                    content=build_error_payload(
                        error_code=ErrorCode.VALIDATION_FAILED,
                        message="Request body is too large",
                    ),
                )
        return await call_next(request)


class HttpsRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect plain HTTP to HTTPS when ENFORCE_HTTPS is enabled."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.ENFORCE_HTTPS:
            host = (request.url.hostname or "").lower()
            # Local smoke / docker health probes hit loopback over plain HTTP.
            if host in {"127.0.0.1", "localhost", "::1"}:
                return await call_next(request)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
            if forwarded_proto and forwarded_proto.lower() != "https":
                target = request.url.replace(scheme="https")
                return RedirectResponse(str(target), status_code=HTTP_307_TEMPORARY_REDIRECT)
        return await call_next(request)


def _origin_allowed(origin: str) -> bool:
    allowed = settings.cors_origins_list
    if not allowed or allowed == ["*"]:
        return True
    return origin.rstrip("/") in {o.rstrip("/") for o in allowed}


def _request_origin(request: Request) -> str | None:
    origin = (request.headers.get("origin") or "").strip()
    if origin:
        return origin
    referer = (request.headers.get("referer") or "").strip()
    if not referer:
        return None
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


class CookieCsrfOriginMiddleware(BaseHTTPMiddleware):
    """Reject cookie-authenticated unsafe requests without a trusted Origin/Referer."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in _UNSAFE_METHODS:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(prefix) for prefix in _CSRF_EXEMPT_PREFIXES):
            return await call_next(request)

        cookies = request.cookies
        if ACCESS_COOKIE_NAME not in cookies and REFRESH_COOKIE_NAME not in cookies:
            return await call_next(request)

        origin = _request_origin(request)
        own_origin = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
        if origin is None:
            # Browsers send Origin on cookie-auth mutations; TestClient/curl often omit it.
            if settings.DEBUG:
                return await call_next(request)
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content=build_error_payload(
                    error_code=ErrorCode.FORBIDDEN,
                    message="CSRF origin check failed",
                ),
            )

        if origin.rstrip("/") == own_origin or _origin_allowed(origin):
            return await call_next(request)

        return JSONResponse(
            status_code=HTTP_403_FORBIDDEN,
            content=build_error_payload(
                error_code=ErrorCode.FORBIDDEN,
                message="CSRF origin check failed",
            ),
        )
