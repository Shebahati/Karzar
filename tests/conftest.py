# tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import get_db
from app.db.models.base import Base
from app.main import app

# ایجاد یک دیتابیس SQLite ایزوله در حافظه موقت (مخصوص تست)
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    poolclass=StaticPool,
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

@pytest.fixture(autouse=True)
def override_database():
    """
    این تابع جادویی، به طور خودکار قبل از هر تست اجرا می‌شود.
    ارتباط FastAPI با دیتابیس واقعی را قطع کرده و آن را به SQLite متصل می‌کند.
    """
    # ۱. ساخت جداول در دیتابیس تستی
    async def init_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init_db())

    # ۲. تزریق دیتابیس تستی به جای دیتابیس واقعی
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db

    # ۳. اجازه اجرای تست
    yield

    # ۴. پاکسازی دیتابیس تستی پس از پایان تست
    async def drop_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(drop_db())
    app.dependency_overrides.clear()