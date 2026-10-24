"""Deterministic AST supplier-file → Karzar leaf category mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Leaf category IDs (depth 2–3, selectable) from production taxonomy snapshot.
CAT = {
    "tap_machine": 122,
    "tap_machine_accessory": 164,
    "magnet_drill_machine": 123,
    "core_drill_machine": 125,
    "tool_sharpener_machine": 121,
    "multi_spindle": 162,
    "chuck_3jaw": 116,
    "pull_stud": 17,
    "collet_bt": 13,
    "morse_cap": 120,
    "vise_precision": 101,
    "turntable": 102,
    "tycop": 103,
    "endmill_carbide_flat": 35,
    "endmill_carbide_ball": 36,
    "endmill_carbide_tip": 37,
    "endmill_hss": 38,
    "drill_indexable": 41,
    "drill_core": 46,
    "drill_conical": 44,
    "annular_cutter": 47,
    "tap_machine_spiral": 48,
    "tap_machine_straight": 49,
    "tap_hand": 50,
    "insert_turning": 166,
    "insert_milling": 168,
    "insert_threading": 172,
    "insert_parting": 170,
    "oil_industrial": 156,
    "gauge_gap": 78,
    "caliper": 57,
    "micrometer": 58,
    "indicator": 59,
    "depth_gauge": 62,
}


@dataclass(frozen=True)
class CategoryDecision:
    category_id: int | None
    family_label: str
    mapping_rule: str
    hold_reason: str = ""


# Longest / most specific source filename needles first.
_FILE_RULES: list[tuple[str, int, str, str]] = [
    ("قلاویز ET", CAT["tap_machine_straight"], "قلاویز ماشینی", "file:et_tap"),
    ("قلاویز ماشینی چینی", CAT["tap_machine_straight"], "قلاویز ماشینی صاف", "file:chinese_machine_tap"),
    ("قلاویز زن اتومات", CAT["tap_machine"], "دستگاه قلاویز زن", "file:tap_machine_auto"),
    ("قلاویززن برقی", CAT["tap_machine"], "دستگاه قلاویز زن", "file:tap_machine_electric"),
    ("قلاویززن بادی", CAT["tap_machine"], "دستگاه قلاویز زن", "file:tap_machine_pneumatic"),
    ("قلاویزگیر", CAT["tap_machine_accessory"], "لوازم جانبی قلاویز زن", "file:tap_wrench"),
    ("لیست قیمت دریل مگنت", CAT["magnet_drill_machine"], "دستگاه دریل مگنت", "file:magnet_drill"),
    ("لیست قیمت کردریل", CAT["annular_cutter"], "برقو", "file:annular_cutter"),
    ("لیست قیمت گردبر دریل مگنت", CAT["annular_cutter"], "برقو", "file:magnet_annular"),
    ("لیست قیمت  فرز انگشتی", CAT["endmill_carbide_flat"], "انگشتی", "file:endmill"),
    ("لیست قیمت  مته برگی", CAT["drill_indexable"], "مته کارباید", "file:indexable_drill"),
    ("لیست مته مرغک و مته خزینه", CAT["drill_core"], "مته مرغک", "file:core_drill"),
    ("مته ته کونیک", CAT["drill_conical"], "مته پشت کونیک HSS", "file:conical_drill"),
    ("مته یوتکس", CAT["drill_indexable"], "مته کارباید", "file:utex_drill"),
    ("لیست قیمت ابزار تیز کن", CAT["tool_sharpener_machine"], "دستگاه ابزار تیزکن", "file:sharpener"),
    ("مولتی اسپیندل", CAT["multi_spindle"], "مولتی اسپیندل", "file:multi_spindle"),
    ("پول استادگیر", CAT["pull_stud"], "PULL STUD – پول استاد", "file:pull_stud"),
    ("کلت و فشنگی", CAT["collet_bt"], "کولت BT و فشنگی و آچار", "file:collet"),
    ("کلاهک و دنباله", CAT["morse_cap"], "کلاهک تبدیل مورس", "file:morse_cap"),
    ("گیره مارک", CAT["vise_precision"], "گیره دقیق", "file:mark_vise"),
    ("تایکوپ و صفحه گردان", CAT["tycop"], "تایکوپ", "file:tycop"),
    ("صفحه گردان", CAT["turntable"], "صفحه گردان", "file:turntable"),
    ("روغن", CAT["oil_industrial"], "روغن صنعتی", "file:oil"),
    ("گردبر کیگو", CAT["annular_cutter"], "برقو", "file:keego_annular"),
    ("لیست چام پاور", CAT["insert_turning"], "اینسرت تراش CNC", "file:chumpower_default"),
]


_DASQUA_KEYWORDS: list[tuple[tuple[str, ...], int, str]] = [
    (("کولیس", "caliper"), CAT["caliper"], "انواع کولیس"),
    (("میکرومتر", "micrometer"), CAT["micrometer"], "انواع میکرومتر"),
    (("ساعت", "indicator"), CAT["indicator"], "ساعت اندیکاتور"),
    (("عمق", "depth"), CAT["depth_gauge"], "عمق سنج"),
    (("گپ", "gap"), CAT["gauge_gap"], "گپ سنج"),
]


_CHUMPOWER_CODE_HINTS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"(?i)^CNMG|^WNMG|^TNMG|^DCMT|^CCMT"), CAT["insert_turning"], "اینسرت تراش CNC"),
    (re.compile(r"(?i)^APMT|^XOMX|^SEKT|^XDGX|^R390"), CAT["insert_milling"], "اینسرت فرز CNC"),
    (re.compile(r"(?i)16ER|22ER|thread"), CAT["insert_threading"], "اینسرت رزوه‌زنی"),
    (re.compile(r"(?i)^SPMT|^N123"), CAT["insert_parting"], "اینسرت شیار و برش"),
]


def _dasqua_from_text(text: str) -> CategoryDecision | None:
    blob = (text or "").lower()
    for needles, cat_id, family in _DASQUA_KEYWORDS:
        if any(n.lower() in blob for n in needles):
            return CategoryDecision(cat_id, family, "dasqua:keyword")
    return None


def _chumpower_from_code(code: str) -> CategoryDecision | None:
    for pattern, cat_id, family in _CHUMPOWER_CODE_HINTS:
        if pattern.search(code):
            return CategoryDecision(cat_id, family, f"chumpower:code:{pattern.pattern}")
    return None


def _endmill_variant(code: str, nearby: str) -> tuple[int, str]:
    blob = f"{code} {nearby}".upper()
    if re.search(r"HSS\s*CO|HSSCO|HSS-?CO", blob) or "HSS" in blob:
        return CAT["endmill_hss"], "انگشتی HSS"
    if "BALL" in blob or "گرد" in nearby:
        return CAT["endmill_carbide_ball"], "انگشتی سر گرد کارباید"
    if "TIP" in blob or "تیپ" in nearby:
        return CAT["endmill_carbide_tip"], "انگشتی تیپ کارباید"
    return CAT["endmill_carbide_flat"], "انگشتی سرتخت کارباید"


def _et_tap_variant(code: str, nearby: str) -> CategoryDecision | None:
    blob = f"{code} {nearby}".lower()
    if "مارپیچ" in blob or "spiral" in blob:
        return CategoryDecision(CAT["tap_machine_spiral"], "قلاویز ماشینی مارپیچ", "et:tap_spiral")
    if "صاف" in blob or "straight" in blob:
        return CategoryDecision(CAT["tap_machine_straight"], "قلاویز ماشینی صاف", "et:tap_straight")
    return CategoryDecision(None, "", "et:tap_variant_unresolved", "HOLD_ET_TAP_VARIANT")


def _chuck_decision(fname: str, nearby: str) -> CategoryDecision:
    blob = f"{fname} {nearby}".lower()
    if "تراش" in blob and "دریل" not in blob:
        return CategoryDecision(CAT["chuck_3jaw"], "سه نظام و لوازم جانبی", "chuck:lathe_3jaw")
    return CategoryDecision(None, "", "chuck:drill_vs_lathe_unresolved", "HOLD_DRILL_CHUCK_IDENTITY")


def classify_create_category(
    *,
    source_file: str,
    brand_hint: str,
    code: str,
    code_nearby: str,
    cat_meta: dict[int, dict[str, Any]],
) -> CategoryDecision:
    fname = source_file or ""

    if brand_hint == "CHUMPOWER":
        hit = _chumpower_from_code(code)
        if hit and _selectable(hit.category_id, cat_meta):
            return hit
        return CategoryDecision(None, "", "chumpower:unclassified_code", "HOLD_CATEGORY_MAPPING")

    if brand_hint == "DASQUA":
        hit = _dasqua_from_text(f"{code_nearby} {code}")
        if hit and _selectable(hit.category_id, cat_meta):
            return hit
        return CategoryDecision(None, "", "dasqua:missing_keyword", "HOLD_CATEGORY_MAPPING")

    if "سه نظام" in fname:
        decision = _chuck_decision(fname, code_nearby)
        if decision.category_id and _selectable(decision.category_id, cat_meta):
            return decision
        return decision

    if "قلاویز ET" in fname and brand_hint == "ET":
        et = _et_tap_variant(code, code_nearby)
        if et.category_id and _selectable(et.category_id, cat_meta):
            return et
        return et

    for needle, cat_id, family, rule in _FILE_RULES:
        if needle in fname:
            if "فرز انگشتی" in needle:
                cat_id, family = _endmill_variant(code, code_nearby)
            if brand_hint == "ET" and "قلاویز ET" not in fname:
                return CategoryDecision(
                    None, "", "et:wrong_source_file", "HOLD_BRAND_SOURCE_MISMATCH"
                )
            if _selectable(cat_id, cat_meta):
                return CategoryDecision(cat_id, family, rule)
            return CategoryDecision(None, family, rule, "category_not_selectable_leaf")

    return CategoryDecision(None, "", "unmapped_source_file", "HOLD_CATEGORY_MAPPING")


def _selectable(cat_id: int | None, cat_meta: dict[int, dict[str, Any]]) -> bool:
    if cat_id is None:
        return False
    meta = cat_meta.get(cat_id)
    return bool(meta and meta.get("selectable"))
