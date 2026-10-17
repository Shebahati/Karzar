"""Tests for TX-OWNER-001 product semantic review cohort and partitions."""

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
from catalog_target.tx_owner_001_semantic_review import (  # noqa: E402
    _classify,
    build_owner_queue,
    build_product_reviews,
    disposition_counts,
    load_cohort_products,
    validate_primary_partition,
)

BASELINE = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15"
REVIEW_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review"


class TxOwner001SemanticReviewTests(unittest.TestCase):
    def _cohort(self):
        return load_cohort_products(
            BASELINE / "02-PRODUCT-CATEGORY-CENSUS.csv",
            category_census_path=BASELINE / "01-CATEGORY-CENSUS.csv",
        )

    def test_cohort_reconciliation_262(self):
        cohort = self._cohort()
        self.assertEqual(len(cohort), 262)
        reviews = build_product_reviews(cohort)
        validate_primary_partition(reviews)
        self.assertEqual(sum(disposition_counts(reviews).values()), 262)

    def test_cnc_woodworking_not_auto_metalworking(self):
        cohort = self._cohort()
        row = next(r for r in cohort if int(r["product_id"]) == 3102)
        review = _classify(row)
        self.assertEqual(review.proposed_disposition, "CATALOG_EXIT_CANDIDATE")
        self.assertNotEqual(review.proposed_industrial_domain_code, "KZ.DOM.CUTTING")

    def test_grooving_needs_more_evidence(self):
        cohort = self._cohort()
        row = next(r for r in cohort if int(r["product_id"]) == 3090)
        review = _classify(row)
        self.assertEqual(review.proposed_disposition, "NEEDS_MORE_EVIDENCE")

    def test_finishing_blade_ambiguous(self):
        cohort = self._cohort()
        row = next(r for r in cohort if int(r["product_id"]) == 3101)
        review = _classify(row)
        self.assertEqual(review.proposed_disposition, "NEEDS_MORE_EVIDENCE")

    def test_finger_joint_bladekat_exit(self):
        cohort = self._cohort()
        row = next(r for r in cohort if int(r["product_id"]) == 3116)
        review = _classify(row)
        self.assertEqual(review.proposed_disposition, "CATALOG_EXIT_CANDIDATE")

    def test_collet_not_toolholding_domain(self):
        cohort = self._cohort()
        row = next(r for r in cohort if int(r["product_id"]) == 5194)
        review = _classify(row)
        self.assertNotEqual(review.proposed_industrial_domain_code, "KZ.DOM.TOOLHOLDING")
        self.assertEqual(review.proposed_disposition, "CATALOG_EXIT_CANDIDATE")
        self.assertEqual(review.confidence_basis, "OEM_DOCUMENTED")

    def test_pneumatic_die_grinder_not_cutting_tools(self):
        cohort = self._cohort()
        row = next(r for r in cohort if int(r["product_id"]) == 5190)
        review = _classify(row)
        self.assertNotEqual(review.proposed_industrial_domain_code, "KZ.DOM.CUTTING")
        self.assertEqual(review.proposed_disposition, "CATALOG_EXIT_CANDIDATE")

    def test_heuristic_not_high_strength_on_regex_only(self):
        cohort = self._cohort()
        row = next(r for r in cohort if int(r["product_id"]) == 3008)
        review = _classify(row)
        self.assertEqual(review.proposed_disposition, "CATALOG_EXIT_CANDIDATE")
        self.assertNotEqual(review.evidence_strength, "HIGH")

    def test_owner_queue_covers_all_products(self):
        cohort = self._cohort()
        reviews = build_product_reviews(cohort)
        queue = build_owner_queue(reviews)
        self.assertEqual(len(queue), 262)

    def test_industrial_exceptions_in_owner_queue(self):
        cohort = self._cohort()
        reviews = build_product_reviews(cohort)
        queue = build_owner_queue(reviews)
        exceptions = {r["product_id"] for r in reviews if r["proposed_disposition"] == "INDUSTRIAL_EXCEPTION_CANDIDATE"}
        queued = {r["product_id"] for r in queue if r["proposed_disposition"] == "INDUSTRIAL_EXCEPTION_CANDIDATE"}
        self.assertEqual(exceptions, queued)

    def test_proposed_domains_are_approved_only(self):
        cohort = self._cohort()
        reviews = build_product_reviews(cohort)
        for row in reviews:
            code = row.get("proposed_industrial_domain_code") or ""
            if code:
                self.assertIn(code, APPROVED_DOMAIN_CODES)

    def test_generated_artifacts_if_present(self):
        master = REVIEW_DIR / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"
        if not master.is_file():
            self.skipTest("review artifacts not generated")
        with master.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 262)
        recon = json.loads((REVIEW_DIR / "08-COHORT-RECONCILIATION.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["unique_product_count"], 262)
        self.assertEqual(recon["owner_queue_row_count"], 262)


if __name__ == "__main__":
    unittest.main()
