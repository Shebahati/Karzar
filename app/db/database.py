from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Create the Async SQLAlchemy Engine
engine = create_async_engine(
    settings.ASYNC_DATABASE_URI,
    echo=False,  # Set to True only for debugging SQL queries
    future=True,
    pool_size=20,      # Optimized for handling concurrent connections
    max_overflow=10,
    pool_pre_ping=True,  # Ensures connections are alive before using them
    connect_args={"timeout": 30}  # Connection timeout in seconds
)

# Create the Async Session Factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # Essential for async operations to prevent DetachedInstanceError
    autoflush=False,
    autocommit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to provide an async database session per request.
    Yields the session and ensures it is closed after the request is finished.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()