"""Unit tests for استاندارد leaf remediation helpers (no DB)."""

from scripts.remediate_standard_leaves import (
    analyze_insert_root,
    build_children_index,
    build_plan,
    direct_counts_from_flat,
    is_empty_deletable_leaf,
    is_padding_name,
    is_standard_name,
    suggest_rename,
    unique_rename,
)


class TestStandardNameDetection:
    def test_exact_and_prefixed(self):
        assert is_standard_name("استاندارد")
        assert is_standard_name("استاندارد — برقو")
        assert is_standard_name("استاندارد - مته")
        assert is_standard_name("استاندارد (12)")
        assert not is_standard_name("برقو")
        assert not is_standard_name("برقو — عمومی")

    def test_padding_includes_general_suffix(self):
        assert is_padding_name("برقو — عمومی")
        assert is_padding_name("سری عمومی")
        assert is_padding_name("استاندارد — حدیده")


class TestSuggestRename:
    def test_strip_meaningful_suffix(self):
        assert suggest_rename("استاندارد — سری اقتصادی", "مته") == "سری اقتصادی"

    def test_parent_duplicate_padding_keeps_l3_label(self):
        assert suggest_rename("استاندارد — برقو", "برقو") == "برقو — عمومی"

    def test_exact_standard_under_parent(self):
        assert suggest_rename("استاندارد", "انگشتی HSS") == "انگشتی HSS — عمومی"

    def test_already_general_not_renamed(self):
        assert suggest_rename("برقو — عمومی", "برقو") is None

    def test_never_suggests_moving_to_parent_alone(self):
        # Buyer-facing rename must remain a distinct L3 label, not equal to bare parent
        # when we need uniqueness — parent duplicate becomes «Parent — عمومی».
        assert suggest_rename("استاندارد — قلاویز دستی", "قلاویز دستی") == "قلاویز دستی — عمومی"


class TestUniqueRename:
    def test_avoids_sibling_collision(self):
        got = unique_rename(
            "برقو — عمومی",
            category_id=140,
            sibling_names={"برقو — عمومی"},
            used_names=set(),
        )
        assert got == "برقو — عمومی (140)"


class TestDeleteSafety:
    def test_empty_leaf_deletable(self):
        cat = {"id": 1, "is_leaf": True, "product_count": 0}
        assert is_empty_deletable_leaf(cat, child_count=0, direct_count=0)

    def test_blocks_when_products_or_children(self):
        cat = {"id": 1, "is_leaf": True, "product_count": 5}
        assert not is_empty_deletable_leaf(cat, child_count=0, direct_count=5)
        cat0 = {"id": 2, "is_leaf": False, "product_count": 0}
        assert not is_empty_deletable_leaf(cat0, child_count=2, direct_count=0)


class TestInsertAnalysisAndPlan:
    def _cats(self):
        # Root Insert with padding-only empty L2/L3, plus one populated استاندارد leaf elsewhere.
        return [
            {
                "id": 3,
                "name": "اینسرت",
                "parent_id": None,
                "depth": 1,
                "is_leaf": False,
                "product_count": 0,
            },
            {
                "id": 33,
                "name": "اینسرت تراش CNC",
                "parent_id": 3,
                "depth": 2,
                "is_leaf": False,
                "product_count": 0,
            },
            {
                "id": 126,
                "name": "استاندارد — اینسرت تراش CNC",
                "parent_id": 33,
                "depth": 3,
                "is_leaf": True,
                "product_count": 0,
            },
            {
                "id": 10,
                "name": "برقو",
                "parent_id": None,
                "depth": 1,
                "is_leaf": False,
                "product_count": 41,
            },
            {
                "id": 11,
                "name": "برقو",
                "parent_id": 10,
                "depth": 2,
                "is_leaf": False,
                "product_count": 41,
            },
            {
                "id": 140,
                "name": "استاندارد — برقو",
                "parent_id": 11,
                "depth": 3,
                "is_leaf": True,
                "product_count": 41,
            },
        ]

    def test_direct_counts_for_leaves(self):
        direct = direct_counts_from_flat(self._cats())
        assert direct[140] == 41
        assert direct[126] == 0
        assert direct[3] == 0

    def test_insert_collapse_decision(self):
        cats = self._cats()
        children = build_children_index(cats)
        direct = direct_counts_from_flat(cats)
        analysis = analyze_insert_root(cats, children=children, direct=direct)
        assert analysis["found"] is True
        assert analysis["decision"] == "collapse_padding_only_empty"
        assert 126 in analysis["collapse_order_ids"]
        assert 3 in analysis["collapse_order_ids"]

    def test_build_plan_rename_and_delete_split(self):
        plan = build_plan(self._cats())
        rename_ids = {r["id"] for r in plan["rename_plan"]}
        delete_ids = {r["id"] for r in plan["delete_plan"]}
        assert 140 in rename_ids
        assert plan["rename_plan"][0]["to"] == "برقو — عمومی"
        assert 126 in delete_ids
        assert 140 not in delete_ids
        # Never plan to move products off L3
        assert all(r["reason"] == "rename_padding_keep_l3" for r in plan["rename_plan"])
