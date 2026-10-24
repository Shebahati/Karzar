"""AST guarded apply gates — unit tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.ast_price_catalog_apply import (  # noqa: E402
    assert_apply_gates,
    load_update_plan,
)
from catalog_target.ast_price_catalog_constants import SOURCE_ARCHIVE_SHA256  # noqa: E402
from catalog_target.sales_wave_apply import ApplyAbort  # noqa: E402


class AstApplyGateTests(unittest.TestCase):
    def test_blocks_without_owner_auth(self):
        with self.assertRaises(ApplyAbort):
            assert_apply_gates(
                apply=True,
                rollback=False,
                owner_authorization="WRONG",
                confirm_production_write=True,
                confirm_source_sha256=SOURCE_ARCHIVE_SHA256,
                confirm_update_manifest_sha256="a",
                confirm_create_manifest_sha256="b",
                update_manifest_sha256="a",
                create_manifest_sha256="b",
                confirm_update_count=1,
                confirm_create_count=0,
                update_count=1,
                create_count=0,
            )

    def test_blocks_missing_explicit_confirm_counts(self):
        with self.assertRaises(ApplyAbort):
            assert_apply_gates(
                apply=True,
                rollback=False,
                owner_authorization="AUTHORIZE_AST_PRICE_CATALOG_APPLY",
                confirm_production_write=True,
                confirm_source_sha256=SOURCE_ARCHIVE_SHA256,
                confirm_update_manifest_sha256="a",
                confirm_create_manifest_sha256="b",
                update_manifest_sha256="a",
                create_manifest_sha256="b",
                confirm_update_count=-1,
                confirm_create_count=0,
                update_count=1,
                create_count=0,
            )

    def test_load_update_skips_non_ok_validation(self):
        path = Path(tempfile.mkstemp(suffix=".csv")[1])
        path.write_text(
            "product_id,sku,expected_current_price,proposed_price,validation_result\n"
            "1,A,100,200,OK\n"
            "2,B,100,200,LARGE_INCREASE_REVIEW\n",
            encoding="utf-8",
        )
        rows = load_update_plan(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].product_id, 1)


if __name__ == "__main__":
    unittest.main()
