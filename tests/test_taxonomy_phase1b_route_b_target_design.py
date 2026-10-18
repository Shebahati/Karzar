"""Regression tests for Phase 1B Route B target taxonomy design package."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_route_b_target_design import (  # noqa: E402
    DOMAIN_CODES,
    INDUSTRIAL_OIL_CATEGORY_ID,
    MIXED_SEMANTIC_CATEGORY_IDS,
    REMOVED_L1_HELICOIL_ROOT_IDS,
    generate_route_b_package,
    load_baseline_categories,
)
from catalog_target.taxonomy_phase1b_baseline import PHASE0B_ANCHOR  # noqa: E402

PACKAGE_DIR = ROOT / "audit/taxonomy-phase1b-route-b-target-design-2026-10-18"


class RouteBTargetDesignTests(unittest.TestCase):
    def test_generate_package_passes_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            payload = generate_route_b_package(out, base_git_sha="base", head_git_sha="head")
            self.assertEqual(payload["validation"]["status"], "PASS")
            manifest = list(csv.DictReader((out / "A-135-CURRENT-TARGET-MANIFEST.csv").open()))
            self.assertEqual(len(manifest), 135)
            self.assertEqual(len({r["current_category_id"] for r in manifest}), 135)

    def test_preserved_package_when_present(self):
        if not (PACKAGE_DIR / "I-RECONCILIATION-REPORT.json").is_file():
            self.skipTest("committed package not generated yet")
        report = json.loads((PACKAGE_DIR / "I-RECONCILIATION-REPORT.json").read_text())
        self.assertEqual(report["validation"]["status"], "PASS")
        self.assertEqual(report["category_manifest_rows"], 135)

    def test_helicoil_and_oils(self):
        rows = load_baseline_categories()
        by_id = {r.category_id: r for r in rows}
        self.assertEqual(by_id[55].direct_live, 29)
        self.assertEqual(by_id[INDUSTRIAL_OIL_CATEGORY_ID].direct_live, 27)

    def test_historical_reconciliation_helicoil_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate_route_b_package(out, base_git_sha="b", head_git_sha="h")
            recon = json.loads((out / "I-RECONCILIATION-REPORT.json").read_text())
            removed = set(recon["historical_reconciliation"]["removed_category_ids"])
            self.assertTrue(REMOVED_L1_HELICOIL_ROOT_IDS.issubset(removed))

    def test_mixed_semantic_cohort_size(self):
        self.assertEqual(len(MIXED_SEMANTIC_CATEGORY_IDS), 12)

    def test_seven_domains_only(self):
        self.assertEqual(len(DOMAIN_CODES), 7)

    def test_audit_script_regression(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "audit_taxonomy_phase1b_route_b_target_design.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

    def test_live_product_count_anchor(self):
        path = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15/02-PRODUCT-CATEGORY-CENSUS.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            products = list(csv.DictReader(handle))
        live = sum(1 for p in products if not (p.get("deleted_at") or "").strip())
        self.assertEqual(live, PHASE0B_ANCHOR["live_products"])


if __name__ == "__main__":
    unittest.main()
