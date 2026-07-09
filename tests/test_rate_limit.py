"""Rate limiter unit and integration tests."""

import asyncio

from fastapi.testclient import TestClient

from app.api.endpoints import auth as auth_endpoints
from app.core.config import settings
from app.core.rate_limit import InMemoryRateLimiter
from app.main import app

client = TestClient(app)


class TestInMemoryRateLimiter:
    def test_counts_failures_and_limits(self):
        limiter = InMemoryRateLimiter()

        async def scenario():
            for _ in range(3):
                assert await limiter.retry_after_if_limited("k", 3, 60) is None
                await limiter.record_failure("k", 60)
            # Fourth check is over the limit.
            retry_after = await limiter.retry_after_if_limited("k", 3, 60)
            assert retry_after is not None and retry_after > 0
            # Clearing resets the counter.
            await limiter.clear("k")
            assert await limiter.retry_after_if_limited("k", 3, 60) is None

        asyncio.run(scenario())


class TestLoginThrottle:
    def test_login_locks_out_after_max_attempts(self):
        auth_endpoints._reset_pin_rate_limiter_for_tests()
        max_attempts = settings.AUTH_MAX_ATTEMPTS

        # Unknown user → fast path, no bcrypt cost.
        for _ in range(max_attempts):
            resp = client.post(
                "/api/v1/auth/login",
                data={"username": "09129999999", "password": "wrong"},
            )
            assert resp.status_code == 401

        blocked = client.post(
            "/api/v1/auth/login",
            data={"username": "09129999999", "password": "wrong"},
        )
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers

        auth_endpoints._reset_pin_rate_limiter_for_tests()
