#!/usr/bin/env python3
"""Build page-aware INSIZE OEM occurrence + identity registries and canonical policy CSV."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.product_naming_phase2d_oem_extract import (  # noqa: E402
    IDENTITY_REGISTRY_CSV,
    OCCURRENCES_CSV,
    build_all_occurrences,
    build_identity_registry,
    write_identity_registry_csv,
    write_occurrences_csv,
)
from app.domain.product_naming_phase2d_oem_policy import normalize_oem_heading  # noqa: E402

POLICY_CSV = (
    ROOT
    / "docs"
    / "architecture"
    / "specs"
    / "product-naming-v1"
    / "OEM_CANONICAL_IDENTITY_POLICY.csv"
)

# EXACT OEM heading → governed Product Type + canonical Persian title (+ optional qualifier).
_HEADING_POLICY_ROWS: list[tuple[str, str, str, str, str, str]] = [
    # heading, product_type, canonical_title_fa, required_qualifier, semantic_scope, basis
    ("ADJUSTABLE SQUARE", "ENGINEERS_SQUARE", "گونیا مهندسی", "قابل تنظیم", "subtype_qualifier", "oem_adjustable_square"),
    ("COATING THICKNESS GAUGES (STANDARD TYPE)", "COATING_THICKNESS_GAUGE", "ضخامت‌سنج پوشش", "", "base_identity", "oem_coating_thickness"),
    ("COMPACT DIAL INDICATORS", "DIAL_INDICATOR", "ساعت اندازه‌گیری", "", "broader_title_acceptable", "oem_dial_indicator_family"),
    ("CONTACT/NON-CONTACT TACHOMETER", "TACHOMETER", "دورسنج", "", "base_identity", "oem_tachometer"),
    ("COUNTING SCALES", "DIGITAL_SCALE", "ترازوی دیجیتال", "", "base_identity", "oem_counting_scale"),
    ("CYLINDER SQUARES", "ENGINEERS_SQUARE", "گونیا مهندسی", "سیلندری", "subtype_qualifier", "oem_cylinder_square"),
    ("DEPTH MICROMETERS", "DEPTH_MICROMETER", "میکرومتر عمق‌سنج", "", "base_identity", "oem_depth_micrometer"),
    ("DIAL DEPTH GAUGES", "DEPTH_GAUGE", "عمق‌سنج", "", "base_identity", "oem_dial_depth_gauge"),
    ("DIAL INDICATORS (BASIC TYPE)", "DIAL_INDICATOR", "ساعت اندازه‌گیری", "", "broader_title_acceptable", "oem_dial_indicator"),
    ("DIAL INDICATORS (LONG STROKE)", "DIAL_INDICATOR", "ساعت اندازه‌گیری", "", "broader_title_acceptable", "oem_dial_indicator_long_stroke"),
    ("DIAL PROTRACTOR", "PROTRACTOR", "زاویه‌سنج", "", "base_identity", "oem_dial_protractor"),
    ("DIAL TEST INDICATORS", "TEST_INDICATOR", "ساعت اهرمی", "", "base_identity", "oem_test_indicator"),
    ("DIGITAL CALIPERS WITH INTERCHANGEABLE POINTS", "INTERCHANGEABLE_POINT_CALIPER", "کولیس نوک‌دار تعویض‌شونده", "", "base_identity", "oem_interchangeable_point_caliper"),
    ("DIGITAL CHAMFER GAUGES", "CHAMFER_GAUGE", "گیج پخ", "", "base_identity", "oem_chamfer_gauge"),
    ("DIGITAL DEPTH GAUGES", "DEPTH_GAUGE", "عمق‌سنج", "", "base_identity", "oem_digital_depth_gauge"),
    ("DIGITAL EXTERNAL CALIPER GAUGES", "INDICATING_CALIPER", "پرگار نشان‌گر", "", "base_identity", "oem_indicating_caliper"),
    ("DIGITAL GEAR TOOTH CALIPERS", "GEAR_TOOTH_CALIPER", "کولیس ضخامت دندانه", "", "base_identity", "oem_gear_tooth_caliper"),
    ("DIGITAL HEIGHT GAUGES", "HEIGHT_GAUGE", "ارتفاع‌سنج", "", "base_identity", "oem_height_gauge"),
    ("DIGITAL HEIGHT GAUGES WITH DRIVING WHEEL", "HEIGHT_GAUGE", "ارتفاع‌سنج", "", "broader_title_acceptable", "oem_height_gauge_driving_wheel"),
    ("DIGITAL HOOK CALIPERS", "HOOK_CALIPER", "کولیس قلاب‌دار", "", "base_identity", "oem_hook_caliper"),
    ("DIGITAL INSIDE GROOVE CALIPERS", "INTERNAL_GROOVE_CALIPER", "کولیس شیار داخلی", "", "base_identity", "oem_internal_groove_caliper"),
    ("DIGITAL INSIDE MICROMETERS (ECONOMIC TYPE)", "INSIDE_MICROMETER", "میکرومتر داخل‌سنج", "", "broader_title_acceptable", "oem_inside_micrometer_digital"),
    ("DIGITAL INTERNAL CALIPER GAUGES", "INDICATING_CALIPER", "پرگار نشان‌گر", "", "base_identity", "oem_internal_caliper_gauge"),
    ("DIGITAL INTERNAL CALIPER GAUGES (ECONOMIC TYPE)", "INDICATING_CALIPER", "پرگار نشان‌گر", "", "broader_title_acceptable", "oem_internal_caliper_economic"),
    ("DIGITAL LEVEL AND SLOPE METER", "DIGITAL_LEVEL", "تراز دیجیتال", "", "base_identity", "oem_digital_level_slope"),
    ("DIGITAL LEVELS AND SLOPE METERS", "DIGITAL_LEVEL", "تراز دیجیتال", "", "base_identity", "oem_digital_level_slope"),
    ("DIGITAL MOISTURE METER", "MOISTURE_METER", "رطوبت‌سنج", "", "base_identity", "oem_moisture_meter"),
    ("DIGITAL PROTRACTOR", "PROTRACTOR", "زاویه‌سنج", "", "base_identity", "oem_digital_protractor"),
    ("DIGITAL PROTRACTORS", "PROTRACTOR", "زاویه‌سنج", "", "base_identity", "oem_digital_protractors"),
    ("DIGITAL SMALL POINT CALIPERS", "POINT_CALIPER", "کولیس نوک‌تیز", "", "base_identity", "oem_point_caliper"),
    ("DIGITAL ZERO SETTER", "ZERO_SETTER", "صفرکن محور Z", "", "base_identity", "oem_digital_zero_setter"),
    ("ELECTRONIC ZERO SETTER", "ZERO_SETTER", "صفرکن محور Z", "", "broader_title_acceptable", "oem_electronic_zero_setter"),
    ("DOUBLE FACE DIAL INDICATOR", "DIAL_INDICATOR", "ساعت اندازه‌گیری", "", "broader_title_acceptable", "oem_double_face_dial"),
    ("ELECTRONIC CRANE SCALES", "DIGITAL_SCALE", "ترازوی دیجیتال", "", "broader_title_acceptable", "oem_crane_scale"),
    ("ELECTRONIC POCKET SCALE (ECONOMIC TYPE)", "DIGITAL_SCALE", "ترازوی دیجیتال", "", "broader_title_acceptable", "oem_pocket_scale"),
    ("EXTERNAL DIAL CALIPER GAUGES", "INDICATING_CALIPER", "پرگار نشان‌گر", "", "base_identity", "oem_external_dial_caliper"),
    ("FEELER GAUGE ROLLS", "FEELER_GAUGE", "فیلر نواری", "", "base_identity", "oem_feeler_roll"),
    ("FEELER GAUGES", "FEELER_GAUGE_SET", "ست فیلر", "", "base_identity", "oem_feeler_set"),
    ("FILLET WELDING GAUGE", "FILLET_WELD_GAUGE", "گیج جوش نبشی", "", "base_identity", "oem_fillet_weld_gauge"),
    ("FILLET WELDING GAUGES", "FILLET_WELD_GAUGE", "گیج جوش نبشی", "", "base_identity", "oem_fillet_weld_gauges"),
    ("GEAR TOOTH PITCH GAUGES", "GEAR_TOOTH_PITCH_GAUGE", "شابلون گام چرخ‌دنده", "", "base_identity", "oem_gear_pitch"),
    ("GRANITE SQUARES", "ENGINEERS_SQUARE", "گونیا مهندسی", "گرانیتی", "subtype_qualifier", "oem_granite_square"),
    ("INCH DIAL INDICATORS", "DIAL_INDICATOR", "ساعت اندازه‌گیری", "", "broader_title_acceptable", "oem_inch_dial"),
    ("INCH FEELER GAUGE", "FEELER_GAUGE", "فیلر نواری", "", "base_identity", "oem_inch_feeler"),
    ("INSIDE MICROMETERS (ECONOMIC TYPE)", "INSIDE_MICROMETER", "میکرومتر داخل‌سنج", "", "broader_title_acceptable", "oem_inside_micrometer"),
    ("INTERNAL DIAL CALIPER GAUGES", "INDICATING_CALIPER", "پرگار نشان‌گر", "", "base_identity", "oem_internal_dial_caliper"),
    ("INTERNAL DIAL CALIPER GAUGES WITH INTERCHANGEABLE POINTS", "INDICATING_CALIPER", "پرگار نشان‌گر", "", "broader_title_acceptable", "oem_internal_dial_interchangeable"),
    ("LASER DISTANCE METERS", "LASER_DISTANCE_METER", "متر لیزری", "", "base_identity", "oem_laser_distance"),
    ("LONG FEELER GAUGES", "FEELER_GAUGE_SET", "ست فیلر", "", "broader_title_acceptable", "oem_long_feeler_set"),
    ("MACHINIST SQUARES (ECONOMIC TYPE)", "ENGINEERS_SQUARE", "گونیا مهندسی", "", "base_identity", "oem_machinist_square"),
    ("MACHINIST SQUARES WITH WIDE BASE (ECONOMIC TYPE)", "ENGINEERS_SQUARE", "گونیا مهندسی", "پایه پهن", "subtype_qualifier", "oem_wide_base_square"),
    ("MEASURING WHEEL", "MEASURING_WHEEL", "چرخ‌متر", "", "base_identity", "oem_measuring_wheel"),
    ("MEASURING WHEEL (BASIC TYPE)", "MEASURING_WHEEL", "چرخ‌متر", "", "base_identity", "oem_measuring_wheel_basic"),
    ("MINI DIGITAL DEPTH GAUGES WITH ROUND BAR", "DEPTH_GAUGE", "عمق‌سنج", "", "broader_title_acceptable", "oem_mini_depth_gauge"),
    ("MULTIMETER SELECTION TABLE", "DIGITAL_MULTIMETER", "مولتی‌متر دیجیتال", "", "broader_title_acceptable", "oem_multimeter_table"),
    ("OUTSIDE MICROMETERS", "OUTSIDE_MICROMETER", "میکرومتر خارج‌سنج", "", "base_identity", "oem_outside_micrometer"),
    ("OUTSIDE MICROMETERS WITH COUNTER", "OUTSIDE_MICROMETER", "میکرومتر خارج‌سنج", "", "broader_title_acceptable", "oem_outside_micrometer_counter"),
    ("OUTSIDE MICROMETERS WITH EXTENSION ANVIL COLLAR", "OUTSIDE_MICROMETER", "میکرومتر خارج‌سنج", "", "broader_title_acceptable", "oem_outside_micrometer_extension"),
    ("PIPE WELDING GAUGE", "WELDING_GAUGE", "گیج جوش", "", "base_identity", "oem_pipe_weld_gauge"),
    ("PITCH GAUGES", "THREAD_PITCH_GAUGE", "شابلون گام رزوه", "", "base_identity", "oem_pitch_gauge"),
    ("PLASTIC ANGLE SQUARE", "ANGLE_GAUGE", "گیج زاویه", "", "base_identity", "oem_plastic_angle_square"),
    ("PORTABLE CRANE SCALE", "DIGITAL_SCALE", "ترازوی دیجیتال", "", "broader_title_acceptable", "oem_portable_crane_scale"),
    ("PROTRACTOR (ECONOMIC TYPE)", "PROTRACTOR", "زاویه‌سنج", "", "base_identity", "oem_protractor_economic"),
    ("STEEL RULERS", "STEEL_RULE", "خط‌کش فلزی", "", "base_identity", "oem_steel_rule"),
    ("TEMPERATURE AND HUMIDITY METER (ECONOMIC TYPE)", "MOISTURE_METER", "دما و رطوبت‌سنج", "", "multi_function", "oem_temp_humidity_meter"),
    ("TUBULAR INSIDE MICROMETERS", "INSIDE_MICROMETER", "میکرومتر داخل‌سنج", "", "broader_title_acceptable", "oem_tubular_inside_micrometer"),
    ("UNIVERSAL PROTRACTOR", "PROTRACTOR", "زاویه‌سنج", "", "broader_title_acceptable", "oem_universal_protractor"),
    ("VERNIER DEPTH GAUGES (STANDARD TYPE)", "DEPTH_GAUGE", "عمق‌سنج", "", "base_identity", "oem_vernier_depth"),
    ("VERNIER HEIGHT GAUGES", "HEIGHT_GAUGE", "ارتفاع‌سنج", "", "base_identity", "oem_vernier_height"),
    ("WATERPROOF DIGITAL PROTRACTOR (HEAVY DUTY)", "PROTRACTOR", "زاویه‌سنج", "", "broader_title_acceptable", "oem_waterproof_protractor"),
    ("WEIGHING SCALES (ECONOMIC TYPE)", "DIGITAL_SCALE", "ترازوی دیجیتال", "", "base_identity", "oem_weighing_scale"),
    ("WELDING GAUGE", "WELDING_GAUGE", "گیج جوش", "", "base_identity", "oem_welding_gauge"),
    ("WELDING GAUGES", "WELDING_GAUGE", "گیج جوش", "", "base_identity", "oem_welding_gauges"),
    ("WET FILM GAUGES", "WET_FILM_THICKNESS_GAUGE", "گیج ضخامت فیلم خیس", "", "base_identity", "oem_wet_film_gauge"),
]


def write_policy_csv(path: Path) -> None:
    fields = [
        "OEM_heading_or_family",
        "match_type",
        "allowed_product_type_code",
        "canonical_title_fa",
        "required_title_qualifier",
        "semantic_scope",
        "policy_status",
        "policy_basis",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for heading, pt, title, qual, scope, basis in _HEADING_POLICY_ROWS:
            w.writerow(
                {
                    "OEM_heading_or_family": normalize_oem_heading(heading),
                    "match_type": "EXACT",
                    "allowed_product_type_code": pt,
                    "canonical_title_fa": title,
                    "required_title_qualifier": qual,
                    "semantic_scope": scope,
                    "policy_status": "APPROVED",
                    "policy_basis": basis,
                }
            )


def main() -> None:
    write_policy_csv(POLICY_CSV)
    print(f"wrote policy {POLICY_CSV}")
    occurrences = build_all_occurrences()
    write_occurrences_csv(OCCURRENCES_CSV, occurrences)
    print(f"wrote {len(occurrences)} occurrences → {OCCURRENCES_CSV}")
    registry = build_identity_registry(occurrences)
    write_identity_registry_csv(IDENTITY_REGISTRY_CSV, registry)
    exact = sum(1 for r in registry.values() if r.evidence_status == "EXACT_PRODUCT_IDENTITY")
    print(f"wrote {len(registry)} identities ({exact} exact) → {IDENTITY_REGISTRY_CSV}")


if __name__ == "__main__":
    main()
