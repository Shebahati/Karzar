"""IP-scoped request throttling for public storefront endpoints.

Unlike ``rate_limit.py`` (failure counters for auth), this module counts every
request and is used to protect contact, checkout, product search, and order
tracking from abuse. Redis-backed counters are shared across workers when
``REDIS_HOST`` is configured.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Protocol

from fastapi import Request
from starlette import status

from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestThrottle(Protocol):
    async def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> int | None:
        """Return seconds-to-wait when over limit; otherwise record and return None."""
        ...


class InMemoryRequestThrottle:
    """Per-process sliding-window request counter."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, hits: deque[float], now: float, window: int) -> None:
        while hits and (now - hits[0]) > window:
            hits.popleft()

    async def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> int | None:
        now = time.monotonic()
        hits = self._hits[key]
        self._prune(hits, now, window_seconds)
        if len(hits) >= max_requests:
            return max(1, int(window_seconds - (now - hits[0])))
        hits.append(now)
        return None

    def reset(self) -> None:
        self._hits.clear()


class RedisRequestThrottle:
    """Fixed-window request counter backed by Redis."""

    _KEY_PREFIX = "reqthrottle:"

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

    async def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> int | None:
        try:
            client = self._get_client()
            redis_key = self._k(key)
            count = await client.incr(redis_key)
            if count == 1:
                await client.expire(redis_key, window_seconds)
            if count > max_requests:
                ttl = await client.ttl(redis_key)
                return max(1, ttl) if ttl and ttl > 0 else window_seconds
            return None
        except Exception as exc:  # pragma: no cover - depends on live Redis
            logger.warning("Request throttle degraded, failing closed: %s", exc)
            return window_seconds


_in_memory = InMemoryRequestThrottle()
_redis: RedisRequestThrottle | None = None


def get_request_throttle() -> RequestThrottle:
    global _redis
    if settings.redis_enabled:
        if _redis is None:
            _redis = RedisRequestThrottle()
        return _redis
    return _in_memory


def reset_in_memory_request_throttle() -> None:
    """Testing helper: clear the in-memory throttle between tests."""
    _in_memory.reset()


def client_ip(request: Request) -> str:
    """Best-effort client IP for throttling (direct connection or first XFF hop)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return "unknown"


async def enforce_public_throttle(
    request: Request,
    *,
    scope: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    """Raise 429 when the client IP exceeds the configured request budget."""
    key = f"{scope}:{client_ip(request)}"
    retry_after = await get_request_throttle().check_and_increment(
        key, max_requests, window_seconds
    )
    if retry_after is not None:
        raise api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMITED,
            message="تعداد درخواست‌ها بیش از حد مجاز است. لطفاً کمی بعد دوباره تلاش کنید.",
            headers={"Retry-After": str(retry_after)},
        )
