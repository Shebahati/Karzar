"""PostgreSQL-backed AST APPLY tests (skip unless integration URL is set)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

INTEGRATION_DB = os.environ.get("KARZAR_AST_INTEGRATION_DATABASE_URL", "").strip()


@unittest.skipUnless(INTEGRATION_DB, "KARZAR_AST_INTEGRATION_DATABASE_URL not set")
class AstApplyPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_mixed_update_create_productcreate_path(self) -> None:


        # Requires pre-seeded product id/sku in integration DB — documented for ops lab only.
        self.skipTest("integration fixture wiring is environment-specific")

    def test_owner_approval_bypass_blocked_in_cli(self) -> None:
        import tempfile
        from pathlib import Path

        from catalog_target.ast_price_catalog_apply import load_create_plan
        from catalog_target.sales_wave_apply import ApplyAbort

        path = Path(tempfile.mkstemp(suffix=".csv")[1])
        path.write_text(
            "sku,brand_id,category_id,name,base_price,is_available,is_active,apply_eligible,"
            "approval_status,pricing_policy_id,archive_checksum\n"
            "Z9,13,49,n Z9,10,false,true,YES,PROPOSED,AST_COOPERATION_LIST_RIAL_DIV_10,\n",
            encoding="utf-8",
        )
        self.assertEqual(len(load_create_plan(path, require_owner_approval=True)), 0)
        with self.assertRaises(ApplyAbort):
            from catalog_target.ast_price_catalog_manifest_acceptance import (
                assert_owner_manifest_bundle_gate,
            )

            assert_owner_manifest_bundle_gate(
                confirm_manifest_bundle_sha256="deadbeef",
                bundle_path=Path("/nonexistent/bundle.json"),
            )


if __name__ == "__main__":
    unittest.main()
