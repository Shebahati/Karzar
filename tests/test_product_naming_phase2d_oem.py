"""Phase 2D OEM semantic authority tests."""

from __future__ import annotations

from app.domain.product_naming_phase2d import Phase2DAuditRow
from app.domain.product_naming_phase2d_oem import (
    OemCodeRecord,
    apply_oem_semantic_holds,
    evaluate_oem_semantic,
)


def _ready_row(
    *,
    product_id: int,
    manufacturer_code: str,
    product_type_code: str,
    canonical_title_fa: str,
) -> Phase2DAuditRow:
    return Phase2DAuditRow(
        product_id=product_id,
        sku=manufacturer_code,
        brand_id=3,
        brand_name="INSIZE",
        brand_display="اینسایز",
        manufacturer_code=manufacturer_code,
        product_type_id=20,
        product_type_code=product_type_code,
        product_type_name_fa=canonical_title_fa,
        canonical_title_fa=canonical_title_fa,
        canonical_title_status="APPROVED",
        product_type_governed=True,
        variant_policy="VARIANT_NOT_REQUIRED_APPROVED",
        variant_policy_basis="test",
        policy_review_status="PASS",
        variant_policy_status="VARIANT_NOT_REQUIRED_APPROVED",
        variant_property_code="",
        variant_raw_value="",
        variant_formatted_value="",
        variant_fact_id="",
        variant_fact_published="no",
        current_name="diag only",
        proposed_name=f"{canonical_title_fa} اینسایز کد {manufacturer_code}",
        comparison_normalized_current="a",
        comparison_normalized_proposed="b",
        terminal_classification="READY_RENAME",
        classification_reason="",
        name_quality_flags="",
        proposed_collision="no",
        collision_product_ids="",
        meta_title_present="yes",
        seo_title_impact="NO_DIRECT_TITLE_FALLBACK",
        is_active="yes",
        is_available="yes",
        priced="yes",
        has_image="yes",
        storefront_visible="yes",
        sellable="yes",
    )


def _oem_level(code: str) -> OemCodeRecord:
    return OemCodeRecord(
        manufacturer_code=code,
        oem_source="/catalog/108A.pdf",
        oem_source_sha256="4b251dbbd6b662e64dcc1703dd373886f8e3df8e3363a5406bc706c8aa85123b",
        oem_page_pdf="497",
        oem_page_printed="497",
        oem_section="DIGITAL LEVELS AND SLOPE METERS",
        oem_product_heading="DIGITAL LEVELS AND SLOPE METERS",
        oem_category_or_family="DIGITAL LEVELS AND SLOPE METERS",
        oem_code=code,
    )


def test_known_protractor_vs_digital_level_conflict():
    oem = _oem_level("2170-1")
    status, reason, hold, rec_pt, _ = evaluate_oem_semantic(
        product_type_code="PROTRACTOR",
        canonical_title_fa="زاویه‌سنج",
        oem=oem,
    )
    assert status == "OEM_PRODUCT_TYPE_CONFLICT"
    assert hold == "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT"
    assert rec_pt == "DIGITAL_LEVEL"
    assert reason


def test_multifunction_humidity_meter_conflict():
    oem = OemCodeRecord(
        manufacturer_code="0312-TH50",
        oem_source="/catalog/108B.pdf",
        oem_source_sha256="31fd0d0eec73bab9cdd750701ec999368536d909e40b340f8420580f7691eb26",
        oem_page_pdf="336",
        oem_page_printed="336",
        oem_section="TEMPERATURE AND HUMIDITY METER (ECONOMIC TYPE)",
        oem_product_heading="TEMPERATURE AND HUMIDITY METER (ECONOMIC TYPE)",
        oem_category_or_family="TEMPERATURE AND HUMIDITY METER (ECONOMIC TYPE)",
        oem_code="0312-TH50",
    )
    status, _reason, hold, _rec, rec_title = evaluate_oem_semantic(
        product_type_code="MOISTURE_METER",
        canonical_title_fa="رطوبت‌سنج",
        oem=oem,
    )
    assert status == "OEM_MULTI_FUNCTION_TITLE_CONFLICT"
    assert hold == "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT"
    assert "دما" in rec_title


def test_oem_gate_downgrades_ready_rows():
    audits = [
        _ready_row(
            product_id=3485,
            manufacturer_code="2170-1",
            product_type_code="PROTRACTOR",
            canonical_title_fa="زاویه‌سنج",
        )
    ]
    index = {"2170-1": _oem_level("2170-1")}
    rows, meta = apply_oem_semantic_holds(audits, index)
    assert audits[0].terminal_classification == "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT"
    assert rows[0]["candidate_eligible_after_oem_gate"] == "no"
    assert meta["pre_oem_READY"] == 1


def test_missing_oem_evidence_cannot_stay_ready():
    audits = [
        _ready_row(
            product_id=1,
            manufacturer_code="UNKNOWN-CODE",
            product_type_code="OUTSIDE_MICROMETER",
            canonical_title_fa="میکرومتر خارج‌سنج",
        )
    ]
    _rows, _meta = apply_oem_semantic_holds(audits, {})
    assert audits[0].terminal_classification == "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING"


def test_load_index_has_known_conflict_codes():
    from app.domain.product_naming_phase2d_oem import load_oem_code_index

    index = load_oem_code_index()
    assert index["2175-360"].oem_category_or_family.startswith("DIGITAL LEVEL")
    assert "TEMPERATURE AND HUMIDITY" in index["0312-TH50"].oem_category_or_family
