"""Unit tests for Phase 1B taxonomy baseline transforms."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_phase1b_baseline import (  # noqa: E402
    build_category_metadata,
    is_sellable_product,
    is_storefront_visible_product,
    owner_scope_candidate,
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
        self.assertFalse(meta[2]["is_selectable"])  # non-leaf L2
        self.assertTrue(meta[3]["is_selectable"])

    def test_owner_scope_heuristic(self):
        self.assertTrue(owner_scope_candidate("ابزار دستی عمومی", "لوازم جانبی › ابزار دستی"))
        self.assertFalse(owner_scope_candidate("کولت BT", "ابزارگیر › کولت"))

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


if __name__ == "__main__":
    unittest.main()
