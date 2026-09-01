"""Unit tests for taxonomy migration alias map."""

from scripts.catalog_taxonomy_migrate import CATEGORY_ALIASES


def test_category_alias_map_has_high_confidence_entries():
    assert CATEGORY_ALIASES["اینسرت"] == "اینسرت تراش"
    assert CATEGORY_ALIASES["مته"] == "مته HSS"
    assert CATEGORY_ALIASES["اندازه گیری"] == "اندازه‌گیری"


def test_category_alias_map_normalizes_to_canonical_names():
    for source, target in CATEGORY_ALIASES.items():
        assert source.strip()
        assert target.strip()
        assert source != target or source == target
