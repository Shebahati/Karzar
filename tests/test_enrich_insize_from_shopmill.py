"""Unit tests for INSIZE shopmill enrichment helpers (no network)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enrich_insize_from_shopmill.py"


def _load():
    spec = importlib.util.spec_from_file_location("enrich_insize_from_shopmill", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def enrich():
    return _load()


def test_map_shopmill_attributes_canonical_and_extras(enrich):
    tech, extras, hints = enrich.map_shopmill_attributes(
        {
            "دامنه اندازه گیری": "0-200mm",
            "دقت اندازه گیری": "±0.03mm",
            "تفکیک پذیری": "0.01mm",
            "متریال": "استنلس استیل",
            "استاندارد ساخت": "DIN862",
            "استاندار باتری": "CR2032",
            "کشور سازنده": "چین",
            "گواهی ضد آب": "خیر",
            "عملکرد دکمه ها": "ABS، mm/inch، ON/OFF",
            "گارانتی": "12 ماه",  # skipped
        }
    )
    assert tech["range"] == "0-200mm"
    assert tech["accuracy"] == "±0.03mm"
    assert tech["resolution"] == "0.01mm"
    assert tech["material"] == "استنلس استیل"
    assert tech["standard"] == "DIN862"
    assert tech["battery_type"] == "CR2032"
    assert extras["کشور سازنده"] == "چین"
    assert "گارانتی" not in extras
    assert hints["waterproof"] is False
    assert hints["has_buttons"] is True


def test_country_never_becomes_material(enrich):
    tech, extras, _ = enrich.map_shopmill_attributes(
        {"متریال": "چین", "کشور سازنده": "چین"}
    )
    assert "material" not in tech
    assert extras["کشور سازنده"] == "چین"


def test_assert_payload_rejects_price(enrich):
    with pytest.raises(RuntimeError):
        enrich.assert_payload_safe({"short_description": "x", "base_price": "1"})


def test_resolve_exact_and_ambiguous(enrich):
    by_sku = {
        "1108-200": {"sku": "1108-200", "specifications": {"دامنه اندازه گیری": "0-200mm"}},
        "1111-100A": {"sku": "1111-100A", "specifications": {"دامنه اندازه گیری": "0-100mm"}},
        "1111-100B": {"sku": "1111-100B", "specifications": {"دامنه اندازه گیری": "0-100mm"}},
    }
    by_base = {
        "1108-200": ["1108-200"],
        "1111-100": ["1111-100A", "1111-100B"],
    }
    row, via, _ = enrich.resolve_shopmill_match("1108-200", by_sku, by_base)
    assert row and via == "exact"
    row2, via2, notes = enrich.resolve_shopmill_match("1111-100", by_sku, by_base)
    assert row2 is None and via2 == "ambiguous"
    assert any("ambiguous" in n for n in notes)


def test_merge_fill_empty_keeps_conflict(enrich):
    existing = {
        "technical_specs": {"range": "0-150mm", "accuracy": "±0.02mm"},
        "features": {},
        "dimensions": {},
        "optional_accessories": [],
        "source_attributes": {},
    }
    merged, notes, filled = enrich.merge_specifications(
        existing,
        {"range": "0-200mm", "resolution": "0.01mm"},
        {"کشور سازنده": "چین"},
        {},
    )
    tech = merged["technical_specs"]
    assert tech["range"] == "0-150mm"  # keep existing on conflict
    assert tech["resolution"] == "0.01mm"
    assert "resolution" in filled
    assert any(n.startswith("keep_existing_range") for n in notes)
    assert merged["source_attributes"]["کشور سازنده"] == "چین"
