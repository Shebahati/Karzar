"""Structural + offline coverage for INSIZE taxonomy classify map (readiness §5)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

MAP = Path("docs/architecture/specs/seeds/classification-map-insize-v0-metrology.json")
TAXONOMY = Path("docs/architecture/specs/seeds/taxonomy-v0-metrology.json")
PROPERTY_DICT = Path("docs/architecture/specs/seeds/property-dictionary-v0-metrology.json")
SAMPLE_CSV = Path("data/imports/insize_products.csv")

REQUIRED_RULE_FIELDS = {"rule_id", "priority", "when", "assign", "auto_apply", "confidence"}
REQUIRED_ASSIGN_FIELDS = {
    "domain",
    "family",
    "type",
    "type_role",
    "applications",
    "template",
    "classification_status",
}
ALLOWED_STATUS = {
    "classified",
    "partial",
    "unclassified_pending_taxonomy",
}


def _load_map() -> dict:
    assert MAP.is_file(), f"missing map {MAP}"
    return json.loads(MAP.read_text(encoding="utf-8"))


def _taxonomy_ids() -> set[str]:
    data = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    return {n["concept_id"] for n in data["nodes"]}


def _template_keys() -> set[str]:
    data = json.loads(PROPERTY_DICT.read_text(encoding="utf-8"))
    return {t["key"] for t in data["templates"]}


def _rule_matches(rule: dict, *, category_id: int | None, haystack: str) -> bool:
    when = rule["when"]
    if when.get("always"):
        return True
    cats = when.get("commerce_category_ids")
    if cats is not None:
        if category_id is None or category_id not in cats:
            return False
    names = when.get("name_any")
    if names:
        lower = haystack.lower()
        if not any(token.lower() in lower for token in names):
            return False
    return cats is not None or bool(names)


def classify_row(map_data: dict, *, category_id: int | None, name: str, description: str = "") -> dict:
    haystack = f"{name} {description}"
    rules = sorted(map_data["rules"], key=lambda r: r["priority"])
    for rule in rules:
        if _rule_matches(rule, category_id=category_id, haystack=haystack):
            return {"rule_id": rule["rule_id"], **rule["assign"]}
    raise AssertionError("fallback rule missing")


def test_map_meta_gates():
    data = _load_map()
    assert data["mapping_kind"] == "taxonomy_classify"
    assert data["artifact_type"] == "MAPPING-TABLE"
    assert data["scope"] == "metrology"
    assert data["ud_03"] == "A"
    assert data["replaces_commerce_categories"] is False
    assert data["writes_facts"] is False
    assert data["dual_write"] == "forbidden"
    assert data["projects_classified_as_edges"] is False
    assert data["brand"]["brand_id"] == 3
    assert data["taxonomy_seed"] == str(TAXONOMY)
    assert Path(data["taxonomy_seed"]).is_file()


def test_rules_reference_closed_taxonomy_and_templates():
    data = _load_map()
    tax_ids = _taxonomy_ids()
    templates = _template_keys()
    priorities: set[int] = set()
    rule_ids: set[str] = set()

    for rule in data["rules"]:
        missing = REQUIRED_RULE_FIELDS - set(rule)
        assert not missing, f"{rule.get('rule_id')}: missing {missing}"
        assert rule["rule_id"] not in rule_ids
        rule_ids.add(rule["rule_id"])
        assert rule["priority"] not in priorities
        priorities.add(rule["priority"])

        assign = rule["assign"]
        missing_a = REQUIRED_ASSIGN_FIELDS - set(assign)
        assert not missing_a, f"{rule['rule_id']}: assign missing {missing_a}"
        assert assign["classification_status"] in ALLOWED_STATUS

        for key in ("domain", "family", "type"):
            value = assign[key]
            if value is not None:
                assert value in tax_ids, f"{rule['rule_id']}: unknown {key}={value}"

        for app in assign["applications"]:
            assert app in tax_ids, f"{rule['rule_id']}: unknown application {app}"

        template = assign["template"]
        if template is not None:
            assert template in templates, f"{rule['rule_id']}: unknown template {template}"

        if assign["type"] is not None:
            assert assign["type_role"] == "primary"
            assert assign["classification_status"] == "classified"
            assert assign["domain"] == "dom.measurement"
            assert assign["family"] is not None

    assert any(r["when"].get("always") for r in data["rules"]), "fallback always rule required"


def test_classifier_examples():
    data = _load_map()
    digital = classify_row(
        data,
        category_id=57,
        name="کولیس دیجیتال 15سانت",
    )
    assert digital["rule_id"] == "insize.caliper.digital"
    assert digital["type"] == "type.caliper.digital"
    assert digital["classification_status"] == "classified"

    mic_out = classify_row(
        data,
        category_id=58,
        name="میکرومتر خارج 0-25",
    )
    assert mic_out["type"] == "type.micrometer.outside"

    mic_in = classify_row(
        data,
        category_id=58,
        name="میکرومتر داخل 5-30",
    )
    assert mic_in["family"] == "fam.micrometers"
    assert mic_in["type"] is None
    assert mic_in["classification_status"] == "partial"

    tape = classify_row(data, category_id=77, name="متر نواری")
    assert tape["classification_status"] == "unclassified_pending_taxonomy"
    assert tape["family"] is None
    rule = next(r for r in data["rules"] if r["rule_id"] == tape["rule_id"])
    assert rule["auto_apply"] is False


def test_offline_sample_csv_coverage():
    """Offline dry coverage against INSIZE price-list sample — no API writes."""
    assert SAMPLE_CSV.is_file(), f"missing sample {SAMPLE_CSV}"
    data = _load_map()
    rows = list(csv.DictReader(SAMPLE_CSV.open(encoding="utf-8-sig")))
    assert len(rows) >= 200

    family_hits = 0
    type_hits = 0
    pending = 0
    for row in rows:
        assert row.get("brand_id") in {"3", 3} or "INSIZE" in (row.get("brand") or "")
        cid_raw = (row.get("category_id") or "").strip()
        category_id = int(cid_raw) if cid_raw.isdigit() else None
        result = classify_row(
            data,
            category_id=category_id,
            name=row.get("name") or "",
            description=row.get("description") or "",
        )
        if result["family"]:
            family_hits += 1
        if result["type"]:
            type_hits += 1
        if result["classification_status"] == "unclassified_pending_taxonomy":
            pending += 1

    # Metrology core L2s dominate the sample; family coverage must be material.
    assert family_hits >= 150, f"family_hits={family_hits}"
    assert type_hits >= 80, f"type_hits={type_hits}"
    assert pending >= 1, "expected some pending families outside taxonomy v0"
