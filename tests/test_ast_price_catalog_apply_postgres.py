"""PostgreSQL-backed AST APPLY integration tests (CI: USE_POSTGRES_TESTS=1)."""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _integration_database_url() -> str:
    explicit = os.environ.get("KARZAR_AST_INTEGRATION_DATABASE_URL", "").strip()
    if explicit:
        return explicit
    if os.environ.get("USE_POSTGRES_TESTS", "").strip() == "1":
        user = os.environ.get("POSTGRES_USER", "postgres")
        password = os.environ.get("POSTGRES_PASSWORD", "postgres")
        host = os.environ.get("POSTGRES_SERVER", "127.0.0.1")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "karzar_ci")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    return ""


INTEGRATION_DB = _integration_database_url()
RUN_PG = bool(INTEGRATION_DB)


@unittest.skipUnless(RUN_PG, "PostgreSQL integration URL not configured")
class AstApplyPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_guarded_update_and_rollback(self) -> None:
        from catalog_target.ast_price_catalog_apply import UpdatePlanRow
        from catalog_target.ast_price_catalog_execution import async_sqlalchemy_database_url
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        class _Conn:
            def __init__(self, session):
                self._session = session
                self.committed = False
                self.rolled_back = False

            def cursor(self, *args, **kwargs):  # noqa: ANN002, ANN003
                raise RuntimeError("use async path")

        engine = create_async_engine(async_sqlalchemy_database_url(INTEGRATION_DB))
        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT id, sku, base_price::text FROM products "
                        "WHERE deleted_at IS NULL LIMIT 1 FOR UPDATE"
                    )
                )
            ).first()
            self.assertIsNotNone(row)
            pid, sku, price = int(row[0]), str(row[1]), Decimal(str(row[2]))
            new_price = price + Decimal("1")
            from catalog_target.ast_price_catalog_execution import _apply_updates_async
            from sqlalchemy.ext.asyncio import AsyncSession

            session = AsyncSession(conn, expire_on_commit=False)
            journal = await _apply_updates_async(
                session,
                [
                    UpdatePlanRow(
                        product_id=pid,
                        sku=sku,
                        expected_current_price=price,
                        proposed_price=new_price,
                    )
                ],
            )
            self.assertEqual(len(journal), 1)
            await conn.execute(text("ROLLBACK"))
        await engine.dispose()

    async def test_execution_store_prepared_and_recovery_read(self) -> None:
        from catalog_target.ast_price_catalog_execution import async_sqlalchemy_database_url
        from catalog_target.ast_price_catalog_execution_store import (
            ensure_execution_store,
            fetch_batch_state,
            insert_prepared_batch,
        )
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        batch_id = f"test-{uuid.uuid4().hex[:8]}"
        engine = create_async_engine(async_sqlalchemy_database_url(INTEGRATION_DB))
        async with AsyncSession(engine) as session:
            async with session.begin():
                await ensure_execution_store(session)
                await insert_prepared_batch(
                    session,
                    batch_id=batch_id,
                    cohort="update",
                    updates=[{"product_id": 1, "sku": "X", "proposed_price": "1"}],
                    creates=[],
                    metadata={"test": True},
                )
            state = await fetch_batch_state(session, batch_id)
            self.assertIsNotNone(state)
            self.assertEqual(state["execution_state"], "PREPARED")
            from sqlalchemy import text

            await session.execute(
                text("DELETE FROM ast_catalog_execution_batches WHERE batch_id = :bid"),
                {"bid": batch_id},
            )
            await session.commit()
        await engine.dispose()

    async def test_create_batch_no_hesabfa(self) -> None:
        import inspect

        from catalog_target.ast_price_catalog_apply import create_products_ast_batch

        src = inspect.getsource(create_products_ast_batch)
        self.assertNotIn("ProductService", src)
        self.assertNotIn("hesabfa", src.lower())


class AstApplyPostgresMandatoryInCi(unittest.TestCase):
    def test_postgres_suite_enabled_under_ci_flag(self) -> None:
        if os.environ.get("USE_POSTGRES_TESTS", "").strip() == "1":
            self.assertTrue(RUN_PG, "USE_POSTGRES_TESTS=1 requires integration DB URL resolution")


if __name__ == "__main__":
    unittest.main()
