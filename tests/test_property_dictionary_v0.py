"""Structural validation for Property Dictionary v0 metrology seed (UD-03 A)."""

from __future__ import annotations

import json
from pathlib import Path

SEED = Path("docs/architecture/specs/seeds/property-dictionary-v0-metrology.json")

REQUIRED_DEF_FIELDS = {
    "definition_id",
    "key",
    "data_type",
    "label_en",
    "label_fa",
    "validation",
    "comparable",
    "filterable",
    "customer_facing",
    "version",
    "status",
}

CALIPER_REQUIRED_KEYS = {
    "measurement_range",
    "resolution",
    "accuracy",
    "display_type",
}


def _load() -> dict:
    assert SEED.is_file(), f"missing seed {SEED}"
    return json.loads(SEED.read_text(encoding="utf-8"))


def test_seed_meta_and_dual_write_forbidden():
    data = _load()
    assert data["scope"] == "metrology"
    assert data["ud_03"] == "A"
    assert data["dual_write"] == "forbidden"
    assert data["status"] in {"draft", "active"}


def test_definitions_have_spec_required_fields():
    data = _load()
    defs = data["definitions"]
    assert len(defs) >= 8
    keys = set()
    for item in defs:
        missing = REQUIRED_DEF_FIELDS - set(item)
        assert not missing, f"{item.get('key')}: missing {missing}"
        assert item["key"].isascii() and " " not in item["key"]
        assert item["key"] not in keys
        keys.add(item["key"])
        assert isinstance(item.get("aliases"), list) and item["aliases"]
        if item["data_type"] == "enum":
            assert item.get("enum_values"), f"{item['key']} enum needs enum_values"


def test_caliper_template_composes_required_metrology_props():
    data = _load()
    templates = {t["key"]: t for t in data["templates"]}
    assert "caliper" in templates
    caliper = templates["caliper"]
    assert caliper["strangler_legacy_key"] == "measurement"
    def_by_id = {d["definition_id"]: d for d in data["definitions"]}
    prop_keys = set()
    for prop in caliper["properties"]:
        assert prop["definition_id"] in def_by_id
        prop_keys.add(def_by_id[prop["definition_id"]]["key"])
    assert CALIPER_REQUIRED_KEYS <= prop_keys
    required_keys = {
        def_by_id[p["definition_id"]]["key"]
        for p in caliper["properties"]
        if p.get("required")
    }
    assert CALIPER_REQUIRED_KEYS <= required_keys


def test_legacy_measurement_keys_map_to_definitions():
    data = _load()
    def_ids = {d["definition_id"] for d in data["definitions"]}
    legacy = data["legacy_key_map"]
    for section in ("technical_specs", "features"):
        for _src, definition_id in legacy[section].items():
            assert definition_id in def_ids
