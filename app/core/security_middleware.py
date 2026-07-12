"""Security-oriented ASGI middleware (body size, HTTPS redirect)."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.status import HTTP_307_TEMPORARY_REDIRECT, HTTP_413_CONTENT_TOO_LARGE

from app.core.config import settings
from app.core.errors import ErrorCode, build_error_payload


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
            forwarded_proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
            if forwarded_proto and forwarded_proto.lower() != "https":
                target = request.url.replace(scheme="https")
                return RedirectResponse(str(target), status_code=HTTP_307_TEMPORARY_REDIRECT)
        return await call_next(request)
