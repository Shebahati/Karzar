"""Owner canonical title precision gate tests."""

from __future__ import annotations

from app.domain.product_naming_phase2d import Phase2DAuditRow
from app.domain.product_naming_phase2d_owner_title import (
    apply_owner_title_holds,
    evaluate_owner_title,
    rebuild_proposed_name_with_title,
)


def _ready_audit(**kwargs) -> Phase2DAuditRow:
    base = {
        "product_id": 1,
        "sku": "X",
        "brand_id": 3,
        "brand_name": "INSIZE",
        "brand_display": "اینسایز",
        "manufacturer_code": "4112-8604",
        "product_type_id": 1,
        "product_type_code": "DIGITAL_SCALE",
        "product_type_name_fa": "ترازوی دیجیتال",
        "canonical_title_fa": "ترازوی دیجیتال",
        "canonical_title_status": "APPROVED",
        "product_type_governed": True,
        "variant_policy": "VARIANT_NOT_REQUIRED_APPROVED",
        "variant_policy_basis": "t",
        "policy_review_status": "PASS",
        "variant_policy_status": "VARIANT_NOT_REQUIRED_APPROVED",
        "variant_property_code": "",
        "variant_raw_value": "",
        "variant_formatted_value": "",
        "variant_fact_id": "",
        "variant_fact_published": "no",
        "current_name": "legacy",
        "proposed_name": "ترازوی دیجیتال اینسایز کد 4112-8604",
        "comparison_normalized_current": "a",
        "comparison_normalized_proposed": "b",
        "terminal_classification": "READY_RENAME",
        "classification_reason": "",
        "name_quality_flags": "",
        "proposed_collision": "no",
        "collision_product_ids": "",
        "meta_title_present": "yes",
        "seo_title_impact": "NO_DIRECT_TITLE_FALLBACK",
        "is_active": "yes",
        "is_available": "yes",
        "priced": "yes",
        "has_image": "yes",
        "storefront_visible": "yes",
        "sellable": "yes",
    }
    base.update(kwargs)
    return Phase2DAuditRow(**base)


def test_crane_scale_not_generic_digital_scale():
    verdict, _reason, status, final, _ = evaluate_owner_title(
        oem_product_heading="PORTABLE CRANE SCALE",
        product_type_code="DIGITAL_SCALE",
        canonical_title_fa="ترازوی دیجیتال",
    )
    assert status == "APPROVED"
    assert "جرثقیلی" in final
    assert verdict != "OWNER_TITLE_HOLD"


def test_digital_protractor_requires_digital_qualifier_in_final():
    _v, _r, status, final, _ = evaluate_owner_title(
        oem_product_heading="DIGITAL PROTRACTOR",
        product_type_code="PROTRACTOR",
        canonical_title_fa="زاویه‌سنج",
    )
    assert status == "APPROVED"
    assert "دیجیتال" in final


def test_pocket_scale_preserves_pocket():
    _v, _r, status, final, _ = evaluate_owner_title(
        oem_product_heading="ELECTRONIC POCKET SCALE (ECONOMIC TYPE)",
        product_type_code="DIGITAL_SCALE",
        canonical_title_fa="ترازوی دیجیتال",
    )
    assert status == "APPROVED"
    assert "جیبی" in final


def test_pipe_welding_gauge_preserves_pipe():
    _v, _r, status, final, _ = evaluate_owner_title(
        oem_product_heading="PIPE WELDING GAUGE",
        product_type_code="WELDING_GAUGE",
        canonical_title_fa="گیج جوش",
    )
    assert status == "APPROVED"
    assert "لوله" in final


def test_counter_micrometer_preserves_counter():
    _v, _r, status, final, _ = evaluate_owner_title(
        oem_product_heading="OUTSIDE MICROMETERS WITH COUNTER",
        product_type_code="OUTSIDE_MICROMETER",
        canonical_title_fa="میکرومتر خارج‌سنج",
    )
    assert status == "APPROVED"
    assert "کنتوردار" in final


def test_internal_interchangeable_caliper_holds():
    verdict, _reason, status, final, _ = evaluate_owner_title(
        oem_product_heading="INTERNAL DIAL CALIPER GAUGES WITH INTERCHANGEABLE POINTS",
        product_type_code="INDICATING_CALIPER",
        canonical_title_fa="پرگار نشان‌گر",
    )
    assert status == "HOLD"
    assert verdict == "OWNER_TITLE_HOLD"
    assert not final


def test_owner_hold_downgrades_ready():
    audit = _ready_audit(
        product_id=1889,
        manufacturer_code="2223-153",
        product_type_code="INDICATING_CALIPER",
        canonical_title_fa="پرگار نشان‌گر",
        proposed_name="پرگار نشان‌گر اینسایز کد 2223-153، 55–153 میلی‌متر",
    )
    oem_rows = [
        {
            "product_id": "1889",
            "oem_product_heading": "INTERNAL DIAL CALIPER GAUGES WITH INTERCHANGEABLE POINTS",
            "candidate_eligible_after_oem_gate": "yes",
        }
    ]
    apply_owner_title_holds([audit], oem_rows)
    assert audit.terminal_classification == "HOLD_OWNER_CANONICAL_TITLE_REVIEW"


def test_oem_pass_alone_does_not_imply_owner_approval_without_policy():
    audit = _ready_audit(product_type_code="UNKNOWN_PT")
    oem_rows = [
        {
            "product_id": "1",
            "oem_product_heading": "UNKNOWN HEADING",
            "candidate_eligible_after_oem_gate": "yes",
        }
    ]
    apply_owner_title_holds([audit], oem_rows)
    assert audit.terminal_classification == "HOLD_OWNER_CANONICAL_TITLE_REVIEW"


def test_rebuild_proposed_name_swaps_title_prefix():
    audit = _ready_audit(
        proposed_name="ترازوی دیجیتال اینسایز کد 4112-8604",
        canonical_title_fa="ترازوی دیجیتال",
        manufacturer_code="4112-8604",
    )
    new_name = rebuild_proposed_name_with_title(audit, "ترازوی جرثقیلی دیجیتال")
    assert new_name.startswith("ترازوی جرثقیلی دیجیتال")
    assert "کد 4112-8604" in new_name
