"""Unit tests for Phase 1B taxonomy baseline transforms."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_phase1b_baseline import (  # noqa: E402
    CANONICAL_PRESERVED_PRODUCT_METRICS,
    PHASE0B_ANCHOR,
    REMOVED_L1_HELICOIL_ROOT_IDS,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    audit_megamenu_references,
    build_category_metadata,
    compare_category_ids_phase0b,
    global_product_counts,
    helicoil_token_present,
    historical_drift,
    is_sellable_product,
    is_storefront_visible_product,
    is_tx_owner_scope_category,
    normalize_taxonomy_text,
    owner_scope_candidate,
    scan_numeric_category_dependencies,
    validate_product_census_export,
)


class TaxonomyPhase1bBaselineTests(unittest.TestCase):
    def test_selectable_leaf_depth(self):
        categories = [
            {"id": 1, "name": "L1", "parent_id": None},
            {"id": 2, "name": "L2", "parent_id": 1},
            {"id": 3, "name": "L3", "parent_id": 2},
        ]
        meta = build_category_metadata(categories)
        self.assertFalse(meta[1]["is_selectable"])
        self.assertFalse(meta[2]["is_selectable"])
        self.assertTrue(meta[3]["is_selectable"])

    def test_tx_owner_scope_ids_frozen(self):
        self.assertEqual(TX_OWNER_SCOPE_CATEGORY_IDS, frozenset({157, 158, 159, 160}))
        self.assertTrue(is_tx_owner_scope_category(158))
        self.assertFalse(is_tx_owner_scope_category(154))

    def test_owner_scope_heuristic_non_id(self):
        self.assertTrue(owner_scope_candidate("ابزار دستی عمومی", "لوازم جانبی › ابزار دستی"))
        self.assertFalse(owner_scope_candidate("کولت BT", "ابزارگیر › کولت"))

    def test_helicoil_normalization_variants(self):
        variants = [
            "هلی کویل",
            "هلی‌کویل",
            "هلی‌ کویل",
            "Helicoil",
            "HELICOIL",
            "Wire Thread Insert",
        ]
        for v in variants:
            self.assertTrue(helicoil_token_present(v), msg=v)
        self.assertIn("هلیکویل", normalize_taxonomy_text("هلی‌کویل"))

    def test_category_drift_removed_helicoil_roots(self):
        current = {55, 154}
        report = compare_category_ids_phase0b(repo_root=ROOT, current_category_ids=current)
        removed = set(report["removed_category_ids"])
        self.assertTrue(REMOVED_L1_HELICOIL_ROOT_IDS.issubset(removed) or removed)
        self.assertIn(186, removed)
        self.assertIn(187, removed)
        self.assertIn(188, removed)

    def test_megamenu_dangling_helicoil_roots(self):
        audit = audit_megamenu_references(
            megamenu_groups=[
                {
                    "slug": "helicoil",
                    "root_category_ids": "186|187|188",
                }
            ],
            live_category_ids={55},
            category_depth_by_id={55: 2},
            category_name_by_id={55: "هلی‌کویل"},
            phase0b_removed_ids=REMOVED_L1_HELICOIL_ROOT_IDS,
        )
        self.assertEqual(len(audit["missing_category_references"]), 3)
        self.assertEqual(len(audit["historical_removed_category_references"]), 3)

    def test_numeric_scan_excludes_generated_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir()
            (root / "app" / "live.py").write_text("category_id = 22\n", encoding="utf-8")
            next_dir = root / "frontend" / ".next" / "server"
            next_dir.mkdir(parents=True)
            (next_dir / "chunk.js").write_text("category_id = 999\n", encoding="utf-8")
            result = scan_numeric_category_dependencies(root)
            ids = {row["numeric_id"] for row in result["dependencies"]}
            self.assertIn("22", ids)
            self.assertNotIn("999", ids)
            self.assertGreater(result["excluded_generated_path_skips"], 0)

    def test_dependency_source_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "scripts" / "zcc_import.py").write_text("category_id = 22\n", encoding="utf-8")
            (root / "tests" / "t.py").write_text("category_id = 1\n", encoding="utf-8")
            result = scan_numeric_category_dependencies(root)
        classes = set(result["hits_by_source_class"])
        self.assertIn("SUPPLIER_IMPORT", classes)
        self.assertIn("TEST_FIXTURE", classes)
        self.assertNotIn("GENERATED_EXCLUDED", classes)

    def test_sellable_requires_price_and_image(self):
        row = {
            "deleted_at": "",
            "is_active": "true",
            "is_available": "true",
            "base_price": "1000",
            "has_valid_image": "true",
        }
        self.assertTrue(is_sellable_product(row))
        row["has_valid_image"] = "false"
        self.assertFalse(is_sellable_product(row))
        self.assertFalse(is_storefront_visible_product(row))

    def test_preserved_product_census_canonical_metrics(self):
        path = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15/02-PRODUCT-CATEGORY-CENSUS.csv"
        if not path.is_file():
            self.skipTest("baseline product census missing")
        with path.open(encoding="utf-8", newline="") as handle:
            products = list(csv.DictReader(handle))
        validate_product_census_export(products)
        counts = global_product_counts(products)
        self.assertEqual(counts, CANONICAL_PRESERVED_PRODUCT_METRICS)

    def test_historical_drift_product_deltas_from_preserved_census(self):
        path = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15/02-PRODUCT-CATEGORY-CENSUS.csv"
        drift_path = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15/10-HISTORICAL-DRIFT.json"
        if not path.is_file() or not drift_path.is_file():
            self.skipTest("baseline artifacts missing")
        import json

        with path.open(encoding="utf-8", newline="") as handle:
            products = list(csv.DictReader(handle))
        counts = global_product_counts(products)
        structure = json.loads(drift_path.read_text(encoding="utf-8"))["current_structure"]
        drift = historical_drift(structure, counts)
        self.assertEqual(drift["live_products_delta"], 0)
        self.assertEqual(drift["sellable_delta"], counts["sellable"] - PHASE0B_ANCHOR["sellable"])
        self.assertEqual(drift["sellable_delta"], 4)
        self.assertEqual(drift["visible_delta"], 0)

    def test_product_census_missing_columns_fail_closed(self):
        with self.assertRaises(RuntimeError):
            validate_product_census_export([{"product_id": "1"}])

    def test_manifest_row_count_from_census(self):
        census = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15/01-CATEGORY-CENSUS.csv"
        manifest = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15/05-PHASE1B-CURRENT-TARGET-WORKING-MANIFEST.csv"
        if not census.is_file() or not manifest.is_file():
            self.skipTest("baseline artifacts missing")
        with census.open(encoding="utf-8", newline="") as handle:
            cat_count = sum(1 for _ in csv.DictReader(handle))
        with manifest.open(encoding="utf-8", newline="") as handle:
            man_rows = list(csv.DictReader(handle))
        self.assertEqual(cat_count, 135)
        self.assertEqual(len(man_rows), 135)
        self.assertTrue(all(r.get("review_status") == "UNREVIEWED" for r in man_rows))


if __name__ == "__main__":
    unittest.main()
