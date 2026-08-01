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
