from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import engine


async def check_database_connection() -> bool:
    """Return True when PostgreSQL accepts a simple query."""
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

        client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
        try:
            return await client.ping()
        finally:
            await client.aclose()
    except Exception:
        return False
