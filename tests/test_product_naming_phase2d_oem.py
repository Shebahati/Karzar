"""Phase 2D OEM semantic authority tests."""

from __future__ import annotations

from app.domain.product_naming_phase2d import Phase2DAuditRow
from app.domain.product_naming_phase2d_oem import apply_oem_semantic_holds, evaluate_oem_semantic
from app.domain.product_naming_phase2d_oem_extract import load_identity_registry


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


def test_known_protractor_vs_digital_level_conflict():
    reg = load_identity_registry()
    identity = reg["2170-1"]
    ev = evaluate_oem_semantic(
        product_type_code="PROTRACTOR",
        canonical_title_fa="زاویه‌سنج",
        identity=identity,
    )
    assert ev.semantic_match_status == "OEM_PRODUCT_TYPE_CONFLICT"
    assert ev.hold_terminal == "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT"
    assert ev.recommended_product_type_code == "DIGITAL_LEVEL"
    assert int(identity.pdf_page) == 587


def test_multifunction_humidity_meter_conflict():
    reg = load_identity_registry()
    identity = reg["0312-TH50"]
    ev = evaluate_oem_semantic(
        product_type_code="MOISTURE_METER",
        canonical_title_fa="رطوبت‌سنج",
        identity=identity,
    )
    assert ev.semantic_match_status == "OEM_MULTI_FUNCTION_TITLE_CONFLICT"
    assert ev.hold_terminal == "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT"
    assert "دما" in ev.recommended_canonical_title_fa


def test_oem_gate_downgrades_ready_rows():
    reg = load_identity_registry()
    audits = [
        _ready_row(
            product_id=3485,
            manufacturer_code="2170-1",
            product_type_code="PROTRACTOR",
            canonical_title_fa="زاویه‌سنج",
        )
    ]
    rows, meta = apply_oem_semantic_holds(audits, reg)
    assert audits[0].terminal_classification == "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT"
    assert rows[0]["candidate_eligible_after_oem_gate"] == "no"
    assert meta["pre_exact_gate_candidates"] == 1


def test_missing_oem_evidence_cannot_stay_ready():
    audits = [
        _ready_row(
            product_id=1,
            manufacturer_code="UNKNOWN-CODE-XY",
            product_type_code="OUTSIDE_MICROMETER",
            canonical_title_fa="میکرومتر خارج‌سنج",
        )
    ]
    _rows, _meta = apply_oem_semantic_holds(audits, {})
    assert audits[0].terminal_classification == "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING"


def test_zero_setter_not_square_anvil_false_conflict():
    reg = load_identity_registry()
    identity = reg["6557-50"]
    ev = evaluate_oem_semantic(
        product_type_code="ZERO_SETTER",
        canonical_title_fa="صفرکن محور Z",
        identity=identity,
    )
    assert identity.evidence_status == "EXACT_PRODUCT_IDENTITY"
    assert "ZERO SETTER" in identity.oem_product_heading
    assert ev.semantic_match_status == "OEM_SEMANTIC_MATCH"
    assert ev.canonical_title_verdict == "OEM_TITLE_EXACT"
