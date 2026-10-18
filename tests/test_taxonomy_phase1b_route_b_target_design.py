"""Regression tests for Phase 1B Route B target taxonomy design package."""

from __future__ import annotations

import copy
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

from catalog_target.taxonomy_phase1b_baseline import PHASE0B_ANCHOR  # noqa: E402
from catalog_target.taxonomy_route_b_semantics import HISTORICAL_DEPRECATED_CODES  # noqa: E402
from catalog_target.taxonomy_route_b_target_design import (  # noqa: E402
    INDUSTRIAL_OIL_CATEGORY_ID,
    MIXED_SEMANTIC_CATEGORY_IDS,
    generate_route_b_package,
    load_baseline_categories,
    load_baseline_products,
    load_owner_authorization_journals,
)
from catalog_target.taxonomy_route_b_validation import validate_route_b_package  # noqa: E402

PACKAGE_DIR = ROOT / "audit/taxonomy-phase1b-route-b-target-design-2026-10-18"


class RouteBTargetDesignTests(unittest.TestCase):
    def test_generate_package_passes_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            payload = generate_route_b_package(
                out,
                pinned_input_git_sha="pin",
                generator_run_git_sha="run",
            )
            self.assertEqual(payload["validation"]["status"], "PASS")
            with (out / "A-135-CURRENT-TARGET-MANIFEST.csv").open(encoding="utf-8", newline="") as handle:
                manifest = list(csv.DictReader(handle))
            self.assertEqual(len(manifest), 135)

    def test_owner_journal_not_pr499_substitution(self):
        journal = load_owner_authorization_journals()
        self.assertEqual(len(journal), 262)
        exits = sum(1 for r in journal.values() if r["owner_decision"] == "APPROVE_CATALOG_EXIT")
        evidence = sum(1 for r in journal.values() if r["owner_decision"] == "REQUEST_MORE_EVIDENCE")
        self.assertEqual(exits, 151)
        self.assertEqual(evidence, 111)

    def test_product_map_uses_owner_decision_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate_route_b_package(out, pinned_input_git_sha="p", generator_run_git_sha="r")
            with (out / "D-PRODUCT-MAPPING-READINESS.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            tx = [r for r in rows if r["tx_owner_cohort"] == "YES"]
            self.assertEqual(len(tx), 262)
            for row in tx:
                self.assertIn(row["owner_authoritative_decision"], ("APPROVE_CATALOG_EXIT", "REQUEST_MORE_EVIDENCE"))
                self.assertEqual(row["approved_target_category_code"], "")
                self.assertNotEqual(row["mapping_authorization"], "APPROVED_FOR_APPLY")

    def test_validation_fails_on_duplicate_registry_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate_route_b_package(out, pinned_input_git_sha="p", generator_run_git_sha="r")
            recon = json.loads((out / "I-RECONCILIATION-REPORT.json").read_text())
            with (out / "A-135-CURRENT-TARGET-MANIFEST.csv").open(encoding="utf-8", newline="") as handle:
                manifest = list(csv.DictReader(handle))
            with (out / "C-TARGET-TAXONOMY-TREE.csv").open(encoding="utf-8", newline="") as handle:
                tree = list(csv.DictReader(handle))
            with (out / "D-PRODUCT-MAPPING-READINESS.csv").open(encoding="utf-8", newline="") as handle:
                products = list(csv.DictReader(handle))
            with (out / "E-TARGET-IDENTITY-REGISTRY.csv").open(encoding="utf-8", newline="") as handle:
                registry = list(csv.DictReader(handle))
            registry.append(copy.deepcopy(registry[0]))
            journal = load_owner_authorization_journals()
            bad = validate_route_b_package(
                manifest=manifest,
                commerce_tree=tree,
                product_rows=products,
                identity_registry=registry,
                owner_journal=journal,
                reconciliation=recon["historical_reconciliation"],
                oil_product_ids=set(recon["product_summary"]["category_156_oil_product_ids"]),
                inputs_products=load_baseline_products(),
            )
            self.assertEqual(bad["status"], "FAIL")

    def test_historical_helicoil_deprecated_codes_unique(self):
        self.assertEqual(len(set(HISTORICAL_DEPRECATED_CODES.values())), 3)

    def test_commerce_depth_parent_plus_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate_route_b_package(out, pinned_input_git_sha="p", generator_run_git_sha="r")
            with (out / "C-TARGET-TAXONOMY-TREE.csv").open(encoding="utf-8", newline="") as handle:
                tree = list(csv.DictReader(handle))
            by_code = {r["commerce_category_code"]: r for r in tree}
            for row in tree:
                parent = (row.get("parent_commerce_code") or "").strip()
                if not parent:
                    self.assertEqual(int(row["commerce_depth"]), 1)
                    continue
                self.assertEqual(
                    int(row["commerce_depth"]),
                    int(by_code[parent]["commerce_depth"]) + 1,
                )
            metrology_l3 = [
                r
                for r in tree
                if r["scientific_domain_code"] == "KZ.DOM.METROLOGY"
                and int(r["commerce_depth"]) == 3
                and r["node_kind"] == "BUYER_COMMERCE_PUBLISHABLE"
            ]
            self.assertEqual(len(metrology_l3), 39)

    def test_validation_fails_on_incorrect_commerce_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate_route_b_package(out, pinned_input_git_sha="p", generator_run_git_sha="r")
            recon = json.loads((out / "I-RECONCILIATION-REPORT.json").read_text())
            with (out / "A-135-CURRENT-TARGET-MANIFEST.csv").open(encoding="utf-8", newline="") as handle:
                manifest = list(csv.DictReader(handle))
            with (out / "C-TARGET-TAXONOMY-TREE.csv").open(encoding="utf-8", newline="") as handle:
                tree = list(csv.DictReader(handle))
            with (out / "D-PRODUCT-MAPPING-READINESS.csv").open(encoding="utf-8", newline="") as handle:
                products = list(csv.DictReader(handle))
            with (out / "E-TARGET-IDENTITY-REGISTRY.csv").open(encoding="utf-8", newline="") as handle:
                registry = list(csv.DictReader(handle))
            leaf = next(r for r in tree if int(r["commerce_depth"]) == 3)
            leaf["commerce_depth"] = "2"
            bad = validate_route_b_package(
                manifest=manifest,
                commerce_tree=tree,
                product_rows=products,
                identity_registry=registry,
                owner_journal=load_owner_authorization_journals(),
                reconciliation=recon["historical_reconciliation"],
                oil_product_ids=set(recon["product_summary"]["category_156_oil_product_ids"]),
                inputs_products=load_baseline_products(),
            )
            self.assertEqual(bad["status"], "FAIL")

    def test_commerce_tree_has_single_root_tier(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate_route_b_package(out, pinned_input_git_sha="p", generator_run_git_sha="r")
            with (out / "C-TARGET-TAXONOMY-TREE.csv").open(encoding="utf-8", newline="") as handle:
                tree = list(csv.DictReader(handle))
            roots = [r for r in tree if not r.get("parent_commerce_code")]
            self.assertEqual(len(roots), 7)
            legacy_l1_in_tree = [
                r for r in tree if r.get("source_current_category_id") in {"1", "2", "56", "154", "155"}
            ]
            self.assertEqual(legacy_l1_in_tree, [])

    def test_no_summary_row_in_product_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate_route_b_package(out, pinned_input_git_sha="p", generator_run_git_sha="r")
            with (out / "D-PRODUCT-MAPPING-READINESS.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(all(r["product_id"].isdigit() for r in rows))
            self.assertEqual(len(rows), PHASE0B_ANCHOR["live_products"])

    def test_audit_script_regression(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "audit_taxonomy_phase1b_route_b_target_design.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

    def test_preserved_package_when_present(self):
        if not (PACKAGE_DIR / "I-RECONCILIATION-REPORT.json").is_file():
            self.skipTest("package not committed")
        report = json.loads((PACKAGE_DIR / "I-RECONCILIATION-REPORT.json").read_text())
        self.assertEqual(report["validation"]["status"], "PASS")

    def test_mixed_semantic_cohort_size(self):
        self.assertEqual(len(MIXED_SEMANTIC_CATEGORY_IDS), 12)

    def test_category_156_oil_count(self):
        rows = load_baseline_categories()
        by_id = {r.category_id: r for r in rows}
        self.assertEqual(by_id[INDUSTRIAL_OIL_CATEGORY_ID].direct_live, 27)


if __name__ == "__main__":
    unittest.main()
