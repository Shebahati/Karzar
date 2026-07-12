"""Pytest fixtures: in-memory SQLite database, seeded data, and auth overrides."""

import os

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
os.environ.setdefault("REDIS_HOST", "")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ADMIN_STEP_UP_PIN", "93827461")
os.environ["ENABLE_API_DOCS"] = "false"
os.environ["ALLOW_PUBLIC_REGISTER"] = "true"
os.environ["OTP_DEV_ECHO"] = "true"

USE_POSTGRES_TESTS = os.environ.get("USE_POSTGRES_TESTS", "").lower() in ("1", "true", "yes")

import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Enum as SAEnum, select
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Base  # noqa: F401 — registers all ORM tables
from app.db.models.product import Category, Brand, Product, ProductImage, StockUnitEnum
from app.db.models.user import User, UserRole
from app.api.deps import get_current_super_admin
from app.main import app


def customer_auth_headers(phone: str = "09123333333") -> dict[str, str]:
    """OTP-login helper for authenticated purchase checkout tests."""
    from fastapi.testclient import TestClient

    test_client = TestClient(app)
    request = test_client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = request.json()["dev_code"]
    verify = test_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "code": code},
    )
    token = verify.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def purchase_customer_headers(monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    return customer_auth_headers("09123333333")


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    """Map PostgreSQL JSONB to SQLite JSON for in-memory test runs."""
    return "JSON"


@compiles(SAEnum, "sqlite")
def compile_enum_sqlite(element, compiler, **kw):
    """Map PostgreSQL native enums to VARCHAR for SQLite compatibility."""
    return "VARCHAR(50)"


test_engine = (
    create_async_engine(
        (
            f"postgresql+asyncpg://{os.environ['POSTGRES_USER']}:"
            f"{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_SERVER']}:"
            f"{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
        ),
        echo=False,
    )
    if USE_POSTGRES_TESTS
    else create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,
    )
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def _seed_reference_data(session: AsyncSession) -> None:
    """Create a strict 3-layer category tree and a test brand."""
    root = Category(name="Digital Calipers")
    session.add(root)
    await session.flush()

    level_two = Category(name="Standard Type", parent_id=root.id)
    session.add(level_two)
    await session.flush()

    level_three = Category(name="0-150mm Range", parent_id=level_two.id)
    brand = Brand(name="TestBrand", country="IR")
    session.add_all([level_three, brand])
    await session.flush()


async def _create_super_admin(session: AsyncSession) -> User:
    admin = User(
        phone_number="09120000001",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Test Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    return admin


async def override_super_admin():
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.phone_number == "09120000001")
        )
        return result.scalars().first()


@pytest.fixture(autouse=True)
def override_database():
    """Replace the production DB dependency with an isolated in-memory SQLite DB."""
    async def init_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as session:
            await _seed_reference_data(session)
            await _create_super_admin(session)
            await session.commit()

    asyncio.run(init_db())

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield

    async def drop_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(drop_db())
    app.dependency_overrides.clear()


@pytest.fixture
def super_admin_headers():
    from app.core.security import create_access_token

    app.dependency_overrides[get_current_super_admin] = override_super_admin

    token = create_access_token(subject="09120000001")
    headers = {"Authorization": f"Bearer {token}"}
    yield headers

    app.dependency_overrides.pop(get_current_super_admin, None)


@pytest.fixture
def step_up_headers(super_admin_headers):
    """Obtain a valid step-up token for destructive-action endpoint tests."""
    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app

    from app.core.config import settings

    client = TestClient(fastapi_app)
    response = client.post(
        "/api/v1/auth/verify-pin",
        json={"pin": settings.ADMIN_STEP_UP_PIN},
        headers=super_admin_headers,
    )
    assert response.status_code == 200
    secure_token = response.json()["secure_token"]
    return {**super_admin_headers, "X-Step-Up-Token": secure_token}


@pytest.fixture
def valid_product_data():
    return {
        "sku": "TEST-001",
        "name": "Test Product",
        "category_id": 3,
        "brand_id": 1,
        "base_price": "99.99",
        "stock_quantity": "50",
        "stock_unit": StockUnitEnum.PIECE.value,
        "is_active": True,
        "specifications": {
            "technical_specs": {"range": "0-150mm"},
            "features": {"waterproof": False},
            "dimensions": {"L_mm": 236.0},
            "optional_accessories": [],
        },
    }
