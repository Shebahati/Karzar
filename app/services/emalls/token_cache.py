"""Token validation cache for Emalls (Redis preferred, in-memory fallback).

Stores only a positive "valid" marker. Never persists the raw token.
"""

from __future__ import annotations

import hashlib
import time
from typing import Protocol

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHE_PREFIX = "emalls:token:"
_VALID_MARKER = "1"


def token_cache_key(token: str, shop_domain: str) -> str:
    """Namespaced SHA-256 digest of token + normalized domain (no raw token)."""
    normalized_domain = shop_domain.strip().lower()
    digest = hashlib.sha256(f"{token}:{normalized_domain}".encode()).hexdigest()
    return f"{_CACHE_PREFIX}{digest}"


class EmallsTokenCache(Protocol):
    async def get_valid(self, key: str) -> bool: ...

    async def set_valid(self, key: str, ttl_seconds: int) -> None: ...

    def reset(self) -> None: ...


class InMemoryEmallsTokenCache:
    """Process-local TTL cache used when Redis is disabled (tests/dev)."""

    def __init__(self) -> None:
        self._entries: dict[str, float] = {}

    async def get_valid(self, key: str) -> bool:
        expires_at = self._entries.get(key)
        if expires_at is None:
            return False
        if expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return False
        return True

    async def set_valid(self, key: str, ttl_seconds: int) -> None:
        self._entries[key] = time.monotonic() + max(1, ttl_seconds)

    def reset(self) -> None:
        self._entries.clear()


class RedisEmallsTokenCache:
    """Redis-backed positive token validation cache."""

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

    async def get_valid(self, key: str) -> bool:
        try:
            value = await self._get_client().get(key)
            return value == _VALID_MARKER
        except Exception as exc:  # pragma: no cover - depends on live Redis
            logger.warning(
                "integration=emalls cache_get_failed reason=%s",
                type(exc).__name__,
            )
            return False

    async def set_valid(self, key: str, ttl_seconds: int) -> None:
        try:
            await self._get_client().set(key, _VALID_MARKER, ex=max(1, ttl_seconds))
        except Exception as exc:  # pragma: no cover - depends on live Redis
            logger.warning(
                "integration=emalls cache_set_failed reason=%s",
                type(exc).__name__,
            )

    def reset(self) -> None:
        self._client = None


_in_memory = InMemoryEmallsTokenCache()
_redis: RedisEmallsTokenCache | None = None


def get_emalls_token_cache() -> EmallsTokenCache:
    global _redis
    if settings.redis_enabled:
        if _redis is None:
            _redis = RedisEmallsTokenCache()
        return _redis
    return _in_memory


def reset_emalls_token_cache_for_tests() -> None:
    """Clear in-memory cache between tests."""
    _in_memory.reset()
