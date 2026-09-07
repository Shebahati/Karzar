"""Pytest fixtures: opt-in test database, seeded data, and auth overrides."""

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
os.environ["SMS_PROVIDER"] = "console"
os.environ["PAYMENT_PROVIDER"] = "mock"
# Lifespan workers use app.db.database.async_session_maker (same Postgres URI in CI).
# Disable them so they cannot race TRUNCATE / payment uniqueness with the suite.
os.environ["DISABLE_BACKGROUND_WORKERS"] = "1"

USE_POSTGRES_TESTS = os.environ.get("USE_POSTGRES_TESTS", "").lower() in ("1", "true", "yes")

# Preserve CI Redis for opt-in integration tests, then disable for the default
# suite. Redis async clients are loop-bound; TestClient + asyncio.run fixtures
# use different loops and Redis rate-limit checks fail closed (429).
os.environ.setdefault("KARZAR_TEST_REDIS_HOST", os.environ.get("REDIS_HOST", ""))
if os.environ.get("USE_REDIS_IN_TESTS", "").lower() not in ("1", "true", "yes"):
    os.environ["REDIS_HOST"] = ""

# ruff: noqa: E402 — env vars must be set before importing app modules
import asyncio

import pytest
from app.api.deps import get_current_super_admin
from app.core.config import settings
from app.core.rate_limit import reset_in_memory_limiter
from app.core.request_throttle import reset_in_memory_request_throttle
from app.core.security import get_password_hash
from app.db.database import get_db
from app.db.models import Base  # noqa: F401 — registers all ORM tables
from app.db.models.product import Brand, Category, StockUnitEnum
from app.db.models.user import User, UserRole
from app.main import app
from app.services.sms_service import reset_sms_provider_for_tests
from sqlalchemy import Enum as SAEnum
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy.schema import CreateIndex

ADMIN_PASSWORD = "adminpass123"
ADMIN_PHONE = "09120000001"

# Observable by regression tests. Hashing is session-cached; database setup is
# opt-in via `override_database` (fixture dependency or usefixtures).
FIXTURE_STATS = {
    "database_setups": 0,
    "password_hashes": 0,
    "table_resets": 0,
}

_admin_password_hash: str | None = None


def get_cached_admin_password_hash() -> str:
    """Return the seeded admin bcrypt hash, computing it at most once per process."""
    global _admin_password_hash
    if _admin_password_hash is None:
        _admin_password_hash = get_password_hash(ADMIN_PASSWORD)
        FIXTURE_STATS["password_hashes"] += 1
    return _admin_password_hash


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
def purchase_customer_headers(monkeypatch, override_database):
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


@compiles(CreateIndex, "sqlite")
def compile_partial_unique_index_sqlite(element, compiler, **kw):
    """SQLite tests ignore PostgreSQL partial unique indexes (not representable 1:1)."""
    index = element.element
    if index.dialect_options.get("postgresql", {}).get("where") is not None:
        index.unique = False
    return compiler.visit_create_index(element, **kw)


# Postgres + TestClient: each asyncio.run() / Starlette request may use a
# different event loop. NullPool avoids reusing asyncpg connections across loops.
test_engine = (
    create_async_engine(
        (
            f"postgresql+asyncpg://{os.environ['POSTGRES_USER']}:"
            f"{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_SERVER']}:"
            f"{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
        ),
        echo=False,
        poolclass=NullPool,
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


async def _reset_postgres_tables() -> None:
    """Wipe rows between tests; schema is owned by Alembic in CI."""
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    if not tables:
        return
    async with test_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def _reset_sqlite_tables() -> None:
    """Delete all rows and reset SQLite autoincrement so seed IDs stay stable."""
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
        seq = await conn.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='sqlite_sequence'"
            )
        )
        if seq.first() is not None:
            await conn.execute(text("DELETE FROM sqlite_sequence"))


async def _reset_all_tables() -> None:
    if USE_POSTGRES_TESTS:
        await _reset_postgres_tables()
    else:
        await _reset_sqlite_tables()
    FIXTURE_STATS["table_resets"] += 1


async def _create_sqlite_schema() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _drop_sqlite_schema() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Isolate throttle / SMS provider state between tests."""
    reset_in_memory_limiter()
    reset_in_memory_request_throttle()
    reset_sms_provider_for_tests()
    yield
    reset_in_memory_limiter()
    reset_in_memory_request_throttle()
    reset_sms_provider_for_tests()


async def _seed_reference_data(session: AsyncSession) -> None:
    """Create a strict 3-layer category tree and a test brand."""
    root = Category(name="Digital Calipers", slug="digital-calipers")
    session.add(root)
    await session.flush()

    level_two = Category(name="Standard Type", parent_id=root.id, slug="standard-type")
    session.add(level_two)
    await session.flush()

    level_three = Category(name="0-150mm Range", parent_id=level_two.id, slug="0-150mm-range")
    brand = Brand(name="TestBrand", country="IR", slug="testbrand")
    session.add_all([level_three, brand])
    await session.flush()


async def _create_super_admin(session: AsyncSession) -> User:
    admin = User(
        phone_number=ADMIN_PHONE,
        hashed_password=get_cached_admin_password_hash(),
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
            select(User).where(User.phone_number == ADMIN_PHONE)
        )
        return result.scalars().first()


@pytest.fixture(scope="session")
def _test_schema():
    """Create SQLite schema once per session when any test opts into the DB fixture."""
    if not USE_POSTGRES_TESTS:
        asyncio.run(_create_sqlite_schema())
    try:
        yield
    finally:
        if not USE_POSTGRES_TESTS:
            asyncio.run(_drop_sqlite_schema())
        asyncio.run(test_engine.dispose())


@pytest.fixture
def override_database(_test_schema):
    """Opt-in isolated test database: truncate + seed once per requesting test.

    Isolation boundary is reset-at-start (TRUNCATE RESTART IDENTITY on Postgres,
    DELETE + sqlite_sequence reset on SQLite). Teardown always disposes the
    engine and clears FastAPI dependency overrides, including after failures.
    The next database test re-seeds; leftover rows cannot leak into a later
    DB test. Pure tests never request this fixture and do not connect.
    """

    async def init_db():
        await _reset_all_tables()
        async with TestingSessionLocal() as session:
            await _seed_reference_data(session)
            await _create_super_admin(session)
            await session.commit()
        if USE_POSTGRES_TESTS:
            # Drop loop-bound asyncpg connections before TestClient starts its loop.
            await test_engine.dispose()

    asyncio.run(init_db())
    FIXTURE_STATS["database_setups"] += 1

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield
    finally:
        app.dependency_overrides.clear()
        asyncio.run(test_engine.dispose())


@pytest.fixture(autouse=True)
def _disable_storefront_image_hiding_for_tests(monkeypatch):
    """Legacy integration tests create products without images; production hides them."""
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "STOREFRONT_HIDE_IMAGELESS_PRODUCTS", False)


@pytest.fixture
def super_admin_headers(override_database):
    from app.core.security import create_access_token

    app.dependency_overrides[get_current_super_admin] = override_super_admin

    token = create_access_token(subject=ADMIN_PHONE)
    headers = {"Authorization": f"Bearer {token}"}
    yield headers

    app.dependency_overrides.pop(get_current_super_admin, None)


@pytest.fixture
def step_up_headers(super_admin_headers):
    """Obtain a valid step-up token for destructive-action endpoint tests."""
    from app.core.config import settings as app_settings
    from app.main import app as fastapi_app
    from fastapi.testclient import TestClient

    client = TestClient(fastapi_app)
    response = client.post(
        "/api/v1/auth/verify-pin",
        json={"pin": app_settings.ADMIN_STEP_UP_PIN},
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
        "is_available": True,
        "stock_unit": StockUnitEnum.PIECE.value,
        "is_active": True,
        "specifications": {
            "technical_specs": {"range": "0-150mm"},
            "features": {"waterproof": False},
            "dimensions": {"L_mm": 236.0},
            "optional_accessories": [],
        },
    }
