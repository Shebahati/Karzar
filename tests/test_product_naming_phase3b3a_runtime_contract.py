"""Phase 3B3A runtime contract — deterministic invariants (no live DB writes)."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.domain.product_naming_phase3b3a import (
    EXPECTED_DECISION_COUNT,
    EXPECTED_REASSIGNMENTS,
    EXPECTED_WAVE_3B_ROWS,
    OWNER_DECISION_SHA256,
    build_phase3b3a_pack,
    load_owner_freeze_sha,
    load_phase3b2_mutation_plan,
    load_phase3b2_scope,
    property_realization_rows,
    reject_mutation_flags,
    reject_unsupported_property_shapes,
)

ROOT = Path(__file__).resolve().parents[1]
LIVE_DUMP = ROOT / "audit/product-naming-phase3b3a-runtime-contract/PHASE3B3A_LIVE_DUMP.json"


@pytest.fixture(scope="module")
def live_tsv() -> str:
    if not LIVE_DUMP.is_file():
        pytest.skip("PHASE3B3A live dump not present")
    import json

    return json.loads(LIVE_DUMP.read_text(encoding="utf-8"))["fact_gate_tsv"]


@pytest.fixture(scope="module")
def pack(live_tsv: str):
    return build_phase3b3a_pack(
        ROOT,
        live_fact_gate_tsv=live_tsv,
        live_meta={"transaction_read_only": "on", "mutation_sql_executed": 0},
    )


def test_owner_decision_sha_unchanged():
    assert load_owner_freeze_sha(ROOT) == OWNER_DECISION_SHA256


def test_wave_3b_rows_unchanged():
    assert len(load_phase3b2_scope(ROOT)) == EXPECTED_WAVE_3B_ROWS


def test_forty_four_reassignment_candidates():
    plan = load_phase3b2_mutation_plan(ROOT)
    assert (
        sum(1 for r in plan if r["entity_type"] == "Product.product_type_id")
        == EXPECTED_REASSIGNMENTS
    )


def test_published_fact_gate_exact(pack):
    gate = pack["fact_gate"]
    assert len(gate) == EXPECTED_REASSIGNMENTS
    blocked = [g for g in gate if g["classification"] == "EXPLICIT_RECLASSIFICATION_REQUIRED"]
    eligible = [g for g in gate if g["classification"] == "DIRECT_REASSIGNMENT_SERVICE_ELIGIBLE"]
    assert len(blocked) == EXPECTED_REASSIGNMENTS
    assert len(eligible) == 0
    assert all(int(g["published_fact_count"]) > 0 for g in blocked)


def test_no_direct_reassignment_when_published_facts(pack):
    assert all(g["service_assignable"] == "no" for g in pack["fact_gate"])


def test_asserted_disputed_compatibility_uses_target_definition(pack):
    assert len(pack["fact_compat"]) == EXPECTED_REASSIGNMENTS
    assert all(r["compatibility_class"] == "COMPATIBLE" for r in pack["fact_compat"])


def test_new_pt_assignment_requires_active_definition(pack):
    rows = [r for r in pack["definition_plan"] if r["kind"] == "NEW_PT"]
    assert len(rows) == 7
    assert all("active_Definition" in r["assignment_dependency"] for r in rows)


def test_active_definition_memberships_not_mutated(pack):
    existing = [r for r in pack["definition_plan"] if r["kind"] == "EXISTING_PT_NEW_VERSION"]
    assert len(existing) == 3
    assert all(r["activation_status"].startswith("create_draft") for r in existing)


def test_existing_pt_membership_delta_creates_new_definition_version(pack):
    for code in ("LEVEL", "DIGITAL_LEVEL", "SURFACE_PLATE"):
        row = next(r for r in pack["definition_plan"] if r["product_type_code"] == code)
        assert int(row["new_definition_version"]) == int(row["current_active_version"]) + 1


def test_draft_property_cannot_support_definition_activation(pack):
    assert pack["rehearsal"]["activation_with_draft_property"] == "REFUSED_DRAFT_PROPERTY"


def test_surface_plate_string_fallback_rejected():
    rows = property_realization_rows()
    rejected = [r for r in rows if r.get("rejection_reason") == "REJECTED_STRING_FALLBACK"]
    assert rejected


def test_unsupported_tuple3_rejected():
    assert (
        reject_unsupported_property_shapes(
            data_type="tuple3", unit_dimension="length_width_thickness"
        )
        == "REJECTED_UNSUPPORTED_TUPLE3"
    )


def test_body_length_valid_under_property_dictionary():
    assert (
        reject_unsupported_property_shapes(data_type="number", unit_dimension="length") is None
    )


def test_property_dictionary_git_seed_remains_authoring_sot(pack):
    assert pack["property_seed_delta"]["authoritative_seed_mutated"] is False
    assert "property-dictionary-v0-metrology.json" in pack["property_seed_delta"]["authoring_sot"]


def test_new_pt_definitions_contain_necessary_memberships(pack):
    long_jaw = [
        m
        for m in pack["membership_diff"]
        if m["product_type_code"] == "LONG_JAW_CALIPER" and m["action"] == "COPY"
    ]
    keys = {m["property_key"] for m in long_jaw}
    assert "measurement_range" in keys
    assert "accuracy" in keys


def test_measurement_range_membership_where_required(pack):
    for code in ("LONG_JAW_CALIPER", "GAP_TAPER_GAUGE", "TAPER_BORE_GAUGE", "TAPER_GAUGE_SET"):
        mem = [
            m
            for m in pack["membership_diff"]
            if m["product_type_code"] == code and m["property_key"] == "measurement_range"
        ]
        assert mem
        assert mem[0]["action"] in {"COPY", "ADD"}


def test_audit_contract_preserved(pack):
    audit = pack["audit_expectations"]
    assert audit["assign_product_type"]["ProductChangeLog"].startswith("yes")
    assert audit["property_dictionary_import"]["AdminAuditLog"].startswith("no")


def test_product_name_actions_zero(pack):
    assert pack["summary"]["product_name_actions"] == 0
    assert any(
        r["mutation_class"] == "Product.name" and r["count"] == "0"
        for r in pack["mutation_graph"]
    )


def test_live_writes_zero(pack):
    assert pack["summary"]["live_mutations"] == 0


def test_decision_groups_eleven():
    assert EXPECTED_DECISION_COUNT == 11


def test_rehearsal_deterministic(pack):
    assert pack["rehearsal"]["result"] == "PASS"
    assert pack["rehearsal"]["published_fact_refusal"] == "REFUSED_PUBLISHED_FACTS"


def test_reject_live_apply_flag():
    with pytest.raises(SystemExit):
        reject_mutation_flags(["--live-apply"])


def test_reclassification_gap_explicit(pack):
    gaps = pack["reclassification_gaps"]
    assert gaps[0]["gap_id"] == "PHASE_3B3_RECLASSIFICATION_BLOCKER"
    assert gaps[0]["existing_workflow_path"] == "NONE"
    assert gaps[0]["reclassification_subset_count"] == str(EXPECTED_REASSIGNMENTS)
