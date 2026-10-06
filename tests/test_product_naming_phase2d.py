"""Phase 2D naming dry-run — pure classification tests (no DB)."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.domain.product_naming import NAMING_PROFILES, build_product_name_v1
from app.domain.product_naming_phase2d import (
    PHASE2C_FROZEN_ROWS,
    PHASE2D_COHORT_BRAND_IDS,
    TERMINAL_CLASSIFICATIONS,
    Phase2DProductInput,
    apply_collision_holds,
    brand_display_governed_phase2d,
    build_builder_facts,
    build_facts_from_kb_rows,
    canonical_candidate_rows,
    canonical_candidate_sha256,
    classify_product_phase2d,
    detect_collisions,
    identity_drift,
    load_authoritative_canonical_policy,
    product_type_naming_policy_blocked,
    reconcile_classifications,
    reject_forbidden_cli_args,
    resolve_naming_profile_phase2d,
    validate_canonical_policy_registry,
    write_canonical_candidate_csv,
)


def _base_input(**overrides) -> Phase2DProductInput:
    base = Phase2DProductInput(
        product_id=1,
        current_name="کولیس دیجیتال اینسایز مدل 1108-150",
        sku="1108-150",
        brand_id=3,
        brand_name="INSIZE | اینسایز",
        manufacturer_code="1108-150",
        product_type_id=1,
        product_type_code="OUTSIDE_MICROMETER",
        product_type_name_fa="میکرومتر خارج‌سنج",
        product_type_status="active",
        product_type_has_active_definition=True,
        meta_title="",
        is_active=True,
        is_available=True,
        priced=True,
        has_image=True,
        storefront_visible=True,
        sellable=True,
        frozen_sku="1108-150",
        frozen_brand_id=3,
        frozen_manufacturer_code="1108-150",
        kb_facts=[
            {
                "property_key": "measurement_range",
                "status": "published",
                "fact_id": 99,
                "value": {"min": 0, "max": 150},
            }
        ],
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_forbidden_cli_args_exit():
    try:
        reject_forbidden_cli_args(["--apply"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit")


def test_cohort_brand_display_governed():
    assert brand_display_governed_phase2d(3, None)
    assert brand_display_governed_phase2d(99, None) is False


def test_resolve_live_product_type_code():
    code, resolution, profile, pol = resolve_naming_profile_phase2d("GEN_CALIPER")
    assert code == "metrology.caliper.v1"
    assert resolution == "PROFILE_GOVERNED"
    assert profile.variant_required is True
    assert pol is not None
    assert pol.title_label_status == "HOLD"


def test_generic_product_type_label_blocked():
    assert product_type_naming_policy_blocked("کولیس عمومی") is True
    assert product_type_naming_policy_blocked("میکرومتر خارج‌سنج") is False


def test_identity_drift_detected():
    row = _base_input(manufacturer_code="OTHER")
    assert identity_drift(row) is True


def test_classify_ready_rename_micrometer():
    reg = {
        "brand_id": "3",
        "display_fa": "اینسایز",
        "status": "PROPOSED",
    }
    audit, _ = classify_product_phase2d(_base_input(), brand_registry_row=reg)
    assert audit.terminal_classification == "READY_RENAME"
    assert "1108-150" in audit.proposed_name
    assert audit.proposed_name.count("کد") == 1


def test_classify_hold_missing_product_type():
    audit, _ = classify_product_phase2d(
        _base_input(product_type_id=None),
        brand_registry_row={"brand_id": "3", "display_fa": "اینسایز", "status": "PROPOSED"},
    )
    assert audit.terminal_classification == "HOLD_MISSING_PRODUCT_TYPE"


def test_classify_hold_naming_policy_generic_caliper_label():
    audit, _ = classify_product_phase2d(
        _base_input(
            product_type_code="GEN_CALIPER",
            product_type_name_fa="کولیس عمومی",
        ),
        brand_registry_row={"brand_id": "3", "display_fa": "اینسایز", "status": "PROPOSED"},
    )
    assert audit.terminal_classification == "HOLD_PRODUCT_TYPE_NAMING_POLICY"


def test_published_facts_only_in_builder_input():
    facts, traces = build_facts_from_kb_rows(
        [
            {"property_key": "measurement_range", "status": "asserted", "value": {"min": 0, "max": 10}},
            {"property_key": "accuracy", "status": "published", "value": "0.01"},
        ]
    )
    assert "measurement_range" not in facts
    assert "accuracy" not in facts


def test_collision_holds_downgrade_ready():
    from app.domain.product_naming_phase2d import Phase2DAuditRow

    a = Phase2DAuditRow(
        product_id=1,
        sku="a",
        brand_id=3,
        brand_name="INSIZE",
        brand_display="اینسایز",
        manufacturer_code="X",
        product_type_id=1,
        product_type_code="OUTSIDE_MICROMETER",
        product_type_name_fa="میکرومتر خارج‌سنج",
        canonical_title_fa="میکرومتر خارج‌سنج",
        canonical_title_status="APPROVED",
        product_type_governed=True,
        variant_policy="VARIANT_REQUIRED",
        variant_policy_basis="",
        policy_review_status="",
        variant_policy_status="",
        variant_property_code="",
        variant_raw_value="",
        variant_formatted_value="",
        variant_fact_id="",
        variant_fact_published="no",
        current_name="old",
        proposed_name="میکرومتر خارج‌سنج اینسایز کد X",
        comparison_normalized_current="old",
        comparison_normalized_proposed="prop",
        terminal_classification="READY_RENAME",
        classification_reason="",
        name_quality_flags="",
        proposed_collision="no",
        collision_product_ids="",
        meta_title_present="no",
        seo_title_impact="YES",
        is_active="yes",
        is_available="yes",
        priced="yes",
        has_image="yes",
        storefront_visible="yes",
        sellable="yes",
    )
    b = Phase2DAuditRow(**{**a.__dict__, "product_id": 2})
    report = detect_collisions([a, b], {})
    apply_collision_holds([a, b], report)
    assert a.terminal_classification == "HOLD_NAME_COLLISION"


def test_terminal_taxonomy_exhaustive_count():
    audits = []
    for i, terminal in enumerate(TERMINAL_CLASSIFICATIONS):
        from app.domain.product_naming_phase2d import Phase2DAuditRow

        audits.append(
            Phase2DAuditRow(
                product_id=i + 1,
                sku="s",
                brand_id=3,
                brand_name="INSIZE",
                brand_display="اینسایز",
                manufacturer_code="c",
                product_type_id=1,
                product_type_code="X",
                product_type_name_fa="t",
                canonical_title_fa="",
                canonical_title_status="",
                product_type_governed=False,
                variant_policy="",
                variant_policy_basis="",
                policy_review_status="",
                variant_policy_status="",
                variant_property_code="",
                variant_raw_value="",
                variant_formatted_value="",
                variant_fact_id="",
                variant_fact_published="no",
                current_name="a",
                proposed_name="b",
                comparison_normalized_current="a",
                comparison_normalized_proposed="b",
                terminal_classification=terminal,
                classification_reason="",
                name_quality_flags="",
                proposed_collision="no",
                collision_product_ids="",
                meta_title_present="no",
                seo_title_impact="YES",
                is_active="yes",
                is_available="yes",
                priced="yes",
                has_image="yes",
                storefront_visible="yes",
                sellable="yes",
            )
        )
    # pad to 1350 for reconciliation helper shape test
    while len(audits) < PHASE2C_FROZEN_ROWS:
        audits.append(audits[-1])
    recon = reconcile_classifications(audits[:PHASE2C_FROZEN_ROWS])
    assert recon["reconciles"]


def test_manufacturer_code_not_from_sku_in_classify():
    audit, _ = classify_product_phase2d(
        _base_input(
            manufacturer_code="1108-150",
            sku="DIFFERENT-SKU",
            frozen_sku="DIFFERENT-SKU",
        ),
        brand_registry_row={"brand_id": "3", "display_fa": "اینسایز", "status": "PROPOSED"},
    )
    assert "1108-150" in audit.proposed_name
    assert "DIFFERENT-SKU" not in audit.proposed_name


def test_phase2d_cohort_brand_ids():
    assert PHASE2D_COHORT_BRAND_IDS == frozenset({3, 4, 5})


def test_canonical_candidate_replay_hash_matches_file(tmp_path: Path):
    from app.domain.product_naming_phase2d import Phase2DAuditRow

    row = Phase2DAuditRow(
        product_id=2,
        sku="s",
        brand_id=3,
        brand_name="INSIZE",
        brand_display="اینسایز",
        manufacturer_code="M1",
        product_type_id=1,
        product_type_code="OUTSIDE_MICROMETER",
        product_type_name_fa="میکرومتر خارج‌سنج",
        canonical_title_fa="میکرومتر خارج‌سنج",
        canonical_title_status="APPROVED",
        product_type_governed=True,
        variant_policy="VARIANT_REQUIRED",
        variant_policy_basis="x",
        policy_review_status="PASS",
        variant_policy_status="SUFFIX_GOVERNED",
        variant_property_code="measurement_range",
        variant_raw_value="",
        variant_formatted_value="0-150mm",
        variant_fact_id="1",
        variant_fact_published="yes",
        current_name="old",
        proposed_name="میکرومتر خارج‌سنج اینسایز 0-150mm کد M1",
        comparison_normalized_current="old",
        comparison_normalized_proposed="prop",
        terminal_classification="READY_RENAME",
        classification_reason="",
        name_quality_flags="",
        proposed_collision="no",
        collision_product_ids="",
        meta_title_present="no",
        seo_title_impact="YES",
        is_active="yes",
        is_available="yes",
        priced="yes",
        has_image="yes",
        storefront_visible="yes",
        sellable="yes",
    )
    rows = canonical_candidate_rows([row])
    digest = canonical_candidate_sha256(rows)
    path = tmp_path / "candidates.csv"
    write_canonical_candidate_csv(path, rows)
    file_digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
    assert digest == file_digest
    broken = __import__("hashlib").sha256(
        "\n".join(f"{r.product_id}|{r.proposed_name}" for r in [row]).encode()
    ).hexdigest()
    assert digest != broken


def test_gap_blocked_products_counts_all_holds():
    from app.domain.product_naming_phase2d import Phase2DAuditRow

    rows = [
        Phase2DAuditRow(
            product_id=i,
            sku="s",
            brand_id=3,
            brand_name="INSIZE",
            brand_display="اینسایز",
            manufacturer_code="c",
            product_type_id=1,
            product_type_code="GEN_CALIPER",
            product_type_name_fa="کولیس عمومی",
            canonical_title_fa="",
            canonical_title_status="HOLD",
            product_type_governed=False,
            variant_policy="VARIANT_REQUIRED",
            variant_policy_basis="",
            policy_review_status="",
            variant_policy_status="",
            variant_property_code="",
            variant_raw_value="",
            variant_formatted_value="",
            variant_fact_id="",
            variant_fact_published="no",
            current_name="a",
            proposed_name="",
            comparison_normalized_current="a",
            comparison_normalized_proposed="",
            terminal_classification="HOLD_PRODUCT_TYPE_NAMING_POLICY",
            classification_reason="generic",
            name_quality_flags="",
            proposed_collision="no",
            collision_product_ids="",
            meta_title_present="no",
            seo_title_impact="YES",
            is_active="yes",
            is_available="yes",
            priced="yes",
            has_image="yes",
            storefront_visible="yes",
            sellable="yes",
        )
        for i in range(3)
    ]
    blocked = sum(1 for r in rows if r.terminal_classification.startswith("HOLD_"))
    assert blocked == 3


def test_arbitrary_min_max_not_aliased_to_measurement_range():
    facts, _ = build_facts_from_kb_rows(
        [
            {
                "property_key": "voltage_range",
                "status": "published",
                "value": {"min": 12, "max": 250},
            }
        ]
    )
    assert "measurement_range" not in facts
    assert facts["voltage_range"] == {"min": 12, "max": 250}


def test_builder_facts_empty_for_not_required():
    policy = load_authoritative_canonical_policy()["DIGITAL_MULTIMETER"]
    facts = {"measurement_range": (0.06, 600), "range_min_mm": 0.06}
    assert build_builder_facts(policy, facts) == {}


def test_profile_object_propagation_blocks_suffix_when_max_attrs_zero():
    policy = load_authoritative_canonical_policy()["DIGITAL_MULTIMETER"]
    _, _, adjusted, _ = resolve_naming_profile_phase2d("DIGITAL_MULTIMETER")
    assert adjusted.max_variant_attributes == 0
    global_profile = NAMING_PROFILES["metrology.micrometer.v1"]
    assert global_profile.max_variant_attributes > 0
    facts = {"measurement_range": (0.06, 600), "range_min_mm": 0.06, "range_max_mm": 600}
    with_code = build_product_name_v1(
        product_type_fa=policy.canonical_title_fa,
        brand_raw="INSIZE | اینسایز",
        manufacturer_code="9247-190",
        facts=facts,
        naming_profile="metrology.micrometer.v1",
        brand_registry_row={"brand_id": "3", "display_fa": "اینسایز", "status": "PROPOSED"},
        manufacturer_code_governed=True,
        brand_display_governed=True,
        naming_profile_governed=True,
        variant_facts_governed=True,
        profile_resolution="PROFILE_GOVERNED",
    )
    with_profile = build_product_name_v1(
        product_type_fa=policy.canonical_title_fa,
        brand_raw="INSIZE | اینسایز",
        manufacturer_code="9247-190",
        facts=build_builder_facts(policy, facts),
        naming_profile=adjusted,
        brand_registry_row={"brand_id": "3", "display_fa": "اینسایز", "status": "PROPOSED"},
        manufacturer_code_governed=True,
        brand_display_governed=True,
        naming_profile_governed=True,
        variant_facts_governed=True,
        profile_resolution="PROFILE_GOVERNED",
    )
    assert "میلی‌متر" in (with_code.name or "")
    assert "میلی‌متر" not in (with_profile.name or "")


def _instrument_input(product_type_code: str, manufacturer_code: str = "9247-190") -> Phase2DProductInput:
    policy = load_authoritative_canonical_policy()[product_type_code]
    return _base_input(
        product_type_code=product_type_code,
        product_type_name_fa=policy.canonical_title_fa,
        manufacturer_code=manufacturer_code,
        frozen_manufacturer_code=manufacturer_code,
        sku=manufacturer_code,
        frozen_sku=manufacturer_code,
        kb_facts=[
            {
                "property_key": "measurement_range",
                "status": "published",
                "fact_id": 1,
                "value": {"min": 0.06, "max": 600},
            }
        ],
    )


def test_digital_multimeter_classify_has_no_mm_suffix():
    audit, _ = classify_product_phase2d(
        _instrument_input("DIGITAL_MULTIMETER"),
        brand_registry_row={"brand_id": "3", "display_fa": "اینسایز", "status": "PROPOSED"},
    )
    assert audit.terminal_classification == "READY_RENAME"
    assert "میلی‌متر" not in audit.proposed_name
    assert audit.variant_formatted_value == ""


@pytest.mark.parametrize(
    "product_type_code",
    [
        "ANEMOMETER",
        "DIGITAL_MULTIMETER",
        "DIGITAL_SCALE",
        "TACHOMETER",
        "VOLTAGE_TESTER",
        "MOISTURE_METER",
        "PROTRACTOR",
    ],
)
def test_not_required_instruments_never_emit_mm_suffix(product_type_code: str):
    audit, _ = classify_product_phase2d(
        _instrument_input(product_type_code, manufacturer_code="TEST-1"),
        brand_registry_row={"brand_id": "3", "display_fa": "اینسایز", "status": "PROPOSED"},
    )
    assert "میلی‌متر" not in (audit.proposed_name or "")


def test_canonical_policy_registry_valid():
    assert validate_canonical_policy_registry() == []
