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

from catalog_target.tx_owner_001_semantic_review import (  # noqa: E402
    build_product_reviews,
    disposition_counts,
    load_cohort_products,
    validate_primary_partition,
)

BASELINE = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15"
REVIEW_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review"


class TxOwner001SemanticReviewTests(unittest.TestCase):
    def test_cohort_reconciliation_262(self):
        cohort = load_cohort_products(
            BASELINE / "02-PRODUCT-CATEGORY-CENSUS.csv",
            category_census_path=BASELINE / "01-CATEGORY-CENSUS.csv",
        )
        self.assertEqual(len(cohort), 262)
        reviews = build_product_reviews(cohort)
        validate_primary_partition(reviews)
        counts = disposition_counts(reviews)
        self.assertEqual(sum(counts.values()), 262)

    def test_generated_artifacts_if_present(self):
        master = REVIEW_DIR / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"
        if not master.is_file():
            self.skipTest("review artifacts not generated")
        with master.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 262)
        recon = json.loads((REVIEW_DIR / "08-COHORT-RECONCILIATION.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["unique_product_count"], 262)
        self.assertTrue(recon["mutually_exclusive_primary_disposition"])


if __name__ == "__main__":
    unittest.main()
