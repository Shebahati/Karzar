# tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.database import get_db
from app.db.models.base import Base
from app.main import app
from fastapi.testclient import TestClient


# Create test database engine
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create a test database and return a session."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    
    async def override_get_db():
        async with async_session_factory() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield async_session_factory
    
    await engine.dispose()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)
