"""Tests for Phase 1B Route B2 architecture review package."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_route_b2_architecture_review import (  # noqa: E402
    PR533_MERGE_SHA,
    build_architecture_review_matrix,
    build_product_impact,
    generate_b2_package,
    load_b2_inputs,
    recalculate_invariants,
    validate_b2_package,
)


class RouteB2ArchitectureReviewTests(unittest.TestCase):
    def test_b1_inputs_present_on_main(self):
        b1 = ROOT / "audit/taxonomy-phase1b-route-b-target-design-2026-10-18"
        self.assertTrue((b1 / "A-135-CURRENT-TARGET-MANIFEST.csv").is_file())

    def test_invariants_from_csv(self):
        inputs = load_b2_inputs()
        inv = recalculate_invariants(inputs)
        self.assertEqual(inv["current_category_count"], 135)
        self.assertEqual(inv["commerce_tree_nodes"], 123)
        self.assertEqual(inv["commerce_l1_roots"], 7)
        self.assertEqual(inv["depth_histogram"], {1: 7, 2: 42, 3: 74})
        self.assertEqual(inv["inherited_from_current_category"], 113)
        self.assertEqual(inv["selectable_leaves"], 105)
        self.assertEqual(inv["live_product_rows"], 6536)
        self.assertEqual(inv["owner_journal_exits"], 151)
        self.assertEqual(inv["owner_journal_evidence"], 111)
        self.assertEqual(inv["category_156_product_rows"], 27)
        self.assertEqual(inv["approved_executable_target_codes"], 0)
        self.assertEqual(inv["product_level_decomposition_required"], 718)

    def test_generate_b2_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            payload = generate_b2_package(
                out,
                base_git_sha=PR533_MERGE_SHA,
                generator_run_git_sha="test",
            )
            self.assertEqual(payload["validation"]["status"], "PASS")
            self.assertIn("FREEZE", payload["category_disposition_counts"])

    def test_validation_fails_if_category_removed(self):
        inputs = load_b2_inputs()
        inv = recalculate_invariants(inputs)
        arch = build_architecture_review_matrix(inputs)
        arch.pop()
        product_impact = build_product_impact(inputs)
        bad = validate_b2_package(inputs, inv, arch, product_impact)
        self.assertEqual(bad["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
