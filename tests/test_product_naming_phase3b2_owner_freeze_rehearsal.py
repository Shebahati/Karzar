"""Phase 3B2 owner freeze & rehearsal — deterministic invariants (no live DB)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from app.domain.product_naming_phase3b2 import (
    EXPECTED_APPLIED_ROWS,
    EXPECTED_DECISION_COUNT,
    EXPECTED_PT_COUNTS,
    EXPECTED_WAVE_3B_ROWS,
    OWNER_APPROVED,
    POLICY_REL,
    build_phase3b2_pack,
    owner_decision_freeze_rows,
    owner_decision_sha256,
    reject_mutation_flags,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pack():
    return build_phase3b2_pack(ROOT)


def test_eleven_owner_decisions_exact_approved(pack):
    freeze = pack["freeze"]
    assert len(freeze) == EXPECTED_DECISION_COUNT
    assert all(r["owner_status"] == "APPROVED" for r in freeze)
    ids = {r["decision_id"] for r in freeze}
    assert ids == set(OWNER_APPROVED)
    by = {r["decision_id"]: r for r in freeze}
    assert by["D-GENCAL-01"]["approved_option"] == "OPTION_B"
    assert by["D-BORE-01"]["approved_option"] == "OPTION_A"
    assert by["D-DIVIDER-01"]["approved_option"] == "OPTION_A"
    assert by["D-TAPER-01"]["approved_option"] == "OPTION_A"
    assert by["D-STRAIGHT-01"]["approved_option"] == "OPTION_C"
    assert by["D-OPTICAL-01"]["approved_option"] == "CONDITIONAL_B_THEN_A_ON_EXACT_OEM_EVIDENCE"
    assert by["D-LEVEL-01"]["approved_option"] == "OPTION_A"
    assert by["D-DLEVEL-01"]["approved_option"] == "OPTION_A"
    assert by["D-PLATE-01"]["approved_option"] == "OPTION_A"
    assert by["D-VISE-01"]["approved_option"] == "CONDITIONAL_C_THEN_A_ON_EXACT_OEM_EVIDENCE"
    assert by["D-VBLOCK-01"]["approved_option"] == "OPTION_A_WITH_6890_702_HELD"


def test_owner_decision_sha_deterministic(pack):
    a = owner_decision_sha256(owner_decision_freeze_rows())
    b = owner_decision_sha256(owner_decision_freeze_rows())
    assert a == b == pack["freeze_sha"]


def test_scope_132_and_counts(pack):
    assert len(pack["scope"]) == EXPECTED_WAVE_3B_ROWS
    counts = Counter(r["product_type_code"] for r in pack["scope"])
    assert dict(counts) == EXPECTED_PT_COUNTS


def test_decision_coverage_132(pack):
    assert len(pack["routing"]) == 132
    assert len({r["product_id"] for r in pack["routing"]}) == 132
    covered = sum(int(r["affected_rows"]) for r in pack["freeze"])
    assert covered == 132


def test_phase2f_intersection_zero(pack):
    assert pack["phase2f_intersection"] == 0
    cands = {r["product_id"] for r in pack["candidates"]}
    assert len(cands) == EXPECTED_APPLIED_ROWS
    assert not ({r["product_id"] for r in pack["scope"]} & cands)


def test_bore_3127_to_inside_micrometer(pack):
    row = next(r for r in pack["routing"] if r["manufacturer_code"] == "3127-300")
    assert row["recommended_pt_code"] == "INSIDE_MICROMETER"
    assert row["recommended_pt_action"] == "REASSIGN_EXISTING_PT"


def test_optical_conditional_hold(pack):
    row = next(r for r in pack["routing"] if r["manufacturer_code"] == "6566-2")
    assert row["recommended_pt_action"] == "SOURCE_EVIDENCE_HOLD"
    ev = next(e for e in pack["evidence"] if e["manufacturer_code"] == "6566-2")
    assert ev["governance_eligible"] == "no"
    assert ev["product_name_used_as_authority"] == "no"


def test_vblock_6890_held(pack):
    row = next(r for r in pack["routing"] if r["manufacturer_code"] == "6890-702")
    assert row["recommended_pt_action"] == "SOURCE_EVIDENCE_HOLD"
    assert "6890" in row["hold_reason_if_any"]


def test_divider_no_straight_pt_from_legacy_name(pack):
    for r in pack["routing"]:
        if r["manufacturer_code"].startswith("7247"):
            assert r["recommended_pt_code"] == "OUTSIDE_SPRING_CALIPER"
            assert r["recommended_pt_action"] == "CREATE_NEW_PT_AND_ASSIGN"


def test_gen_caliper_long_jaw_split(pack):
    long_jaw = [
        r for r in pack["routing"] if r["recommended_pt_code"] == "LONG_JAW_CALIPER"
    ]
    assert long_jaw
    assert all(r["recommended_pt_action"] == "CREATE_NEW_PT_AND_ASSIGN" for r in long_jaw)


def test_no_product_name_in_mutation_plan(pack):
    assert pack["mutation_plan"]
    assert all(r["entity_type"] != "Product.name" for r in pack["mutation_plan"])
    assert all("Product.name" not in r["entity_type"] for r in pack["mutation_plan"])


def test_body_length_not_measurement_range(pack):
    props = {p["property_code"]: p for p in pack["props"]}
    assert props["body_length"]["dimension"] == "length"
    assert "measurement_range" in props["body_length"]["collision_with_existing"]
    level_delta = next(d for d in pack["policy_delta"] if d["product_type_code"] == "LEVEL")
    assert level_delta["new_primary_variant_property"] == "body_length"
    assert level_delta["new_primary_variant_property"] != "measurement_range"


def test_plate_dimensions_multi_dimensional(pack):
    p = next(x for x in pack["props"] if x["property_code"] == "plate_dimensions")
    assert p["dimension"] == "length_width_thickness"
    assert p["cardinality"] == "ordered_triple"


def test_conditional_cannot_advance_without_exact_evidence(pack):
    for code in ("6566-2", "6520-67", "6520-87", "6520-102"):
        row = next(r for r in pack["routing"] if r["manufacturer_code"] == code)
        assert row["recommended_pt_action"] == "SOURCE_EVIDENCE_HOLD"


def test_sku_and_name_not_authority(pack):
    for e in pack["evidence"]:
        assert e["sku_used_as_authority"] == "no"
        assert e["product_name_used_as_authority"] == "no"


def test_new_pts_have_inclusion_exclusion(pack):
    assert pack["new_pt_rows"]
    for r in pack["new_pt_rows"]:
        assert r["inclusion_rule"]
        assert r["exclusion_rule"]
        assert r["persian_canonical_title"]
        assert r["semantic_definition"]


def test_new_properties_have_unit_dimension_formatter(pack):
    for p in pack["props"]:
        assert p["dimension"]
        assert p["unit"]
        assert p["display_formatter"]


def test_post_governance_one_state_each(pack):
    assert len(pack["post_states"]) == 132
    assert len({r["product_id"] for r in pack["post_states"]}) == 132
    assert all(r["post_governance_state"] for r in pack["post_states"])
    assert sum(pack["state_counts"].values()) == 132
    banned = {"REVIEW", "review", ""}
    assert not any(r["post_governance_state"] in banned for r in pack["post_states"])


def test_wave3c_deduplicated(pack):
    w = pack["w3c"]
    assert w["deduplicated_future_variant_fact_total"] == (
        w["existing_wave3c_rows"] + w["new_rows_entering_variant_fact_from_3b"]
    )


def test_phase2f_regression_gate(pack):
    assert len(pack["candidates"]) == EXPECTED_APPLIED_ROWS


def test_collisions_zero(pack):
    # slash titles not in SAFE ADD titles for residual
    for d in pack["policy_delta"]:
        if d["action"] in {"ADD", "UPDATE"} and d["new_canonical_title_fa"]:
            assert "/" not in d["new_canonical_title_fa"]


def test_rehearsal_rollback(pack):
    assert pack["rehearsal"]["persistent_mutations"] == 0
    assert pack["rehearsal"]["product_name_actions"] == 0


def test_failure_injections_rollback(pack):
    for name, res in pack["injections"].items():
        assert res["rollback_ok"], name
        assert res["persistent_mutations"] == 0


def test_reject_live_apply_flag():
    with pytest.raises(SystemExit):
        reject_mutation_flags(["--live-apply"])


def test_authoritative_policy_unchanged(pack):
    assert pack["policy_sha256"] == sha256_file(ROOT / POLICY_REL)


def test_replay_deterministic(pack):
    pack2 = build_phase3b2_pack(ROOT)
    assert pack["freeze_sha"] == pack2["freeze_sha"]
    assert pack["action_counts"] == pack2["action_counts"]
    assert pack["state_counts"] == pack2["state_counts"]
    assert pack["w3c"]["deduplicated_future_variant_fact_total"] == pack2["w3c"][
        "deduplicated_future_variant_fact_total"
    ]


def test_laser_level_routed(pack):
    row = next(r for r in pack["routing"] if r["manufacturer_code"] == "4917-30")
    assert row["recommended_pt_code"] == "LASER_LEVEL"


def test_2199_semantic_hold(pack):
    row = next(r for r in pack["routing"] if r["manufacturer_code"] == "2199-1")
    assert row["recommended_pt_action"] == "SEMANTIC_HOLD"
