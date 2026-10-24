"""PostgreSQL canary stage + gate integration tests (CI: USE_POSTGRES_TESTS=1)."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.ast_price_catalog_apply import UpdatePlanRow  # noqa: E402
from catalog_target.ast_price_catalog_backup_attestation import (  # noqa: E402
    assert_production_backup_attestation_gate,
)
from catalog_target.ast_price_catalog_database_identity import (  # noqa: E402
    fetch_database_identity_fingerprint,
)
from catalog_target.ast_price_catalog_execution import (  # noqa: E402
    _apply_updates_async,
    async_sqlalchemy_database_url,
)
from catalog_target.ast_price_catalog_execution_store import (  # noqa: E402
    assert_update_product_ids_not_committed,
    committed_update_product_ids,
    ensure_execution_store,
    insert_prepared_batch,
    mark_batch_committed,
)
from catalog_target.ast_price_catalog_update_canary import select_canary_partitions  # noqa: E402
from catalog_target.sales_wave_apply import ApplyAbort  # noqa: E402
from tests.test_ast_price_catalog_apply_postgres import INTEGRATION_DB, RUN_PG  # noqa: E402


async def _ensure_execution_table(session) -> None:
    try:
        await ensure_execution_store(session)
    except ApplyAbort:
        await session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ast_catalog_execution_batches (
                    batch_id TEXT PRIMARY KEY,
                    execution_state TEXT NOT NULL,
                    cohort TEXT NOT NULL,
                    mutation_plan JSONB NOT NULL,
                    mutation_result JSONB,
                    post_commit_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )


@unittest.skipUnless(RUN_PG, "PostgreSQL integration URL not configured")
class AstCanaryPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_stage_partitions_do_not_double_update(self) -> None:
        audit = ROOT / "audit/ast-price-and-catalog-20261024"
        update_path = audit / "UPDATE_PRODUCTS.csv"
        if not update_path.is_file():
            self.skipTest("UPDATE_PRODUCTS.csv not present locally")
        with update_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        parts = select_canary_partitions(rows)
        master = "test-master-sha"
        batch_id = f"test-{uuid.uuid4().hex[:8]}"
        pid = int(parts["stage1"][0]["product_id"])
        engine = create_async_engine(async_sqlalchemy_database_url(INTEGRATION_DB))
        async with AsyncSession(engine) as session:
            async with session.begin():
                await _ensure_execution_table(session)
                await insert_prepared_batch(
                    session,
                    batch_id=batch_id,
                    cohort="update",
                    updates=[{"product_id": pid, "sku": "X", "proposed_price": "1"}],
                    creates=[],
                    metadata={"master_update_manifest_sha256": master, "update_stage": "stage1"},
                )
                await mark_batch_committed(
                    session,
                    batch_id=batch_id,
                    update_journal=[{"product_id": pid, "sku": "X", "new_price": "1"}],
                    create_journal=[],
                )
            with self.assertRaises(ApplyAbort):
                await assert_update_product_ids_not_committed(
                    session,
                    product_ids=[pid],
                    master_update_manifest_sha256=master,
                )
            committed = await committed_update_product_ids(session, master_update_manifest_sha256=master)
            self.assertIn(pid, committed)
            await session.execute(
                text("DELETE FROM ast_catalog_execution_batches WHERE batch_id = :b"),
                {"b": batch_id},
            )
            await session.commit()
        await engine.dispose()

    async def test_database_identity_fingerprint_readable(self) -> None:
        identity = await fetch_database_identity_fingerprint(INTEGRATION_DB)
        self.assertIn("db=", identity)

    async def test_real_transaction_rollback(self) -> None:
        engine = create_async_engine(async_sqlalchemy_database_url(INTEGRATION_DB))
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT id, sku, base_price::text FROM products WHERE deleted_at IS NULL LIMIT 1")
                )
            ).first()
            self.assertIsNotNone(row)
            pid, sku, price = int(row[0]), str(row[1]), Decimal(str(row[2]))
            session = AsyncSession(conn, expire_on_commit=False)
            await _apply_updates_async(
                session,
                [
                    UpdatePlanRow(
                        product_id=pid,
                        sku=sku,
                        expected_current_price=price,
                        proposed_price=price + Decimal("1"),
                    )
                ],
            )
            await conn.execute(text("ROLLBACK"))
        await engine.dispose()

    def test_backup_gate_rejects_missing_verified_identity(self) -> None:
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text(
            json.dumps(
                {
                    "backup_completion_status": "COMPLETED",
                    "restore_validation_status": "VERIFIED",
                    "backup_artifact_sha256": "abc",
                    "backup_artifact_location": "/tmp/nope",
                    "backup_created_at": "2026-10-24T10:00:00Z",
                    "attestation_signed_at": "2026-10-24T11:00:00Z",
                    "production_database_identity": "db=x",
                    "attested_by": "ops",
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ApplyAbort):
            assert_production_backup_attestation_gate(
                attestation_path=path,
                confirm_backup_artifact_sha256="abc",
                verified_database_identity="",
            )


if __name__ == "__main__":
    unittest.main()
