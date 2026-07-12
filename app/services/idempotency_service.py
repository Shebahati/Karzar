"""Idempotency key storage for checkout and payment flows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Optional

from fastapi import Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import platform as crud_platform


async def run_idempotent(
    db: AsyncSession,
    *,
    scope: str,
    key: Optional[str],
    handler: Callable[[], Coroutine[Any, Any, tuple[int, dict[str, Any]]]],
) -> Response:
    """Return a cached response when the same idempotency key is replayed."""
    if not key or not key.strip():
        status_code, body = await handler()
        return JSONResponse(status_code=status_code, content=body)

    normalized_key = key.strip()
    existing = await crud_platform.get_idempotency_record(
        db, scope=scope, key=normalized_key
    )
    if existing is not None:
        return JSONResponse(
            status_code=existing.status_code,
            content=existing.response_body,
        )

    status_code, body = await handler()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS)
    await crud_platform.store_idempotency_record(
        db,
        scope=scope,
        key=normalized_key,
        status_code=status_code,
        response_body=body,
        expires_at=expires_at,
    )
    await db.commit()
    return JSONResponse(status_code=status_code, content=body)
