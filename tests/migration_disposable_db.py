"""Disposable PostgreSQL databases for migration integration tests only."""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import asyncpg

_DISPOSABLE_NAME = re.compile(r"^karzar_u6_mig_[a-f0-9]{12}$")


def assert_disposable_database_name(name: str) -> None:
    if not _DISPOSABLE_NAME.match(name):
        raise RuntimeError(
            f"Refusing migration test on database '{name}'; "
            "name must match karzar_u6_mig_<12 hex chars>",
        )


def _pg_connect_kwargs(database: str) -> dict[str, str]:
    return {
        "host": os.environ["POSTGRES_SERVER"],
        "port": os.environ["POSTGRES_PORT"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "database": database,
    }


async def _create_database(db_name: str) -> None:
    assert_disposable_database_name(db_name)
    conn = await asyncpg.connect(**_pg_connect_kwargs("postgres"))
    try:
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


async def _drop_database(db_name: str) -> None:
    assert_disposable_database_name(db_name)
    conn = await asyncpg.connect(**_pg_connect_kwargs("postgres"))
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
    finally:
        await conn.close()


@contextmanager
def disposable_migration_database() -> Iterator[str]:
    """Create an isolated database; drop it on exit (even after failures)."""
    db_name = f"karzar_u6_mig_{uuid.uuid4().hex[:12]}"
    asyncio.run(_create_database(db_name))
    try:
        yield db_name
    finally:
        asyncio.run(_drop_database(db_name))


async def connect_disposable(db_name: str) -> asyncpg.Connection:
    assert_disposable_database_name(db_name)
    return await asyncpg.connect(**_pg_connect_kwargs(db_name))
