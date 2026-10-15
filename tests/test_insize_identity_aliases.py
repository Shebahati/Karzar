"""Tests for INSIZE explicit site→source identity aliases (PROVEN registry)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from scripts.insize_sales_activation_lib import (
    WorkbookRow,
    load_insize_identity_aliases,
    match_exact,
    match_insize_identity_alias,
    match_insize_workbook_terminal_a_alias,
    normalize_sku,
    valid_workbook_price,
)

ALIAS_CSV = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "architecture"
    / "specs"
    / "product-naming-v1"
    / "INSIZE_SITE_TO_SOURCE_CODE_ALIASES.csv"
)


def _wb(code: str, usd: Decimal | None = Decimal("10")) -> WorkbookRow:
    return WorkbookRow(
        code=code,
        description="x",
        total_inventory=Decimal("1"),
        status="موجود",
        usd_price=usd,
        source_row=2,
    )


def test_registry_loads_proven_aliases_including_1205():
    aliases = load_insize_identity_aliases(ALIAS_CSV, proven_only=True)
    assert normalize_sku("0213-500A") in aliases
    assert aliases[normalize_sku("0213-500A")].authoritative_source_code == "0213-A500"
    assert aliases[normalize_sku("6297-1A")].authoritative_source_code == "6297-1"
    assert aliases[normalize_sku("7527-1D")].authoritative_source_code == "7527-D1"
    assert aliases[normalize_sku("7527-2D")].authoritative_source_code == "7527-D2"
    assert aliases[normalize_sku("1205-1502")].authoritative_source_code == "1205-1502S"
    assert aliases[normalize_sku("1205-2002")].authoritative_source_code == "1205-2002S"
    assert aliases[normalize_sku("1205-3002")].authoritative_source_code == "1205-3002S"
    assert len(aliases) == 7


def test_identity_alias_0213():
    wb = {"0213-A500": _wb("0213-A500", Decimal("55.92"))}
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    r = match_insize_identity_alias(
        "0213-500A", wb, aliases=aliases, insize_db_skus=frozenset({"0213-500A"})
    )
    assert r.method == "INSIZE_IDENTITY_ALIAS"
    assert normalize_sku(r.workbook_code) == "0213-A500"


def test_identity_alias_6297_and_7527_family():
    wb = {
        "6297-1": _wb("6297-1", Decimal("15.48")),
        "7527-D1": _wb("7527-D1", Decimal("27.36")),
        "7527-D2": _wb("7527-D2", Decimal("31.2")),
        "7527-D1B": _wb("7527-D1B", Decimal("29.16")),
    }
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    assert (
        match_insize_identity_alias(
            "6297-1A", wb, aliases=aliases, insize_db_skus=frozenset({"6297-1A"})
        ).method
        == "INSIZE_IDENTITY_ALIAS"
    )
    assert (
        normalize_sku(
            match_insize_identity_alias(
                "7527-1D", wb, aliases=aliases, insize_db_skus=frozenset({"7527-1D"})
            ).workbook_code
        )
        == "7527-D1"
    )
    assert (
        normalize_sku(
            match_insize_identity_alias(
                "7527-2D", wb, aliases=aliases, insize_db_skus=frozenset({"7527-2D"})
            ).workbook_code
        )
        == "7527-D2"
    )
    # D1B remains a distinct workbook code; alias must not steal it
    assert match_exact("7527-D1B", wb).method == "exact"


def test_exact_match_overrides_identity_alias():
    wb = {"0213-500A": _wb("0213-500A", Decimal("1")), "0213-A500": _wb("0213-A500", Decimal("55.92"))}
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    r = match_insize_identity_alias(
        "0213-500A", wb, aliases=aliases, insize_db_skus=frozenset({"0213-500A"})
    )
    assert r.method == "exact"
    assert normalize_sku(r.workbook_code) == "0213-500A"


def test_wrong_brand_rejected():
    wb = {"0213-A500": _wb("0213-A500")}
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    r = match_insize_identity_alias(
        "0213-500A",
        wb,
        aliases=aliases,
        insize_db_skus=frozenset({"0213-500A"}),
        brand_is_insize=False,
    )
    assert r.method == "unmatched"


def test_source_missing_rejected():
    wb = {"OTHER": _wb("OTHER")}
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    r = match_insize_identity_alias(
        "0213-500A", wb, aliases=aliases, insize_db_skus=frozenset({"0213-500A"})
    )
    assert r.method == "unmatched"


def test_na_price_gate():
    cls, _, toman = valid_workbook_price(None, Decimal("2500000"))
    assert cls == "INVALID_WORKBOOK_PRICE"
    assert toman is None


def test_competing_db_source_sku_rejected():
    wb = {"6297-1": _wb("6297-1")}
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    r = match_insize_identity_alias(
        "6297-1A",
        wb,
        aliases=aliases,
        insize_db_skus=frozenset({"6297-1A", "6297-1"}),
    )
    assert r.method == "IDENTITY_ALIAS_AMBIGUOUS"


def test_trailing_a_precedence_not_broken_by_registry():
    # Prior 134 cohort path still works independently
    wb = {"1120-150A": _wb("1120-150A", Decimal("89.64"))}
    r = match_insize_workbook_terminal_a_alias(
        "1120-150", wb, insize_db_skus=frozenset({"1120-150"})
    )
    assert r.method == "WORKBOOK_TRAILING_A_ALIAS"


def test_exact_cohort_sku_unaffected():
    wb = {"1106-1002": _wb("1106-1002", Decimal("526.8"))}
    assert match_exact("1106-1002", wb).method == "exact"
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    # No identity alias should rewrite an exact-matched SKU
    r = match_insize_identity_alias(
        "1106-1002", wb, aliases=aliases, insize_db_skus=frozenset({"1106-1002"})
    )
    assert r.method == "exact"


def test_1205_02_maps_to_02s_not_e_or_bare_s():
    wb = {
        "1205-1502S": _wb("1205-1502S", Decimal("25.92")),
        "1205-1502E": _wb("1205-1502E", Decimal("30.24")),
        "1205-150S": _wb("1205-150S", Decimal("25.92")),
        "1205-2002S": _wb("1205-2002S", Decimal("39.24")),
        "1205-2002E": _wb("1205-2002E", Decimal("45.48")),
        "1205-200S": _wb("1205-200S", Decimal("39.36")),
        "1205-3002S": _wb("1205-3002S", Decimal("65.76")),
        "1205-3002E": _wb("1205-3002E", Decimal("78.48")),
        "1205-300S": _wb("1205-300S", Decimal("66")),
    }
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    db = frozenset(
        {
            "1205-1502",
            "1205-150S",
            "1205-2002",
            "1205-200S",
            "1205-3002",
            "1205-300S",
        }
    )
    for site, source in (
        ("1205-1502", "1205-1502S"),
        ("1205-2002", "1205-2002S"),
        ("1205-3002", "1205-3002S"),
    ):
        r = match_insize_identity_alias(site, wb, aliases=aliases, insize_db_skus=db)
        assert r.method == "INSIZE_IDENTITY_ALIAS"
        assert normalize_sku(r.workbook_code) == source
    # Sibling *S remains exact; must not be rewritten by *02 alias
    assert match_exact("1205-150S", wb).method == "exact"
    assert match_exact("1205-200S", wb).method == "exact"
    assert match_exact("1205-300S", wb).method == "exact"
    # Competing DB product owning source SKU blocks alias
    blocked = match_insize_identity_alias(
        "1205-1502",
        wb,
        aliases=aliases,
        insize_db_skus=db | {"1205-1502S"},
    )
    assert blocked.method == "IDENTITY_ALIAS_AMBIGUOUS"


def test_1205_e_s_price_distinction_not_used_as_matcher():
    # Registry chooses 02S explicitly; E remains a distinct unused source code.
    aliases = load_insize_identity_aliases(ALIAS_CSV)
    assert aliases[normalize_sku("1205-1502")].authoritative_source_code == "1205-1502S"
    assert "1205-1502E" not in {
        a.authoritative_source_code for a in aliases.values()
    }
