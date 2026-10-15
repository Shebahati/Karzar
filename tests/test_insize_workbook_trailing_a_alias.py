"""Tests for INSIZE workbook trailing-A alias matcher (XA → X, exact-first)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from scripts.insize_sales_activation_lib import (
    WorkbookRow,
    match_exact,
    match_insize_workbook_terminal_a_alias,
    normalize_sku,
    strip_exactly_one_terminal_workbook_A,
    valid_workbook_price,
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


def test_strip_exactly_one_terminal_a():
    assert strip_exactly_one_terminal_workbook_A("ABC123A") == "ABC123"
    assert strip_exactly_one_terminal_workbook_A("ABCA123") is None
    assert strip_exactly_one_terminal_workbook_A("ABC123AA") == "ABC123A"
    assert strip_exactly_one_terminal_workbook_A("ABC123") is None
    assert strip_exactly_one_terminal_workbook_A("A") is None


def test_exact_match_unchanged():
    wb = {"1114-150A": _wb("1114-150A")}
    assert match_exact("1114-150A", wb).method == "exact"
    assert match_exact("1114-150", wb).method == "unmatched"


def test_workbook_xa_aliases_to_db_x():
    wb = {"1120-150A": _wb("1120-150A", Decimal("89.64"))}
    result = match_insize_workbook_terminal_a_alias(
        "1120-150",
        wb,
        insize_db_skus=frozenset({"1120-150"}),
    )
    assert result.method == "WORKBOOK_TRAILING_A_ALIAS"
    assert normalize_sku(result.workbook_code) == "1120-150A"
    assert result.candidates == ["1120-150"]


def test_exact_db_xa_wins_over_alias_to_x():
    wb = {"XA": _wb("XA")}
    # DB has both XA and X conceptually; workbook XA must not alias to X
    result = match_insize_workbook_terminal_a_alias(
        "X",
        wb,
        insize_db_skus=frozenset({"X", "XA"}),
    )
    assert result.method == "WORKBOOK_TRAILING_A_AMBIGUOUS"


def test_workbook_both_x_and_xa_exact_wins_for_x():
    wb = {"X": _wb("X", Decimal("1")), "XA": _wb("XA", Decimal("2"))}
    assert match_exact("X", wb).method == "exact"
    # Alias path must not override once exact is present
    result = match_insize_workbook_terminal_a_alias(
        "X",
        wb,
        insize_db_skus=frozenset({"X"}),
    )
    assert result.method == "exact"


def test_multiple_source_rows_same_code_use_by_code_unique():
    # by_code keeps first; conflicting USD gated elsewhere
    wb = {"1108-150A": _wb("1108-150A", Decimal("28.5"))}
    result = match_insize_workbook_terminal_a_alias(
        "1108-150",
        wb,
        insize_db_skus=frozenset({"1108-150"}),
    )
    assert result.method == "WORKBOOK_TRAILING_A_ALIAS"


def test_source_xa_with_na_excluded_by_price_gate():
    cls, _, _ = valid_workbook_price(None, Decimal("2500000"))
    assert cls == "INVALID_WORKBOOK_PRICE"
    wb = {"YA": _wb("YA", usd=None)}
    result = match_insize_workbook_terminal_a_alias(
        "Y",
        wb,
        insize_db_skus=frozenset({"Y"}),
    )
    # Matcher may still classify alias; price gate excludes write
    assert result.method == "WORKBOOK_TRAILING_A_ALIAS"
    cls2, _, toman = valid_workbook_price(wb["YA"].usd_price, Decimal("2500000"))
    assert cls2 == "INVALID_WORKBOOK_PRICE"
    assert toman is None


def test_non_insize_must_not_use_fallback():
    wb = {"ZA": _wb("ZA")}
    result = match_insize_workbook_terminal_a_alias(
        "Z",
        wb,
        insize_db_skus=frozenset({"Z"}),
        brand_is_insize=False,
    )
    assert result.method == "unmatched"


def test_internal_a_untouched():
    wb = {"ABCA123": _wb("ABCA123")}
    assert strip_exactly_one_terminal_workbook_A("ABCA123") is None
    result = match_insize_workbook_terminal_a_alias(
        "ABCA12",
        wb,
        insize_db_skus=frozenset({"ABCA12"}),
    )
    assert result.method == "unmatched"


def test_idempotent_target_equality():
    rate = Decimal("2500000")
    usd = Decimal("89.64")
    cls, _, toman = valid_workbook_price(usd, rate)
    assert cls == "VALID_WORKBOOK_PRICE"
    product = SimpleNamespace(base_price=toman)
    assert Decimal(str(product.base_price)) == toman


def test_exact_cohort_not_alias_when_exact_exists():
    # Previous 688 exact cohort: workbook code equals SKU — never strip A
    wb = {"1106-1002": _wb("1106-1002", Decimal("526.8"))}
    assert match_exact("1106-1002", wb).method == "exact"
    alias = match_insize_workbook_terminal_a_alias(
        "1106-1002",
        wb,
        insize_db_skus=frozenset({"1106-1002"}),
    )
    assert alias.method == "exact"
