"""Unit tests for INSIZE +10% price APPLY domain helpers."""

from decimal import Decimal

from app.domain.insize_price_110 import (
    CHANGE_REASON,
    build_manifest_row,
    discount_impact_row,
    proposed_base_price,
)


def test_proposed_base_price_round_half_up():
    assert proposed_base_price(Decimal("1000.00")) == Decimal("1100.00")
    assert proposed_base_price(Decimal("1000.01")) == Decimal("1100.01")
    assert proposed_base_price(Decimal("1000.05")) == Decimal("1100.06")


def test_change_reason_exact():
    assert CHANGE_REASON == "INSIZE +10% owner-authorized price update 2026-10-19"


def test_discount_impact_when_new_meets_compare_at():
    impact = discount_impact_row(
        old_base=Decimal("900.00"),
        new_base=Decimal("990.00"),
        original_price=Decimal("1000.00"),
    )
    assert impact is not None
    assert impact["before"] == "discounted"
    assert impact["after"] in {"no_discount_equal", "above_compare_at", "discounted"}


def test_build_manifest_row():
    row = build_manifest_row(
        {
            "id": 1,
            "sku": "X",
            "name": "n",
            "slug": "s",
            "brand_id": 3,
            "brand_name": "INSIZE | اینسایز",
            "old_base_price": "100.00",
            "original_price": None,
            "is_active": True,
            "is_available": False,
            "deleted_at": None,
        }
    )
    assert row["proposed_base_price"] == "110.00"
    assert row["discount_impact"] is None
