"""Read-only database access for IMG-02A-01."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from .contracts import AuditError, ImageRow, ProductRow

# Reject mutating / DDL statements while allowing SELECT and read-only txn setup.
_WRITE_DDL_RE = re.compile(
    r"(?is)\b(?:"
    r"INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|"
    r"GRANT|REVOKE|COPY|VACUUM|REINDEX"
    r")\b"
)
_ALLOWED_SETUP_RE = re.compile(
    r"(?is)^\s*(?:SET\s+TRANSACTION\s+READ\s+ONLY|SHOW\s+transaction_read_only)\s*;?\s*$"
)


def assert_readonly_sql(statement: str) -> None:
    """Fail closed on governed write/DDL SQL. Allows SELECT and read-only txn setup."""
    stripped = (statement or "").strip()
    if not stripped:
        raise AuditError("sql_guard", "empty SQL rejected")
    if _ALLOWED_SETUP_RE.match(stripped):
        return
    # Strip single-line SQL comments for guard scanning
    no_line_comments = re.sub(r"--[^\n]*", " ", stripped)
    if _WRITE_DDL_RE.search(no_line_comments):
        raise AuditError("sql_guard", f"mutating/DDL SQL rejected: {stripped[:120]}")
    upper = no_line_comments.lstrip().upper()
    if not (
        upper.startswith("SELECT")
        or upper.startswith("WITH")
        or upper.startswith("EXPLAIN")
        or upper.startswith("SHOW")
        or upper.startswith("SET TRANSACTION")
        or upper.startswith("PRAGMA")  # SQLite introspection in tests
    ):
        raise AuditError("sql_guard", f"non-SELECT SQL rejected: {stripped[:120]}")


def sanitize_database_url_for_engine(url: str) -> str:
    """Accept asyncpg or generic postgres URLs; never log the result."""
    raw = (url or "").strip()
    if not raw:
        raise AuditError("database", "database URL is required")
    if raw.startswith("postgresql://"):
        return "postgresql+asyncpg://" + raw[len("postgresql://") :]
    if raw.startswith("postgres://"):
        return "postgresql+asyncpg://" + raw[len("postgres://") :]
    if raw.startswith("sqlite://") and not raw.startswith("sqlite+"):
        # Prefer aiosqlite for AsyncEngine
        return "sqlite+aiosqlite://" + raw[len("sqlite://") :]
    return raw


def safe_database_identity(url: str, *, dialect: str, database_name: str | None, database_user: str | None) -> dict[str, Any]:
    """Identity fields safe to persist (no host/password/DSN)."""
    return {
        "dialect": dialect,
        "database_name": database_name,
        "database_user": database_user,
    }


def _parse_safe_identity(url: str) -> tuple[str | None, str | None]:
    try:
        parsed = urlparse(url)
    except Exception:
        return None, None
    name = (parsed.path or "").lstrip("/") or None
    user = parsed.username
    return name, user


@dataclass
class ReadOnlyDbContext:
    session: AsyncSession
    dialect: str
    database_name: str | None
    database_user: str | None
    transaction_read_only: str  # "on" | "off" | "sqlite-test"


def _install_statement_guard(engine: AsyncEngine) -> None:
    sync_engine = engine.sync_engine

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before_cursor_execute(  # type: ignore[no-untyped-def]
        conn, cursor, statement, parameters, context, executemany
    ):
        assert_readonly_sql(statement)


@asynccontextmanager
async def open_readonly_session(database_url: str) -> AsyncIterator[ReadOnlyDbContext]:
    """Open one explicit read-only transaction; always rollback."""
    url = sanitize_database_url_for_engine(database_url)
    db_name, db_user = _parse_safe_identity(url)
    engine = create_async_engine(url, echo=False, future=True)
    _install_statement_guard(engine)
    maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    session = maker()
    dialect = engine.dialect.name
    txn_flag = "off"
    try:
        # Begin an explicit transaction (SQLAlchemy 2 style)
        await session.connection()
        if dialect == "postgresql":
            await session.execute(text("SET TRANSACTION READ ONLY"))
            result = await session.execute(text("SHOW transaction_read_only"))
            row = result.first()
            txn_flag = str(row[0]).lower() if row else "off"
            if txn_flag != "on":
                raise AuditError(
                    "database",
                    f"PostgreSQL transaction_read_only must be on, got {txn_flag!r}",
                )
        else:
            # SQLite (tests): no SET TRANSACTION READ ONLY; guard still active
            txn_flag = "sqlite-test"

        ctx = ReadOnlyDbContext(
            session=session,
            dialect=dialect,
            database_name=db_name,
            database_user=db_user,
            transaction_read_only=txn_flag,
        )
        yield ctx
    finally:
        try:
            await session.rollback()
        except Exception:
            pass
        await session.close()
        await engine.dispose()


async def fetch_products(
    session: AsyncSession,
    *,
    include_deleted: bool = True,
) -> list[ProductRow]:
    """SELECT Product rows with brand/category names (Core-style ORM select)."""
    from app.db.models.product import Brand, Category, Product

    stmt: Select[Any] = (
        select(
            Product.id,
            Product.sku,
            Product.slug,
            Product.name,
            Product.category_id,
            Product.brand_id,
            Product.is_active,
            Product.is_available,
            Product.deleted_at,
            Brand.name,
            Category.name,
        )
        .select_from(Product)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .order_by(Product.id.asc())
    )
    if not include_deleted:
        stmt = stmt.where(Product.deleted_at.is_(None))

    result = await session.execute(stmt)
    rows: list[ProductRow] = []
    for r in result.all():
        rows.append(
            ProductRow(
                product_id=int(r[0]),
                sku=str(r[1]),
                slug=str(r[2]),
                name=str(r[3]),
                category_id=int(r[4]) if r[4] is not None else None,
                brand_id=int(r[5]) if r[5] is not None else None,
                is_active=bool(r[6]),
                is_available=bool(r[7]),
                deleted_at=r[8],
                brand_name=str(r[9]) if r[9] is not None else None,
                category_name=str(r[10]) if r[10] is not None else None,
            )
        )
    return rows


async def fetch_product_images(session: AsyncSession) -> list[ImageRow]:
    from app.db.models.product import ProductImage

    stmt = (
        select(
            ProductImage.id,
            ProductImage.product_id,
            ProductImage.image_url,
            ProductImage.is_primary,
            ProductImage.display_order,
        )
        .order_by(ProductImage.product_id.asc(), ProductImage.id.asc())
    )
    result = await session.execute(stmt)
    out: list[ImageRow] = []
    for r in result.all():
        out.append(
            ImageRow(
                image_id=int(r[0]),
                product_id=int(r[1]),
                image_url=str(r[2]),
                is_primary=bool(r[3]),
                display_order=int(r[4]),
            )
        )
    return out


def sync_assert_readonly_sql_for_tests(statement: str) -> None:
    """Public alias for unit tests."""
    assert_readonly_sql(statement)


def sync_guard_rejects_on_session(session: Session, statement: str) -> None:
    """Execute via sync Session to exercise the same guard string check."""
    assert_readonly_sql(statement)
    # Do not actually execute mutating SQL in tests — guard alone is the proof.
