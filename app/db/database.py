"""Async SQLAlchemy engine, session factory, and FastAPI database dependency."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.ASYNC_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"timeout": 30},
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # Keep ORM instances usable after commit in async request handlers.
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield one AsyncSession per request; rollback on error, always close."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
