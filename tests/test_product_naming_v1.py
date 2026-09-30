"""Pure unit tests for Karzar Product Naming Standard v1 (no DB)."""

from __future__ import annotations

from app.domain.product_naming import (
    HARD_LENGTH_LIMIT,
    NAMING_STANDARD_VERSION,
    PROFILE_GOVERNED,
    PROFILE_MISSING,
    brand_display_for_title,
    brand_display_is_governed,
    build_product_name_v1,
    compare_product_name_v1,
    extract_manufacturer_code_candidates,
    format_diameter_mm,
    format_measurement_range_mm,
    format_metric_thread,
    lint_product_name_v1,
    manufacturer_code_is_governed,
    normalize_persian_text,
    resolve_naming_profile_v1,
)


def test_insize_caliper_1108_150_exact_string():
    result = build_product_name_v1(
        product_type="کولیس دیجیتال",
        brand="INSIZE | اینسایز",
        manufacturer_code="1108-150",
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
        product_type_governed=True,
        manufacturer_code_governed=True,
        brand_display_governed=True,
        naming_profile_governed=True,
        variant_facts_governed=True,
    )
    assert result.name == "کولیس دیجیتال اینسایز کد 1108-150، 0–150 میلی‌متر"
    assert result.state == "RENAME_SAFE"
    assert result.profile == "metrology.caliper.v1"
    assert result.naming_standard_version == NAMING_STANDARD_VERSION
    assert result.confidence == "high"
    assert "–" in result.name  # en-dash


def test_zcc_turning_insert_preserves_grade_and_hyphen():
    result = build_product_name_v1(
        product_type="اینسرت تراشکاری",
        brand="ZCC.CT | زد سی‌سی",
        manufacturer_code="DCMT11T312-XM YBC203",
        naming_profile="cutting.turning_insert.v1",
        product_type_governed=True,
    )
    assert result.name == "اینسرت تراشکاری ZCC.CT کد DCMT11T312-XM YBC203"
    assert "DCMT11T312-XM YBC203" in result.name
    assert result.state == "RENAME_SAFE"
    assert "میلی‌متر" not in (result.name or "")


def test_san_ou_chuck_capacity():
    result = build_product_name_v1(
        product_type="سه‌نظام منظم",
        brand="SAN OU | سانو",
        manufacturer_code="K11-315MM",
        facts={"capacity_mm": 315},
        naming_profile="workholding.chuck.v1",
        product_type_governed=True,
    )
    assert result.name == "سه‌نظام منظم سانو کد K11-315MM، 315 میلی‌متر"
    assert "K11-315MM" in result.name


def test_code_preservation_hyphens_spaces_grades():
    code = "SNHQ150704S NC5340"
    result = build_product_name_v1(
        product_type="اینسرت تراشکاری",
        brand="ZCC.CT",
        manufacturer_code=code,
        naming_profile="cutting.turning_insert.v1",
        preferred_brand_form="ZCC.CT",
        product_type_governed=True,
    )
    assert result.name is not None
    assert code in result.name
    assert result.name.count(code) == 1


def test_unit_formatting_helpers():
    assert format_measurement_range_mm(0, 150) == "0–150 میلی‌متر"
    assert format_measurement_range_mm(0.0, 25.0) == "0–25 میلی‌متر"
    assert format_diameter_mm(8) == "Ø8 میلی‌متر"
    assert format_metric_thread("M6", 1) == "M6×1"
    assert format_metric_thread(6, 1) == "M6×1"
    assert format_metric_thread("6", "0.75") == "M6×0.75"


def test_prohibited_terms_lint():
    hits = lint_product_name_v1("بهترین کولیس حرفه‌ای اورجینال خرید قیمت فروش کارزار")
    assert any(h.startswith("PROHIBITED_TERM:بهترین") for h in hits)
    assert any(h.startswith("PROHIBITED_TERM:حرفه‌ای") for h in hits)
    assert any(h.startswith("PROHIBITED_TERM:اورجینال") for h in hits)
    assert any(h.startswith("PROHIBITED_TERM:خرید") for h in hits)
    assert any(h.startswith("PROHIBITED_TERM:قیمت") for h in hits)
    assert any(h.startswith("PROHIBITED_TERM:فروش") for h in hits)
    assert any(h.startswith("PROHIBITED_TERM:کارزار") for h in hits)
    assert "USES_MODEL_LABEL" in lint_product_name_v1("کولیس اینسایز مدل 1108-150")


def test_missing_fields_hold():
    no_brand = build_product_name_v1(
        product_type="کولیس دیجیتال",
        brand=None,
        manufacturer_code="1108-150",
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
    )
    assert no_brand.name is None
    assert no_brand.state == "HOLD_MISSING_BRAND"

    no_code = build_product_name_v1(
        product_type="کولیس دیجیتال",
        brand="INSIZE | اینسایز",
        manufacturer_code=None,
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
    )
    assert no_code.name is None
    assert no_code.state == "HOLD_MISSING_MANUFACTURER_CODE"

    no_type = build_product_name_v1(
        product_type=None,
        brand="INSIZE | اینسایز",
        manufacturer_code="1108-150",
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
    )
    assert no_type.name is None
    assert no_type.state == "HOLD_MISSING_PRODUCT_TYPE"

    no_range = build_product_name_v1(
        product_type="کولیس دیجیتال",
        brand="INSIZE | اینسایز",
        manufacturer_code="1108-150",
        facts={},
        naming_profile="metrology.caliper.v1",
    )
    assert no_range.name is None
    assert no_range.state == "HOLD_MISSING_VARIANT_ATTRIBUTE"


def test_deterministic_same_input_same_output():
    kwargs = dict(
        product_type="کولیس دیجیتال",
        brand="INSIZE | اینسایز",
        manufacturer_code="1108-150",
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
        product_type_governed=True,
    )
    a = build_product_name_v1(**kwargs)
    b = build_product_name_v1(**kwargs)
    assert a == b
    assert a.name == b.name


def test_arabic_ye_kaf_normalization_on_persian_display_only():
    raw = "كوليس ديجيتال"  # Arabic ك and ي
    assert "ك" in raw or "ي" in raw
    normalized = normalize_persian_text(raw)
    assert "ك" not in normalized
    assert "ي" not in normalized
    assert "ک" in normalized or "ی" in normalized

    code = "XY-1108"
    result = build_product_name_v1(
        product_type="كوليس ديجيتال",
        brand="INSIZE | اينسايز",
        manufacturer_code=code,
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
        product_type_governed=True,
    )
    assert result.name is not None
    assert code in result.name
    without_code = result.name.replace(code, "")
    assert "ك" not in without_code
    assert "ي" not in without_code


def test_exact_state_when_current_matches():
    proposed = "کولیس دیجیتال اینسایز کد 1108-150، 0–150 میلی‌متر"
    result = build_product_name_v1(
        product_type="کولیس دیجیتال",
        brand="INSIZE | اینسایز",
        manufacturer_code="1108-150",
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
        current_name=proposed,
        product_type_governed=True,
    )
    assert result.state == "EXACT"
    assert result.name == proposed


def test_compare_and_brand_display_helpers():
    cmp = compare_product_name_v1(
        "کولیس دیجیتال اینسایز کد 1108-150، 0–150 میلی‌متر",
        "كوليس ديجيتال اينسايز کد 1108-150، 0–150 میلی‌متر",
    )
    assert cmp["equal"] is True
    assert cmp["classification"] == "EXACT"

    assert brand_display_for_title("INSIZE | اینسایز") == "اینسایز"
    assert brand_display_for_title("ZCC.CT | زد سی‌سی") == "ZCC.CT"
    assert brand_display_for_title("SAN OU | سانو") == "سانو"
    assert brand_display_for_title("INSIZE", preferred_form="INSIZE") == "INSIZE"


def test_hard_length_hold():
    long_type = "ت" * 240
    result = build_product_name_v1(
        product_type=long_type,
        brand="INSIZE | اینسایز",
        manufacturer_code="1108-150",
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
    )
    assert result.name is None
    assert result.state == "HOLD_NAME_TOO_LONG"
    assert len(long_type) + 20 > HARD_LENGTH_LIMIT


def test_extract_manufacturer_code_candidates():
    cands = extract_manufacturer_code_candidates(
        name="کولیس دیجیتال اینسایز مدل 1108-150",
        sku="1108-150",
        specs={"manufacturer_code": "1108-150", "accuracy": "±0.02"},
    )
    codes = [c for c, _ in cands]
    assert "1108-150" in codes


def test_thread_repair_optional_thread():
    result = build_product_name_v1(
        product_type="اینسرت ترمیم رزوه",
        brand="INSIZE | اینسایز",
        manufacturer_code="2710-M6X1",
        facts={"thread_size": "M6", "thread_pitch": 1},
        naming_profile="thread_repair.insert.v1",
        product_type_governed=True,
    )
    assert result.name == "اینسرت ترمیم رزوه اینسایز کد 2710-M6X1، M6×1"


def test_solid_tool_optional_diameter():
    result = build_product_name_v1(
        product_type="انگشتی کاربایدی",
        brand="ZCC.CT | زد سی‌سی",
        manufacturer_code="GM-4E-D8.0",
        facts={"diameter_mm": 8},
        naming_profile="cutting.solid_tool.v1",
        product_type_governed=True,
    )
    assert result.name is not None
    assert "Ø8 میلی‌متر" in result.name
    assert "GM-4E-D8.0" in result.name


def test_micrometer_requires_range():
    ok = build_product_name_v1(
        product_type="میکرومتر خارج‌سنج دیجیتال",
        brand="INSIZE | اینسایز",
        manufacturer_code="3105-25",
        facts={"range": (0, 25)},
        naming_profile="metrology.micrometer.v1",
        product_type_governed=True,
    )
    assert ok.name == "میکرومتر خارج‌سنج دیجیتال اینسایز کد 3105-25، 0–25 میلی‌متر"


def test_generic_profile_type_brand_code_only():
    result = build_product_name_v1(
        product_type="محصول صنعتی",
        brand="INSIZE | اینسایز",
        manufacturer_code="X-1",
        facts={"range_min_mm": 0, "range_max_mm": 150, "accuracy": "±0.02"},
        naming_profile="generic.v1",
        product_type_governed=True,
    )
    assert result.name == "محصول صنعتی اینسایز کد X-1"
    assert "0–150" not in result.name
    assert "accuracy" in result.omitted_fields or "OMITTED_NOISE:accuracy" in result.warnings


def test_high_requires_full_governance_contract():
    base = dict(
        product_type="کولیس دیجیتال",
        brand="INSIZE | اینسایز",
        manufacturer_code="1108-150",
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
    )
    full = dict(
        product_type_governed=True,
        manufacturer_code_governed=True,
        brand_display_governed=True,
        naming_profile_governed=True,
        variant_facts_governed=True,
    )
    both = build_product_name_v1(**base, **full)
    assert both.confidence == "high"
    assert both.state == "RENAME_SAFE"

    pt_only = build_product_name_v1(
        **base,
        product_type_governed=True,
        manufacturer_code_governed=False,
        brand_display_governed=True,
        naming_profile_governed=True,
        variant_facts_governed=True,
    )
    assert pt_only.confidence != "high"
    assert pt_only.confidence == "medium"
    assert "manufacturer_code_not_governed" in pt_only.reason_codes

    oem_only = build_product_name_v1(
        **base,
        product_type_governed=False,
        manufacturer_code_governed=True,
        brand_display_governed=True,
        naming_profile_governed=True,
        variant_facts_governed=True,
    )
    assert oem_only.confidence != "high"
    assert "product_type_not_fk_verified" in oem_only.reason_codes

    ungoverned_brand = build_product_name_v1(
        **base,
        product_type_governed=True,
        manufacturer_code_governed=True,
        brand_display_governed=False,
        naming_profile_governed=True,
        variant_facts_governed=True,
    )
    assert ungoverned_brand.confidence != "high"
    assert "brand_display_not_governed" in ungoverned_brand.reason_codes

    ungoverned_facts = build_product_name_v1(
        **base,
        product_type_governed=True,
        manufacturer_code_governed=True,
        brand_display_governed=True,
        naming_profile_governed=True,
        variant_facts_governed=False,
    )
    assert ungoverned_facts.confidence != "high"
    assert "variant_facts_not_governed" in ungoverned_facts.reason_codes

    generic = build_product_name_v1(
        product_type="محصول صنعتی",
        brand="INSIZE | اینسایز",
        manufacturer_code="X-1",
        naming_profile="generic.v1",
        product_type_governed=True,
        manufacturer_code_governed=True,
        brand_display_governed=True,
        naming_profile_governed=True,
        variant_facts_governed=True,
    )
    assert generic.confidence != "high"
    assert "naming_profile_not_governed" in generic.reason_codes


def test_heuristic_candidates_never_imply_governed():
    cands = extract_manufacturer_code_candidates(
        name="کولیس دیجیتال اینسایز کد 1108-150",
        sku="1108-150",
        specs={"model": "1108-150"},
    )
    assert cands
    code = cands[0][0]
    assert manufacturer_code_is_governed(
        manufacturer_code=code, manufacturer_code_governed=False
    ) is False
    # Even with a candidate string present, default build stays below HIGH.
    result = build_product_name_v1(
        product_type="کولیس دیجیتال",
        brand="INSIZE | اینسایز",
        manufacturer_code=code,
        facts={"range_min_mm": 0, "range_max_mm": 150},
        naming_profile="metrology.caliper.v1",
        product_type_governed=True,
        # manufacturer_code_governed defaults False
    )
    assert result.confidence != "high"
    assert result.confidence == "medium"


def test_manufacturer_code_round_trip_preservation_in_titles():
    codes = [
        "1108-150",
        "500-196-30",
        "DCMT11T312-XM YBC203",
        "WNMG080408-PM",
        "K11-315MM",
        "GM-4E-D8.0",
        "PTTNL2525M22",
        "SNMG120408-PM / YBC252",
        "X--Y--Z",
    ]
    for code in codes:
        result = build_product_name_v1(
            product_type="اینسرت تراشکاری",
            brand="ZCC.CT",
            manufacturer_code=code,
            naming_profile="cutting.turning_insert.v1",
            preferred_brand_form="ZCC.CT",
            product_type_governed=True,
            manufacturer_code_governed=True,
            brand_display_governed=True,
            naming_profile_governed=True,
        )
        assert result.name is not None
        assert code in result.name
        assert result.name.count(code) == 1


def test_resolve_naming_profile_v1_and_brand_registry_governance():
    code, status = resolve_naming_profile_v1("PROVISIONAL_METROLOGY_CALIPER")
    assert code == "metrology.caliper.v1"
    assert status == PROFILE_GOVERNED
    code2, status2 = resolve_naming_profile_v1("UNKNOWN_PT")
    assert code2 == "generic.v1"
    assert status2 == PROFILE_MISSING
    assert brand_display_is_governed({"status": "NEEDS_GOVERNANCE"}) is False
    assert brand_display_is_governed({"status": "GOVERNED"}) is True
