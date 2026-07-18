"""P5: Redis-backed rate limiter integration tests (CI provides Redis)."""

import asyncio
import os

import pytest
from app.core.config import settings


def _redis_host() -> str:
    return os.environ.get("KARZAR_TEST_REDIS_HOST") or os.environ.get("REDIS_HOST", "")


@pytest.mark.integration
def test_redis_rate_limiter_counts_failures(monkeypatch):
    host = _redis_host()
    if not host:
        pytest.skip("Redis not configured for tests")

    monkeypatch.setattr(settings, "REDIS_HOST", host)
    monkeypatch.setattr(settings, "REDIS_PORT", int(os.environ.get("REDIS_PORT", "6379")))

    import app.core.rate_limit as rate_limit_module

    rate_limit_module._redis = None
    limiter = rate_limit_module.RedisRateLimiter()
    key = "p5:test:redis-rate"

    async def scenario():
        await limiter.clear(key)
        for _ in range(3):
            assert await limiter.retry_after_if_limited(key, 3, 30) is None
            await limiter.record_failure(key, 30)
        retry_after = await limiter.retry_after_if_limited(key, 3, 30)
        assert retry_after is not None and retry_after > 0
        await limiter.clear(key)

    asyncio.run(scenario())


@pytest.mark.integration
def test_redis_request_throttle_counts_requests(monkeypatch):
    host = _redis_host()
    if not host:
        pytest.skip("Redis not configured for tests")

    monkeypatch.setattr(settings, "REDIS_HOST", host)
    monkeypatch.setattr(settings, "REDIS_PORT", int(os.environ.get("REDIS_PORT", "6379")))

    import app.core.request_throttle as throttle_module

    throttle_module._redis = None
    limiter = throttle_module.RedisRequestThrottle()
    key = "p5:test:redis-throttle"

    async def scenario():
        for _ in range(3):
            assert await limiter.check_and_increment(key, 3, 30) is None
        retry_after = await limiter.check_and_increment(key, 3, 30)
        assert retry_after is not None and retry_after > 0

    asyncio.run(scenario())
