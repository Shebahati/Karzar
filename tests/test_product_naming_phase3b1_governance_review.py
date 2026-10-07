"""Phase 3B1 governance review — deterministic invariants (no live DB)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from app.domain.product_naming_phase3b1 import (
    EXPECTED_APPLIED_ROWS,
    EXPECTED_NAMING_POLICY_ROWS,
    EXPECTED_NAMING_PT_COUNTS,
    EXPECTED_VARIANT_POLICY_ROWS,
    EXPECTED_VARIANT_PT_COUNTS,
    EXPECTED_WAVE_3B_ROWS,
    PHASE2D_CANDIDATES_REL,
    PHASE3A_MATRIX_REL,
    POLICY_REL,
    assert_no_phase2f_intersection,
    assert_readonly_sql,
    assert_scope_counts,
    build_phase3b1_pack,
    classify_bore_subfamily,
    classify_gen_caliper_subfamily,
    load_wave_3b_scope,
    name_quality_flags,
    reject_mutation_flags,
    sha256_file,
    slash_in_title,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pack():
    return build_phase3b1_pack(ROOT)


def test_wave_3b_scope_exact_132():
    rows = load_wave_3b_scope(ROOT / PHASE3A_MATRIX_REL)
    assert len(rows) == EXPECTED_WAVE_3B_ROWS


def test_naming_and_variant_counts(pack):
    rows = pack["rows"]
    naming = [
        r
        for r in rows
        if r["historical_hold_reason"] == "HOLD_PRODUCT_TYPE_NAMING_POLICY"
    ]
    variant = [
        r
        for r in rows
        if r["historical_hold_reason"] == "HOLD_VARIANT_POLICY_UNDEFINED"
    ]
    assert len(naming) == EXPECTED_NAMING_POLICY_ROWS
    assert len(variant) == EXPECTED_VARIANT_POLICY_ROWS
    assert assert_scope_counts(rows) == []


def test_exact_product_type_group_counts(pack):
    from collections import Counter

    naming = [
        r
        for r in pack["rows"]
        if r["historical_hold_reason"] == "HOLD_PRODUCT_TYPE_NAMING_POLICY"
    ]
    variant = [
        r
        for r in pack["rows"]
        if r["historical_hold_reason"] == "HOLD_VARIANT_POLICY_UNDEFINED"
    ]
    nc = Counter(r["current_product_type_code"] for r in naming)
    vc = Counter(r["current_product_type_code"] for r in variant)
    assert dict(nc) == EXPECTED_NAMING_PT_COUNTS
    assert dict(vc) == EXPECTED_VARIANT_PT_COUNTS


def test_phase2f_intersection_zero(pack):
    cands = list(
        csv.DictReader((ROOT / PHASE2D_CANDIDATES_REL).open(encoding="utf-8"))
    )
    assert len(cands) == EXPECTED_APPLIED_ROWS
    assert_no_phase2f_intersection(pack["rows"], cands)


def test_phase2f_names_unchanged_every_simulation(pack):
    for mode in ("BASELINE", "SAFE_ONLY", "RECOMMENDED_OWNER_OPTIONS"):
        sim = pack["sims"][mode]
        assert sim["phase2f_identical"] == EXPECTED_APPLIED_ROWS
        assert sim["phase2f_regression"] == 0


def test_no_mutation_capable_sql():
    with pytest.raises(RuntimeError):
        assert_readonly_sql("UPDATE products SET name='x'")
    assert_readonly_sql("SELECT id FROM products LIMIT 1")


def test_reject_mutation_flags():
    with pytest.raises(SystemExit):
        reject_mutation_flags(["--apply"])


def test_authoritative_policy_unchanged_during_pack_build(pack):
    # Pack records sha; file must still match after build
    assert pack["policy_sha256"] == sha256_file(ROOT / POLICY_REL)


def test_gen_caliper_cannot_auto_approve(pack):
    assert pack["groups"]["GEN_CALIPER"].one_title_safe == "no"
    assert all(
        r["safe_auto_approve_generic_kolis"] == "no" for r in pack["gen_caliper_split"]
    )
    assert "LONG_JAW_CALIPER" in pack["groups"]["GEN_CALIPER"].subfamilies
    assert pack["groups"]["GEN_CALIPER"].verdict == "HOMOGENEOUS_WITH_IDENTITY_QUALIFIERS"


def test_bore_gauge_cannot_use_one_title_if_micrometer(pack):
    mis = [r for r in pack["bore_analysis"] if r["misassigned_as_bore_gauge"] == "yes"]
    assert mis
    assert all(r["safe_single_persian_title_for_all_16"] == "no" for r in pack["bore_analysis"])
    assert classify_bore_subfamily(
        "DIGITAL TWO POINTS/THREE POINTS INTERNAL MICROMETERS",
        "میکرومتر دیجیتال داخل",
        "3127-300",
    ) == "THREE_POINT_INTERNAL_MICROMETER"


def test_level_cannot_use_body_length_as_measurement_range(pack):
    for r in pack["level_analysis"]:
        assert r["measurement_range_allowed"] == "no"
    vo = {r["product_type_code"]: r for r in pack["variant_options"]}
    assert vo["LEVEL"]["proposed_variant_property"] == "body_length"
    assert vo["LEVEL"]["proposed_variant_property"] != "measurement_range"
    assert vo["LEVEL"]["measurement_range_forbidden_reason"] == "body_length_not_range"
    assert vo["DIGITAL_LEVEL"]["proposed_variant_property"] == "body_length"


def test_surface_plate_not_scalar(pack):
    vo = next(r for r in pack["variant_options"] if r["product_type_code"] == "SURFACE_PLATE")
    assert vo["proposed_variant_property"] == "plate_dimensions"
    assert "multi" in vo["measurement_range_forbidden_reason"]
    assert any(
        p["property_code"] == "plate_dimensions"
        and p["proposal_status"] == "NEW_PROPERTY_REQUIRED"
        for p in pack["property_requirements"]
    )


def test_product_name_not_sole_evidence_optical(pack):
    assert pack["optical"]["direct_unlock_retained"] is False
    assert pack["optical"]["oem_evidence_status"] != "EXACT_PRODUCT_IDENTITY"


def test_sku_pattern_not_sole_evidence_vise(pack):
    assert pack["groups"]["PRECISION_VISE"].verdict == "OWNER_SEMANTIC_DECISION"
    assert "SKU" in pack["groups"]["PRECISION_VISE"].recommended_action or "pattern" in pack[
        "groups"
    ]["PRECISION_VISE"].recommended_action.lower() or "Confirm" in pack["groups"][
        "PRECISION_VISE"
    ].recommended_action


def test_slash_titles_not_safe_recommendation(pack):
    for o in pack["overlay"]:
        if slash_in_title(o.get("canonical_title_fa") or ""):
            assert o["proposal_status"] != "SAFE_RECOMMENDATION"
    assert pack["safe_overlay_count"] == 0


def test_owner_decision_groups_have_options(pack):
    assert len(pack["owner_decisions"]) >= 8
    for d in pack["owner_decisions"]:
        assert d["option_a"]
        assert d["option_b"]
        assert d["recommended_option"]


def test_variant_properties_have_unit_dimension(pack):
    for p in pack["property_requirements"]:
        if p["proposal_status"] in {"NEW_PROPERTY_REQUIRED", "EXISTING"}:
            assert p["dimension"]
            assert p["unit"]
            assert p["formatter"]


def test_every_3b_row_has_post_policy_blocker(pack):
    rec = pack["sims"]["RECOMMENDED_OWNER_OPTIONS"]
    assert len(rec["blockers"]) == EXPECTED_WAVE_3B_ROWS
    assert all(b["post_policy_blocker"] for b in rec["blockers"])
    assert rec["reconciles_to_132"] is True


def test_simulation_counts_reconcile(pack):
    for mode in ("BASELINE", "SAFE_ONLY", "RECOMMENDED_OWNER_OPTIONS"):
        sim = pack["sims"][mode]
        assert sum(sim["counts"].values()) == EXPECTED_WAVE_3B_ROWS


def test_wave3c_expansion_deduplicated(pack):
    w = pack["wave3c"]
    assert w["existing_wave3c_rows"] == 58
    assert w["deduplicated_future_variant_fact_total"] == (
        w["existing_wave3c_rows"] + w["new_rows_entering_variant_fact_from_3b"]
    )


def test_replay_deterministic(pack):
    pack2 = build_phase3b1_pack(ROOT)
    assert pack["verdict_counts"] == pack2["verdict_counts"]
    assert pack["wave3c"] == pack2["wave3c"]
    assert pack["sims"]["SAFE_ONLY"]["counts"] == pack2["sims"]["SAFE_ONLY"]["counts"]
    assert (
        pack["sims"]["RECOMMENDED_OWNER_OPTIONS"]["counts"]
        == pack2["sims"]["RECOMMENDED_OWNER_OPTIONS"]["counts"]
    )


def test_gen_caliper_subfamily_classifier():
    assert (
        classify_gen_caliper_subfamily("LONG JAW VERNIER CALIPERS (SEPARATE TYPE)", "")
        == "LONG_JAW_CALIPER"
    )
    assert (
        classify_gen_caliper_subfamily("DIGITAL CALIPERS", "کولیس دیجیتال")
        == "DIGITAL_CALIPER"
    )


def test_name_quality_slash():
    assert "slash_separated_title" in name_quality_flags("گیج/میکرومتر")
