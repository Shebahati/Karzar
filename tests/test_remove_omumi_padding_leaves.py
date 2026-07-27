"""Padding «عمومی» leaf detection and remove-plan helpers."""

from app.utils.category_padding import is_padding_leaf_name, plan_omumi_removals


class TestIsPaddingLeafName:
    def test_exact_omumi(self):
        assert is_padding_leaf_name("عمومی") is True
        assert is_padding_leaf_name("  عمومی  ") is True

    def test_separator_suffix(self):
        assert is_padding_leaf_name("کولیس — عمومی") is True
        assert is_padding_leaf_name("برقو - عمومی") is True
        assert is_padding_leaf_name("حدیده – عمومی") is True

    def test_arabic_yeh_normalized(self):
        # Arabic Yeh in عمومی should still match after norm
        assert is_padding_leaf_name("عمومي") is True

    def test_real_leaf_with_omumi_word_not_padding(self):
        assert is_padding_leaf_name("ابزار دستی عمومی") is False
        assert is_padding_leaf_name("انواع کولیس") is False
        assert is_padding_leaf_name("") is False


class TestPlanOmumiRemovals:
    def test_clear_l3_sole_child_is_applied(self):
        cats = [
            {
                "id": 1,
                "name": "مته",
                "parent_id": None,
                "depth": 1,
                "product_count": 0,
                "breadcrumb": ["مته"],
            },
            {
                "id": 10,
                "name": "برقو",
                "parent_id": 1,
                "depth": 2,
                "product_count": 0,
                "breadcrumb": ["مته", "برقو"],
            },
            {
                "id": 100,
                "name": "برقو — عمومی",
                "parent_id": 10,
                "depth": 3,
                "product_count": 5,
                "breadcrumb": ["مته", "برقو", "برقو — عمومی"],
            },
        ]
        plan = plan_omumi_removals(cats)
        assert plan["move_count"] == 1
        assert plan["moves"][0]["id"] == 100
        assert plan["moves"][0]["parent_id"] == 10
        assert plan["skip_count"] == 0
        assert plan["products_to_move"] == 5

    def test_skips_when_parent_has_other_children(self):
        cats = [
            {
                "id": 1,
                "name": "مته",
                "parent_id": None,
                "depth": 1,
                "product_count": 0,
                "breadcrumb": ["مته"],
            },
            {
                "id": 10,
                "name": "برقو",
                "parent_id": 1,
                "depth": 2,
                "product_count": 0,
                "breadcrumb": ["مته", "برقو"],
            },
            {
                "id": 100,
                "name": "برقو — عمومی",
                "parent_id": 10,
                "depth": 3,
                "product_count": 5,
                "breadcrumb": ["مته", "برقو", "برقو — عمومی"],
            },
            {
                "id": 101,
                "name": "برقو الماس",
                "parent_id": 10,
                "depth": 3,
                "product_count": 2,
                "breadcrumb": ["مته", "برقو", "برقو الماس"],
            },
        ]
        plan = plan_omumi_removals(cats)
        assert plan["move_count"] == 0
        assert plan["skip_count"] == 1
        assert plan["skips"][0]["reason"] == "not_sole_child_parent_would_remain_non_leaf"

    def test_near_miss_hand_tools_left_intact(self):
        cats = [
            {
                "id": 1,
                "name": "لوازم",
                "parent_id": None,
                "depth": 1,
                "product_count": 0,
                "breadcrumb": ["لوازم"],
            },
            {
                "id": 10,
                "name": "ابزار دستی",
                "parent_id": 1,
                "depth": 2,
                "product_count": 0,
                "breadcrumb": ["لوازم", "ابزار دستی"],
            },
            {
                "id": 158,
                "name": "ابزار دستی عمومی",
                "parent_id": 10,
                "depth": 3,
                "product_count": 196,
                "breadcrumb": ["لوازم", "ابزار دستی", "ابزار دستی عمومی"],
            },
        ]
        plan = plan_omumi_removals(cats)
        assert plan["move_count"] == 0
        assert plan["skip_count"] == 0
        assert len(plan["near_misses"]) == 1
        assert plan["near_misses"][0]["id"] == 158
