"""Alembic migration environment with async engine and dynamic database URL."""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.append(os.getcwd())

import app.db.models  # noqa: F401 — register all ORM models with Base.metadata
from app.core.config import settings
from app.core.data_plane import format_identity_report, validate_data_plane
from app.db.models.base import Base

# Non-secret destination identity before any migration mutation.
_migration_identity = validate_data_plane(
    app_env=settings.APP_ENV,
    data_plane_explicit=settings.KARZAR_DATA_PLANE,
    postgres_db=settings.POSTGRES_DB,
    postgres_server=settings.POSTGRES_SERVER,
    media_plane=settings.KARZAR_MEDIA_PLANE,
    catalog_staging_db_name=settings.KARZAR_CATALOG_STAGING_DB_NAME,
    extra_live_db_names=settings.KARZAR_LIVE_DB_DENYLIST or None,
)
print("Alembic target identity:\n" + format_identity_report(_migration_identity))

config = context.config
config.set_main_option("sqlalchemy.url", settings.ASYNC_DATABASE_URI)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DBAPI connection (SQL script generation)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
