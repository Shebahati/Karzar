"""Structural validation for taxonomy v0 metrology seed (UD-03 A / CF-SPEC-01)."""

from __future__ import annotations

import json
from pathlib import Path

SEED = Path("docs/architecture/specs/seeds/taxonomy-v0-metrology.json")

REQUIRED_NODE_FIELDS = {
    "concept_id",
    "dimension",
    "name_fa",
    "name_en",
    "slug",
    "parent",
    "status",
    "synonyms",
    "description",
}

REQUIRED_FAMILIES = {
    "fam.calipers",
    "fam.micrometers",
    "fam.height_gauges",
    "fam.indicators",
}

METROLOGY_BRIDGE_IDS = {56, 81, 87}


def _load() -> dict:
    assert SEED.is_file(), f"missing seed {SEED}"
    return json.loads(SEED.read_text(encoding="utf-8"))


def test_seed_meta_forbids_second_category_dag():
    data = _load()
    assert data["scope"] == "metrology"
    assert data["ud_03"] == "A"
    assert data["replaces_commerce_categories"] is False
    assert data["indexable_knowledge_hubs"] is False
    assert data["ud_04"] == "deferred"


def test_nodes_have_required_fields_and_unique_ids():
    data = _load()
    nodes = data["nodes"]
    assert len(nodes) >= 15
    ids: set[str] = set()
    by_id = {}
    for node in nodes:
        missing = REQUIRED_NODE_FIELDS - set(node)
        assert not missing, f"{node.get('concept_id')}: missing {missing}"
        assert node["concept_id"] not in ids
        ids.add(node["concept_id"])
        by_id[node["concept_id"]] = node
        assert node["dimension"] in data["dimensions"]
        assert node["status"] in {"active", "draft", "deprecated"}

    for node in nodes:
        parent = node["parent"]
        if parent is not None:
            assert parent in by_id, f"{node['concept_id']} parent {parent} missing"


def test_measurement_domain_and_seed_r2_families():
    data = _load()
    by_id = {n["concept_id"]: n for n in data["nodes"]}
    assert "dom.measurement" in by_id
    assert by_id["dom.measurement"]["parent"] == "dom.root"
    assert REQUIRED_FAMILIES <= set(by_id)
    assert by_id["fam.calipers"]["parent"] == "fam.dim"
    assert by_id["type.caliper.digital"]["parent"] == "fam.calipers"
    assert "caliper" in by_id["fam.calipers"]["related_templates"]


def test_commerce_bridge_only_metrology_l1():
    data = _load()
    mappings = data["commerce_category_bridge"]["mappings"]
    ids = {m["commerce_l1_id"] for m in mappings}
    assert ids == METROLOGY_BRIDGE_IDS
    assert all(m["knowledge_domain"] == "dom.measurement" for m in mappings)


def test_no_cutting_domain_in_metrology_v0_slice():
    """Metrology v0 must not pull cutting/toolholding domains (UD-03 A)."""
    data = _load()
    ids = {n["concept_id"] for n in data["nodes"]}
    assert "dom.cutting" not in ids
    assert "fam.inserts" not in ids
