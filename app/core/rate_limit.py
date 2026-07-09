"""Distributed rate limiting for auth-sensitive endpoints.

Provides a small failure-counter abstraction with two backends:

* ``RedisRateLimiter`` — fixed-window counters shared across all API workers,
  used whenever ``REDIS_HOST`` is configured. This is what makes brute-force
  protection effective behind multiple gunicorn/uvicorn processes.
* ``InMemoryRateLimiter`` — a per-process sliding window used as a fallback
  when Redis is not configured (e.g. local dev and the test suite).

The limiter counts *failures*: callers record a failure on a bad attempt and
clear the key on success, mirroring a login/OTP throttle.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Optional, Protocol

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter(Protocol):
    async def retry_after_if_limited(
        self, key: str, max_attempts: int, window_seconds: int
    ) -> Optional[int]:
        """Return seconds-to-wait if ``key`` is over the limit, else ``None``."""
        ...

    async def record_failure(self, key: str, window_seconds: int) -> None: ...

    async def clear(self, key: str) -> None: ...


class InMemoryRateLimiter:
    """Per-process sliding-window failure counter (single-worker fallback)."""

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, attempts: deque[float], now: float, window: int) -> None:
        while attempts and (now - attempts[0]) > window:
            attempts.popleft()

    async def retry_after_if_limited(
        self, key: str, max_attempts: int, window_seconds: int
    ) -> Optional[int]:
        now = time.monotonic()
        attempts = self._attempts[key]
        self._prune(attempts, now, window_seconds)
        if len(attempts) >= max_attempts:
            return max(1, int(window_seconds - (now - attempts[0])))
        return None

    async def record_failure(self, key: str, window_seconds: int) -> None:
        now = time.monotonic()
        attempts = self._attempts[key]
        self._prune(attempts, now, window_seconds)
        attempts.append(now)

    async def clear(self, key: str) -> None:
        self._attempts.pop(key, None)

    def reset(self) -> None:
        self._attempts.clear()


class RedisRateLimiter:
    """Fixed-window failure counter backed by Redis (shared across workers).

    Fails open on Redis errors: if the store is unreachable the request is not
    throttled (the readiness probe removes such an instance from rotation).
    """

    _KEY_PREFIX = "ratelimit:"

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True,
            )
        return self._client

    def _k(self, key: str) -> str:
        return f"{self._KEY_PREFIX}{key}"

    async def retry_after_if_limited(
        self, key: str, max_attempts: int, window_seconds: int
    ) -> Optional[int]:
        try:
            client = self._get_client()
            redis_key = self._k(key)
            count = await client.get(redis_key)
            if count is not None and int(count) >= max_attempts:
                ttl = await client.ttl(redis_key)
                return max(1, ttl) if ttl and ttl > 0 else window_seconds
            return None
        except Exception as exc:  # pragma: no cover - depends on live Redis
            logger.warning("Rate limiter (check) degraded, failing open: %s", exc)
            return None

    async def record_failure(self, key: str, window_seconds: int) -> None:
        try:
            client = self._get_client()
            redis_key = self._k(key)
            new_count = await client.incr(redis_key)
            if new_count == 1:
                await client.expire(redis_key, window_seconds)
        except Exception as exc:  # pragma: no cover - depends on live Redis
            logger.warning("Rate limiter (record) degraded: %s", exc)

    async def clear(self, key: str) -> None:
        try:
            client = self._get_client()
            await client.delete(self._k(key))
        except Exception as exc:  # pragma: no cover - depends on live Redis
            logger.warning("Rate limiter (clear) degraded: %s", exc)


_in_memory = InMemoryRateLimiter()
_redis: Optional[RedisRateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Return the active limiter based on runtime configuration."""
    global _redis
    if settings.redis_enabled:
        if _redis is None:
            _redis = RedisRateLimiter()
        return _redis
    return _in_memory


def reset_in_memory_limiter() -> None:
    """Testing helper: clear the in-memory limiter between tests."""
    _in_memory.reset()
