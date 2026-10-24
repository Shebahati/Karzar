"""PostgreSQL-backed AST APPLY tests (CI: USE_POSTGRES_TESTS=1)."""

from __future__ import annotations

import os
import sys
import unittest
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


@unittest.skipUnless(INTEGRATION_DB, "PostgreSQL integration URL not configured")
class AstApplyPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_post_commit_verify_empty_cohort_on_live_db(self) -> None:
        from catalog_target.ast_price_catalog_execution import verify_committed_cohort

        report = await verify_committed_cohort(
            INTEGRATION_DB,
            update_journal=[],
            create_journal=[],
            create_plan=[],
        )
        self.assertTrue(report.ok)

    async def test_async_sqlalchemy_url_normalization(self) -> None:
        from catalog_target.ast_price_catalog_execution import async_sqlalchemy_database_url

        self.assertTrue(
            async_sqlalchemy_database_url("postgresql://u:p@localhost/db").startswith("postgresql+asyncpg://")
        )


class AstApplyGatePostgresFreeTests(unittest.TestCase):
    def test_owner_approval_bypass_blocked(self) -> None:
        import tempfile

        from catalog_target.ast_price_catalog_apply import load_create_plan
        from catalog_target.ast_price_catalog_constants import PRICING_POLICY_ID
        from catalog_target.sales_wave_apply import ApplyAbort

        path = Path(tempfile.mkstemp(suffix=".csv")[1])
        path.write_text(
            "sku,brand_id,category_id,name,base_price,is_available,is_active,apply_eligible,"
            "approval_status,pricing_policy_id,archive_checksum\n"
            f"Z9,13,49,n Z9,10,false,true,YES,PROPOSED,{PRICING_POLICY_ID},\n",
            encoding="utf-8",
        )
        self.assertEqual(len(load_create_plan(path, require_owner_approval=True)), 0)
        with self.assertRaises(ApplyAbort):
            from catalog_target.ast_price_catalog_manifest_acceptance import assert_owner_manifest_bundle_gate

            assert_owner_manifest_bundle_gate(
                confirm_manifest_bundle_sha256="deadbeef",
                bundle_path=Path("/nonexistent/bundle.json"),
            )


if __name__ == "__main__":
    unittest.main()
