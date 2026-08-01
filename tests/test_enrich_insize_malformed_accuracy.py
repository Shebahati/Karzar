"""Wave A: corrupt slash-decimal accuracy must yield to well-formed shopmill values."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "enrich_insize_from_shopmill.py"


@pytest.fixture(scope="module")
def enrich():
    spec = importlib.util.spec_from_file_location("enrich_insize_from_shopmill", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before exec for dataclasses on Python 3.12
    import sys

    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_corrupt_slash_decimal_detection(enrich):
    assert enrich.is_corrupt_slash_decimal("0/01")
    assert enrich.is_corrupt_slash_decimal("0/02mm")
    assert not enrich.is_corrupt_slash_decimal("±0.03mm")
    assert not enrich.looks_like_accuracy("0/01")
    assert enrich.looks_like_accuracy("±0.03mm")


def test_merge_replaces_malformed_accuracy(enrich):
    merged, notes, filled = enrich.merge_specifications(
        {"technical_specs": {"دقت": "0/01", "بازه اندازه‌گیری": "0-150mm"}},
        {"range": "0-150mm", "accuracy": "±0.03mm", "resolution": "0.01mm"},
        {},
        {},
    )
    assert merged["technical_specs"]["accuracy"] == "±0.03mm"
    assert filled.get("accuracy") == "±0.03mm"
    assert any(n.startswith("replace_malformed_accuracy:") for n in notes)


def test_merge_keeps_non_malformed_conflict(enrich):
    merged, notes, filled = enrich.merge_specifications(
        {"technical_specs": {"دقت": "±0.04mm"}},
        {"accuracy": "±0.03mm"},
        {},
        {},
    )
    assert merged["technical_specs"]["accuracy"] == "±0.04mm"
    assert any(n.startswith("keep_existing_accuracy:") for n in notes)
    assert "accuracy" not in filled


def test_text_has_corrupt_slash_decimal(enrich):
    assert enrich.text_has_corrupt_slash_decimal(
        "کولیس برند اینسایز. بازه 0-150mm؛ دقت 0/01. کد 1520-150."
    )
    assert enrich.text_has_corrupt_slash_decimal("دقت ۰/۰۱ میلی‌متر")
    assert not enrich.text_has_corrupt_slash_decimal(
        "کولیس برند اینسایز. بازه 0-150mm؛ دقت ±0.03mm. کد 1520-150."
    )


def test_short_description_skips_corrupt_accuracy(enrich):
    body = enrich.persian_short_description(
        name="کولیس 1520-150",
        brand_name="INSIZE | اینسایز",
        category_name="کولیس",
        sku="1520-150",
        tech={"range": "0-150mm", "resolution": "0.01mm", "accuracy": "0/01"},
    )
    assert body is not None
    assert "0/01" not in body
    assert "دقت" not in body  # corrupt accuracy omitted; do not invent
    assert "بازه 0-150mm" in body


def test_build_payload_rewrites_corrupt_short_and_meta(enrich):
    product = {
        "id": 1,
        "sku": "1520-150",
        "name": "کولیس دیجیتال اینسایز 1520-150",
        "brand": {"name": "INSIZE | اینسایز"},
        "category": {"name": "کولیس"},
        "short_description": (
            "کولیس برند اینسایز. بازه 0-150mm؛ تفکیک‌پذیری 0.01mm؛ دقت 0/01. "
            "کد 1520-150. مشخصات رسمی برند."
        ),
        "meta_description": (
            "کولیس برند اینسایز. بازه 0-150mm؛ تفکیک‌پذیری 0.01mm؛ دقت 0/01. "
            "کد 1520-150. مشخصات رسمی برند."
        ),
        "description": "کولیس برند اینسایز (INSIZE) با کد 1520-150. مرجع مشخصات: مشخصات رسمی برند.",
        "specifications": {
            "technical_specs": {
                "range": "0-150mm",
                "resolution": "0.01mm",
                "accuracy": "±0.03mm",
            }
        },
    }
    shop_row = {
        "sku": "1520-150",
        "source_url": "https://shopmilltools.com/product/x/",
        "specifications": {
            "بازه اندازه گیری": "0-150mm",
            "دقت اندازه گیری": "±0.03mm",
            "درجه بندی": "0.01mm",
        },
    }
    payload, audit = enrich.build_payload(product, shop_row)
    assert "short_description" in payload
    assert "meta_description" in payload
    assert "0/01" not in payload["short_description"]
    assert "0/01" not in payload["meta_description"]
    assert "±0.03mm" in payload["short_description"]
    assert audit["new_short"] is True
    assert audit["new_meta_description"] is True
