"""Redis-backed distributed lock for single-leader background tasks."""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client = None
_LOCK_PREFIX = "lock:"


def _get_client():
    global _client
    if _client is None:
        import redis.asyncio as aioredis

        _client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
    return _client


async def try_acquire_lock(key: str, ttl_seconds: int) -> bool:
    """Acquire a short-lived lock; returns True when this worker should run the task."""
    if not settings.redis_enabled:
        return True
    try:
        client = _get_client()
        acquired = await client.set(f"{_LOCK_PREFIX}{key}", "1", nx=True, ex=ttl_seconds)
        return bool(acquired)
    except Exception as exc:  # pragma: no cover - depends on live Redis
        logger.warning("Distributed lock degraded, allowing task: %s", exc)
        return True


def reset_distributed_lock_client_for_tests() -> None:
    global _client
    _client = None
