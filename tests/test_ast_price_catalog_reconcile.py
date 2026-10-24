"""AST catalog reconcile — deterministic unit tests (no DB)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.ast_price_catalog_constants import SOURCE_ARCHIVE_SHA256  # noqa: E402
from catalog_target.ast_price_catalog_reconcile import (  # noqa: E402
    build_authoritative_rows,
    proposed_customer_price,
    run_reconcile,
)


class AstReconcileTests(unittest.TestCase):
    def test_proposed_price_rial_div_10(self):
        price, policy, _ = proposed_customer_price(897_000_000, "20")
        self.assertEqual(price, Decimal("89700000"))
        self.assertEqual(policy, "AST_COOPERATION_LIST_RIAL_DIV_10")

    def test_pricing_policy_hold_on_review_label(self):
        price, policy, _ = proposed_customer_price(100_000_000, "15_DEVICE_OR_10_SPARE_REVIEW")
        self.assertIsNone(price)
        self.assertIn("HOLD", policy)

    def test_authoritative_rejects_conflict_keys(self):
        rows = [
            {
                "brand_hint": "ET",
                "code_candidate": "X-1",
                "status": "CONFLICTING_SOURCE_QUOTES_HOLD",
                "source_date": "1405/07/07",
            },
            {
                "brand_hint": "ET",
                "code_candidate": "X-1",
                "status": "CANDIDATE_EXACT_VISUAL_QA_REQUIRED",
                "source_date": "1405/07/21",
                "source_price_rial": "1000000",
                "cash_discount_label": "20",
            },
        ]
        auth, rejected, _ = build_authoritative_rows(rows)
        self.assertEqual(len(auth), 0)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].primary_outcome, "REJECTED")

    def test_run_reconcile_ledger_balances(self):
        audit = Path(__file__).resolve().parents[1] / "audit/ast-price-and-catalog-20261024"
        if not (audit / "source/AST(2).zip").is_file():
            self.skipTest("local audit bundle missing")
        report = run_reconcile(
            audit_dir=Path(tempfile.mkdtemp(prefix="ast-audit-")),
            candidates_csv=audit / "work/supplier_price_candidates_NOT_FOR_APPLY.csv",
            catalog_csv=audit / "CATALOG_SNAPSHOT_20261024.csv",
            categories_csv=audit / "CATEGORIES_SNAPSHOT_20261024.csv",
            source_docs_csv=audit / "work/source_documents.csv",
            source_zip=audit / "source/AST(2).zip",
        )
        self.assertTrue(report["ledger_balance_check"])
        self.assertTrue(report["inclusive_outcome_balanced"])
        self.assertEqual(report["source_archive_sha256"], SOURCE_ARCHIVE_SHA256)


if __name__ == "__main__":
    unittest.main()
