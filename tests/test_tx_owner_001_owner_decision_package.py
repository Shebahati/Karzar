"""Tests for TX-OWNER-001 Owner decision package generator."""

from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.tx_owner_001_external_sources import APPROVED_DOMAIN_CODES  # noqa: E402
from catalog_target.tx_owner_001_semantic_review import load_cohort_products  # noqa: E402

PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
BASELINE = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15"
REVIEW = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review"


class TxOwner001OwnerDecisionPackageTests(unittest.TestCase):
    def test_package_reconciliation_if_generated(self):
        recon_path = PKG / "06-RECONCILIATION-262.json"
        if not recon_path.is_file():
            self.skipTest("owner package not generated")
        recon = json.loads(recon_path.read_text(encoding="utf-8"))
        self.assertEqual(recon["unique_product_ids"], 262)
        self.assertEqual(len(recon["product_ids_accounted"]), 262)
        self.assertFalse(recon["category_154_included"])
        self.assertFalse(recon["category_156_oils_included"])

    def test_critical_matrix_twenty_if_generated(self):
        path = PKG / "01-CRITICAL-20-EVIDENCE-MATRIX.csv"
        if not path.is_file():
            self.skipTest("owner package not generated")
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 20)
        ids = {int(r["product_id"]) for r in rows}
        self.assertIn(2915, ids)
        self.assertIn(3238, ids)

    def test_low_confidence_register_176_if_generated(self):
        path = PKG / "03-LOW-CONFIDENCE-EXIT-RISK-REGISTER.csv"
        if not path.is_file():
            self.skipTest("owner package not generated")
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 176)

    def test_owner_journal_no_prefilled_approval(self):
        path = PKG / "07-OWNER-APPROVAL-JOURNAL-TEMPLATE.csv"
        if not path.is_file():
            self.skipTest("owner package not generated")
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 262)
        self.assertTrue(all(r["authorization_status"] == "PENDING" for r in rows))
        self.assertTrue(all(r["owner_decision"] == "" for r in rows))

    def test_cohort_excludes_154_and_156_oils(self):
        cohort = load_cohort_products(
            BASELINE / "02-PRODUCT-CATEGORY-CENSUS.csv",
            category_census_path=BASELINE / "01-CATEGORY-CENSUS.csv",
        )
        cats = {int(r["category_id"]) for r in cohort}
        self.assertTrue(cats <= {158, 160})

    def test_pr499_domains_only_seven(self):
        path = REVIEW / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                code = row.get("proposed_industrial_domain_code") or ""
                if code:
                    self.assertIn(code, APPROVED_DOMAIN_CODES)


if __name__ == "__main__":
    unittest.main()
