"""Tests for Phase 1B Route B2 architecture review package."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_route_b2_architecture_review import (  # noqa: E402
    HOLD_CATEGORY_IDS,
    PR533_MERGE_SHA,
    build_architecture_review_matrix,
    build_grouped_owner_decisions,
    build_hold_category_decision_map,
    build_product_impact,
    generate_b2_package,
    load_b2_inputs,
    recalculate_invariants,
    validate_b2_package,
)
from catalog_target.taxonomy_route_b2_deliverable_validation import (  # noqa: E402
    validate_b2_deliverables,
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

    def test_hold_categories_covered_by_decision_map(self):
        groups = build_grouped_owner_decisions(load_b2_inputs())
        hold_map = build_hold_category_decision_map(groups)
        self.assertEqual(len(hold_map), len(HOLD_CATEGORY_IDS))
        self.assertEqual({int(r["hold_category_id"]) for r in hold_map}, HOLD_CATEGORY_IDS)

    def test_generate_b2_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            payload = generate_b2_package(
                out,
                base_git_sha=PR533_MERGE_SHA,
                generator_run_git_sha="test",
            )
            self.assertEqual(payload["validation"]["status"], "PASS")
            self.assertEqual(payload["owner_decision_group_count"], 10)
            self.assertTrue((out / "C2-HOLD-CATEGORY-TO-DECISION-GROUP-MAP.csv").is_file())

    def test_validation_fails_if_category_removed(self):
        inputs = load_b2_inputs()
        inv = recalculate_invariants(inputs)
        arch = build_architecture_review_matrix(inputs)
        arch.pop()
        product_impact = build_product_impact(inputs)
        bad = validate_b2_package(inputs, inv, arch, product_impact)
        self.assertEqual(bad["status"], "FAIL")

    def test_deliverable_validation_fails_missing_hold_coverage(self):
        inputs = load_b2_inputs()
        inv = recalculate_invariants(inputs)
        arch = build_architecture_review_matrix(inputs)
        product_impact = build_product_impact(inputs)
        groups = build_grouped_owner_decisions(inputs)
        hold_map = build_hold_category_decision_map(groups)
        groups_bad = [g for g in groups if g["decision_group_id"] != "MACHINE-ACCESSORIES-163-164"]
        hold_map_bad = [r for r in hold_map if r["hold_category_id"] not in {"163", "164"}]
        from catalog_target.taxonomy_route_b2_architecture_review import (
            build_sensitive_dossier,
            build_tree_disposition,
        )

        tree = build_tree_disposition(inputs)
        sensitive = build_sensitive_dossier(inputs)
        b1_ids = {int(r["product_id"]) for r in inputs.product_map if r["product_id"].isdigit()}
        result = validate_b2_deliverables(
            inputs=inputs,
            invariants=inv,
            arch_matrix=arch,
            tree_disposition=tree,
            owner_groups=groups_bad,
            hold_category_map=hold_map_bad,
            product_impact=product_impact,
            sensitive_dossier=sensitive,
            b1_product_ids=b1_ids,
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["errors"])

    def test_deliverable_validation_fails_if_owner_marked_approved(self):
        inputs = load_b2_inputs()
        inv = recalculate_invariants(inputs)
        arch = copy.deepcopy(build_architecture_review_matrix(inputs))
        arch[0]["owner_architecture_decision_status"] = "OWNER_APPROVED"
        product_impact = build_product_impact(inputs)
        groups = build_grouped_owner_decisions(inputs)
        hold_map = build_hold_category_decision_map(groups)
        from catalog_target.taxonomy_route_b2_architecture_review import (
            build_sensitive_dossier,
            build_tree_disposition,
        )

        tree = build_tree_disposition(inputs)
        sensitive = build_sensitive_dossier(inputs)
        b1_ids = {int(r["product_id"]) for r in inputs.product_map if r["product_id"].isdigit()}
        result = validate_b2_deliverables(
            inputs=inputs,
            invariants=inv,
            arch_matrix=arch,
            tree_disposition=tree,
            owner_groups=groups,
            hold_category_map=hold_map,
            product_impact=product_impact,
            sensitive_dossier=sensitive,
            b1_product_ids=b1_ids,
        )
        self.assertEqual(result["status"], "FAIL")

    def test_category_154_descendant_distinct_matches_graph(self):
        inputs = load_b2_inputs()
        arch = build_architecture_review_matrix(inputs)
        row = next(r for r in arch if r["current_category_id"] == "154")
        self.assertEqual(int(row["descendant_inclusive_distinct_product_ids_count"]), 289)
        self.assertGreater(int(row["descendant_inclusive_distinct_product_ids_count"]), 0)

    def _deliverable_context(self):
        inputs = load_b2_inputs()
        inv = recalculate_invariants(inputs)
        arch = build_architecture_review_matrix(inputs)
        product_impact = build_product_impact(inputs)
        groups = build_grouped_owner_decisions(inputs)
        hold_map = build_hold_category_decision_map(groups)
        from catalog_target.taxonomy_route_b2_architecture_review import (
            build_sensitive_dossier,
            build_tree_disposition,
        )

        return {
            "inputs": inputs,
            "inv": inv,
            "arch": arch,
            "product_impact": product_impact,
            "groups": groups,
            "hold_map": hold_map,
            "tree": build_tree_disposition(inputs),
            "sensitive": build_sensitive_dossier(inputs),
            "b1_ids": {int(r["product_id"]) for r in inputs.product_map if r["product_id"].isdigit()},
        }

    def test_deliverable_fails_cat_154_distinct_zeroed(self):
        ctx = self._deliverable_context()
        arch = copy.deepcopy(ctx["arch"])
        row = next(r for r in arch if r["current_category_id"] == "154")
        row["descendant_inclusive_distinct_product_ids_count"] = "0"
        result = validate_b2_deliverables(
            inputs=ctx["inputs"],
            invariants=ctx["inv"],
            arch_matrix=arch,
            tree_disposition=ctx["tree"],
            owner_groups=ctx["groups"],
            hold_category_map=ctx["hold_map"],
            product_impact=ctx["product_impact"],
            sensitive_dossier=ctx["sensitive"],
            b1_product_ids=ctx["b1_ids"],
        )
        self.assertEqual(result["status"], "FAIL")

    def test_deliverable_fails_cat_163_unresolved_corrupted(self):
        ctx = self._deliverable_context()
        arch = copy.deepcopy(ctx["arch"])
        row = next(r for r in arch if r["current_category_id"] == "163")
        row["descendant_inclusive_unresolved_product_ids_count"] = "0"
        result = validate_b2_deliverables(
            inputs=ctx["inputs"],
            invariants=ctx["inv"],
            arch_matrix=arch,
            tree_disposition=ctx["tree"],
            owner_groups=ctx["groups"],
            hold_category_map=ctx["hold_map"],
            product_impact=ctx["product_impact"],
            sensitive_dossier=ctx["sensitive"],
            b1_product_ids=ctx["b1_ids"],
        )
        self.assertEqual(result["status"], "FAIL")

    def test_deliverable_fails_c2_orphan_while_groups_intact(self):
        ctx = self._deliverable_context()
        hold_map = [r for r in ctx["hold_map"] if r["hold_category_id"] != "163"]
        result = validate_b2_deliverables(
            inputs=ctx["inputs"],
            invariants=ctx["inv"],
            arch_matrix=ctx["arch"],
            tree_disposition=ctx["tree"],
            owner_groups=ctx["groups"],
            hold_category_map=hold_map,
            product_impact=ctx["product_impact"],
            sensitive_dossier=ctx["sensitive"],
            b1_product_ids=ctx["b1_ids"],
        )
        self.assertEqual(result["status"], "FAIL")

    def test_deliverable_fails_duplicate_product_row_same_id(self):
        ctx = self._deliverable_context()
        dup = copy.deepcopy(ctx["product_impact"])
        dup.append(copy.deepcopy(dup[0]))
        result = validate_b2_deliverables(
            inputs=ctx["inputs"],
            invariants=ctx["inv"],
            arch_matrix=ctx["arch"],
            tree_disposition=ctx["tree"],
            owner_groups=ctx["groups"],
            hold_category_map=ctx["hold_map"],
            product_impact=dup,
            sensitive_dossier=ctx["sensitive"],
            b1_product_ids=ctx["b1_ids"],
        )
        self.assertEqual(result["status"], "FAIL")

    def test_deliverable_fails_semantic_owner_approved(self):
        ctx = self._deliverable_context()
        arch = copy.deepcopy(ctx["arch"])
        arch[0]["b1_semantic_interpretation_evidence"] = "OWNER_APPROVED"
        result = validate_b2_deliverables(
            inputs=ctx["inputs"],
            invariants=ctx["inv"],
            arch_matrix=arch,
            tree_disposition=ctx["tree"],
            owner_groups=ctx["groups"],
            hold_category_map=ctx["hold_map"],
            product_impact=ctx["product_impact"],
            sensitive_dossier=ctx["sensitive"],
            b1_product_ids=ctx["b1_ids"],
        )
        self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
