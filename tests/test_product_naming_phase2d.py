"""Phase 2D naming dry-run — pure classification tests (no DB)."""

from __future__ import annotations

from app.domain.product_naming_phase2d import (
    PHASE2C_FROZEN_ROWS,
    PHASE2D_COHORT_BRAND_IDS,
    Phase2DProductInput,
    TERMINAL_CLASSIFICATIONS,
    apply_collision_holds,
    brand_display_governed_phase2d,
    build_facts_from_kb_rows,
    classify_product_phase2d,
    detect_collisions,
    identity_drift,
    product_type_naming_policy_blocked,
    reconcile_classifications,
    reject_forbidden_cli_args,
    resolve_naming_profile_phase2d,
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
    code, resolution, profile = resolve_naming_profile_phase2d("GEN_CALIPER")
    assert code == "metrology.caliper.v1"
    assert resolution == "PROFILE_GOVERNED"
    assert profile.variant_required is True


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
    assert "accuracy" in facts


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
        product_type_governed=True,
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
                product_type_governed=False,
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
