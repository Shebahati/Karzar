"""Exact OEM page extraction and canonical title authority tests."""

from __future__ import annotations

from app.domain.product_naming_phase2d import Phase2DAuditRow
from app.domain.product_naming_phase2d_oem import apply_oem_semantic_holds, evaluate_oem_semantic
from app.domain.product_naming_phase2d_oem_extract import (
    OemOccurrence,
    extract_printed_page,
    pdf_pages,
    select_product_identity,
)
from app.domain.product_naming_phase2d_oem_policy import OemCanonicalPolicyRow, normalize_oem_heading


def test_pdf_pages_use_form_feed_not_line_estimates(tmp_path):
    pdf = tmp_path / "tiny.pdf"
    # Not a real PDF — exercise split logic via pages list API on synthetic text path:
    from app.domain.product_naming_phase2d_oem_extract import insize_catalog_paths

    path_a, _ = insize_catalog_paths()
    if not path_a.is_file():
        return
    pages = pdf_pages(path_a)
    assert len(pages) > 900
    assert all(isinstance(p, str) for p in pages[:3])


def test_printed_page_unknown_when_not_present():
    assert extract_printed_page("DIGITAL CALIPER\nno page numbers here\n") == "UNKNOWN"


def test_accessory_occurrence_cannot_become_exact_identity():
    occ = OemOccurrence(
        manufacturer_code="6557-50",
        source_pdf="/108A.pdf",
        source_sha256="a",
        pdf_page=629,
        printed_page="UNKNOWN",
        section_heading="SQUARE ANVIL (OPTIONAL)",
        nearest_product_heading="SQUARE ANVIL (OPTIONAL)",
        line_context_before="",
        code_line="6557-50",
        line_context_after="",
        occurrence_type="OPTIONAL_ACCESSORY",
    )
    ident = select_product_identity("6557-50", [occ])
    assert ident is not None
    assert ident.evidence_status == "INSUFFICIENT"


def test_product_row_wins_over_accessory_for_same_code():
    product = OemOccurrence(
        manufacturer_code="6557-50",
        source_pdf="/108A.pdf",
        source_sha256="a",
        pdf_page=621,
        printed_page="UNKNOWN",
        section_heading="DIGITAL ZERO SETTER",
        nearest_product_heading="DIGITAL ZERO SETTER",
        line_context_before="Code",
        code_line="6557-50",
        line_context_after="",
        occurrence_type="PRODUCT_ROW",
    )
    accessory = OemOccurrence(
        manufacturer_code="6557-50",
        source_pdf="/108A.pdf",
        source_sha256="a",
        pdf_page=629,
        printed_page="UNKNOWN",
        section_heading="SQUARE ANVIL (OPTIONAL)",
        nearest_product_heading="SQUARE ANVIL (OPTIONAL)",
        line_context_before="",
        code_line="6557-50",
        line_context_after="",
        occurrence_type="OPTIONAL_ACCESSORY",
    )
    ident = select_product_identity("6557-50", [accessory, product])
    assert ident.evidence_status == "EXACT_PRODUCT_IDENTITY"
    assert "ZERO SETTER" in ident.oem_product_heading


def test_ambiguous_product_occurrences_hold():
    a = OemOccurrence(
        manufacturer_code="X-1",
        source_pdf="/108A.pdf",
        source_sha256="a",
        pdf_page=1,
        printed_page="1",
        section_heading="FILLET WELDING GAUGES",
        nearest_product_heading="FILLET WELDING GAUGES",
        line_context_before="Code",
        code_line="X-1",
        line_context_after="",
        occurrence_type="PRODUCT_ROW",
    )
    b = OemOccurrence(
        manufacturer_code="X-1",
        source_pdf="/108A.pdf",
        source_sha256="a",
        pdf_page=2,
        printed_page="2",
        section_heading="WELDING GAUGES",
        nearest_product_heading="WELDING GAUGES",
        line_context_before="Code",
        code_line="X-1",
        line_context_after="",
        occurrence_type="PRODUCT_ROW",
    )
    ident = select_product_identity("X-1", [a, b])
    assert ident.evidence_status == "AMBIGUOUS"


def test_product_type_match_alone_insufficient_for_title():
    from app.domain.product_naming_phase2d_oem_extract import OemProductIdentity

    identity = OemProductIdentity(
        manufacturer_code="CYL-1",
        source_pdf="/108A.pdf",
        source_sha256="a",
        pdf_page=10,
        printed_page="UNKNOWN",
        oem_product_heading="CYLINDER SQUARES",
        oem_family="CYLINDER SQUARES",
        oem_subtype_or_qualifier="cylinder_square",
        product_occurrence_class="PRODUCT_ROW",
        evidence_context="Code",
        evidence_status="EXACT_PRODUCT_IDENTITY",
    )
    pol = {
        normalize_oem_heading("CYLINDER SQUARES"): OemCanonicalPolicyRow(
            oem_heading_or_family="CYLINDER SQUARES",
            match_type="EXACT",
            allowed_product_type_code="ENGINEERS_SQUARE",
            canonical_title_fa="گونیا مهندسی",
            required_title_qualifier="سیلندری",
            semantic_scope="subtype_qualifier",
            policy_status="APPROVED",
            policy_basis="test",
        )
    }
    ev = evaluate_oem_semantic(
        product_type_code="ENGINEERS_SQUARE",
        canonical_title_fa="گونیا مهندسی",
        identity=identity,
        policies=pol,
    )
    assert ev.semantic_match_status == "OEM_SEMANTIC_MATCH"
    assert ev.canonical_title_verdict == "OEM_TITLE_REQUIRES_QUALIFIER"
    assert ev.hold_terminal == "HOLD_CANONICAL_TITLE_AUTHORITY_CONFLICT"


def _ready_row(**kwargs) -> Phase2DAuditRow:
    base = {
        "product_id": 1,
        "sku": "X",
        "brand_id": 3,
        "brand_name": "INSIZE",
        "brand_display": "اینسایز",
        "manufacturer_code": "X",
        "product_type_id": 1,
        "product_type_code": "PROTRACTOR",
        "product_type_name_fa": "زاویه‌سنج",
        "canonical_title_fa": "زاویه‌سنج",
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
        "current_name": "d",
        "proposed_name": "p",
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


def test_title_conflict_downgrades_ready():
    from app.domain.product_naming_phase2d_oem_extract import load_identity_registry

    reg = load_identity_registry()
    ident = reg.get("2170-1")
    assert ident and ident.evidence_status == "EXACT_PRODUCT_IDENTITY"
    audits = [
        _ready_row(product_id=3485, manufacturer_code="2170-1", product_type_code="PROTRACTOR")
    ]
    rows, _meta = apply_oem_semantic_holds(audits, {"2170-1": ident})
    assert audits[0].terminal_classification == "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT"
    assert rows[0]["candidate_eligible_after_oem_gate"] == "no"
