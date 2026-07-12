"""Application middleware helpers (request id, security headers)."""

from __future__ import annotations

import uuid

from starlette.requests import Request


def get_or_create_request_id(request: Request) -> str:
    incoming = request.headers.get("X-Request-ID")
    if incoming and incoming.strip():
        return incoming.strip()[:128]
    return str(uuid.uuid4())
