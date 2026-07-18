"""Readiness probes for external dependencies (PostgreSQL, Redis)."""

from sqlalchemy import text

from app.db.database import engine


async def check_database_connection() -> bool:
    """Return True when PostgreSQL accepts a simple SELECT 1 query."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def ping_redis() -> bool:
    """Return True when Redis is reachable, or when Redis is not configured."""
    from app.core.config import settings

    if not settings.redis_enabled:
        return True

    try:
        import redis.asyncio as aioredis

        # redis_enabled guarantees REDIS_HOST is set; narrow for type checkers.
        host = settings.REDIS_HOST
        if not host:
            return True

        client = aioredis.Redis(
            host=host,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
        try:
            return await client.ping()
        finally:
            await client.close()
    except Exception:
        return False
