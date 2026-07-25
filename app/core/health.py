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
        from app.core.redis_client import create_redis_client

        # redis_enabled guarantees REDIS_HOST is set; narrow for type checkers.
        if not settings.REDIS_HOST:
            return True

        client = create_redis_client()
        try:
            return await client.ping()
        finally:
            await client.close()
    except Exception:
        return False
