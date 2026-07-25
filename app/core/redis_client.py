"""Shared Redis client factory (password-aware)."""

from __future__ import annotations

from typing import Any

from app.core.config import settings


def redis_connection_kwargs() -> dict[str, Any]:
    """Keyword args for redis.asyncio.Redis / redis.Redis."""
    kwargs: dict[str, Any] = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "decode_responses": True,
    }
    if settings.REDIS_PASSWORD:
        kwargs["password"] = settings.REDIS_PASSWORD
    return kwargs


def create_redis_client():
    """Create an async Redis client using current settings."""
    import redis.asyncio as aioredis

    return aioredis.Redis(**redis_connection_kwargs())
