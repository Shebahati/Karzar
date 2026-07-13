"""Unit tests for in-memory category tree assembly."""

import pytest
from app.db.models.product import Category
from app.utils.category_tree import build_category_tree


def _category(category_id: int, name: str, parent_id: int | None = None) -> Category:
    slug = name.lower().replace(" ", "-")
    return Category(id=category_id, name=name, parent_id=parent_id, slug=slug)


class TestBuildCategoryTree:
    def test_empty_list_returns_empty_tree(self):
        assert build_category_tree([]) == []

    def test_single_root_without_children(self):
        tree = build_category_tree([_category(1, "Root")])
        assert len(tree) == 1
        assert tree[0].id == 1
        assert tree[0].subcategories == []

    def test_builds_four_levels_deep(self):
        categories = [
            _category(1, "Level 1"),
            _category(2, "Level 2", 1),
            _category(3, "Level 3", 2),
            _category(4, "Level 4", 3),
        ]

        tree = build_category_tree(categories)

        assert len(tree) == 1
        assert tree[0].name == "Level 1"
        assert tree[0].subcategories[0].name == "Level 2"
        assert tree[0].subcategories[0].subcategories[0].name == "Level 3"
        assert tree[0].subcategories[0].subcategories[0].subcategories[0].name == "Level 4"
        assert tree[0].subcategories[0].subcategories[0].subcategories[0].subcategories == []

    def test_multiple_roots_sorted_by_name(self):
        categories = [
            _category(2, "Beta"),
            _category(1, "Alpha"),
            _category(3, "Gamma"),
        ]

        tree = build_category_tree(categories)

        assert [node.name for node in tree] == ["Alpha", "Beta", "Gamma"]

    def test_children_sorted_by_name(self):
        categories = [
            _category(1, "Root"),
            _category(3, "Charlie", 1),
            _category(2, "Bravo", 1),
            _category(4, "Alpha", 1),
        ]

        tree = build_category_tree(categories)
        assert [child.name for child in tree[0].subcategories] == ["Alpha", "Bravo", "Charlie"]

    def test_orphan_category_promoted_to_root(self):
        categories = [
            _category(1, "Root"),
            _category(2, "Orphan", parent_id=999),
        ]

        tree = build_category_tree(categories)

        assert len(tree) == 2
        assert {node.id for node in tree} == {1, 2}

    def test_detects_cycles(self):
        categories = [
            _category(1, "A", 2),
            _category(2, "B", 1),
        ]

        with pytest.raises(ValueError, match="cycle"):
            build_category_tree(categories)
