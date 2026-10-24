"""Read-only production database identity fingerprint."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from catalog_target.ast_price_catalog_execution import async_sqlalchemy_database_url


async def fetch_database_identity_fingerprint(database_url: str) -> str:
    engine = create_async_engine(async_sqlalchemy_database_url(database_url))
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT
                          current_database(),
                          COALESCE(inet_server_addr()::text, 'local'),
                          COALESCE(inet_server_port()::text, '0'),
                          current_setting('server_version')
                        """
                    )
                )
            ).one()
        db_name, host, port, version = row
        return f"db={db_name}|host={host}|port={port}|pg={version}"
    finally:
        await engine.dispose()


async def assert_database_identity_matches_attestation(
    *,
    database_url: str,
    attested_identity: str,
) -> str:
    live = await fetch_database_identity_fingerprint(database_url)
    expected = (attested_identity or "").strip()
    if not expected:
        raise ValueError("production_database_identity_missing_in_attestation")
    if live != expected:
        raise ValueError("verified_production_database_identity_mismatch_attestation")
    return live
