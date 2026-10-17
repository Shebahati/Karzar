"""TX-OWNER-001 product-level semantic review (read-only proposals, no APPLY)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalog_target.taxonomy_phase1b_baseline import (
    TARGET_DOMAINS,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    is_live_product,
    is_tx_owner_scope_category,
    normalize_taxonomy_text,
    tx_owner_scope_product_ids,
    write_csv,
)

PRIMARY_DISPOSITIONS = frozenset(
    {
        "CATALOG_EXIT_CANDIDATE",
        "INDUSTRIAL_EXCEPTION_CANDIDATE",
        "NEEDS_MORE_EVIDENCE",
        "SEMANTIC_CONFLICT",
        "OWNER_DECISION_REQUIRED",
    }
)

EVIDENCE_STRENGTHS = frozenset({"HIGH", "MEDIUM", "LOW"})
CONFIDENCE_LEVELS = frozenset({"HIGH", "MEDIUM", "LOW"})

DOMAIN_BY_CODE = {d["code"]: d["en"] for d in TARGET_DOMAINS}

# Engineering-inference markers (product title + path); not OEM-backed unless noted.
CUTTING_MARKERS = re.compile(
    r"cnc|بلیدکات|bladekat|شیارزن|کفتراش|کف\s*بردار|تیغ\s|تیغچه|اینسرت|insert|"
    r"فرز\s|فرزکاری|end\s*mill|groov|turning|milling|carbide|کاربید|HSS|"
    r"اور\s*فرز|face\s*mill|trigon|wiper|boring|drill\s*bit|مته",
    re.I,
)
WOODWORKING_MARKERS = re.compile(
    r"چوب|نجار|wood|planer|رنده\s*چوب|رنده\s*نجار|تیغه\s*رنده|تیشه|مغار|"
    r"براده\s*شکن.*رنده|کبوتری|لیسه\s*چوب|JN3\d{2}",
    re.I,
)
HAND_WORKSHOP_MARKERS = re.compile(
    r"انبر|آچار|چکش|پیچ.?گوشتی|شابر|پلیسه|کلمپ|گیره|سوهان|قداره|"
    r"سنبه|پانچ|درآر|نشان|مغار|تیشه|بادپاش|تفنگ\s*باد|بکس\s*بادی|"
    r"سوکت|آلن\s*بکس|دریل\s*شارژ|اره\s*موئی|کمان\s*اره|دسته\s*پلیسه|"
    r"قرقره\s*سنگ|صاف\s*کن|hand\s*tool|pliers|wrench|hammer|chisel",
    re.I,
)
TOOLHOLDING_MARKERS = re.compile(
    r"کولت|collet|chuck|ابزارگیر|هولدر|holder|آداپتور\s*ابزار|mandrel",
    re.I,
)
WORKHOLDING_MARKERS = re.compile(
    r"گیره\s*سنگ|vise|jaw|fixture|بست\s*صنعتی|جک\s*ماشین|machine\s*jack",
    re.I,
)
METROLOGY_MARKERS = re.compile(
    r"کولیس|caliper|میکرومتر|micrometer|گage|gauge|ساعت\s*اندازه",
    re.I,
)
MACHINE_EQUIP_MARKERS = re.compile(
    r"موتور\s*صنعتی|spindle\s*motor|پمپ\s*صنعتی|compressor",
    re.I,
)
THREAD_REPAIR_MARKERS = re.compile(
    r"هلیکویل|helicoil|thread\s*repair|قلاویز\s*رمی|فنر\s*هلیکویل",
    re.I,
)
FLUID_MARKERS = re.compile(
    r"روغن\s*صنعتی|cutting\s*fluid|coolant|گریس\s*صنعتی",
    re.I,
)
GENERIC_MARKERS = re.compile(
    r"^(ست|ابزار|محصول|مدل)\s|^\s*مایتی\s*سون|^[A-Z]{2,}\d{3,}$",
    re.I,
)


@dataclass(frozen=True)
class ReviewRow:
    product_id: int
    sku: str
    manufacturer_code: str
    current_name: str
    brand: str
    category_id: int
    category_path: str
    is_active: str
    is_available: str
    is_priced: str
    image_present: str
    storefront_visible: str
    sellable: str
    product_type_code: str
    product_type_name: str
    actual_product_meaning: str
    engineering_function: str
    industrial_application: str
    evidence_source: str
    evidence_strength: str
    scope_assessment: str
    proposed_disposition: str
    proposed_industrial_domain_code: str
    proposed_industrial_domain_name: str
    decision_rationale: str
    confidence: str
    owner_review_required: str
    review_status: str


def load_cohort_products(
    product_census_path: Path,
    *,
    category_census_path: Path | None = None,
) -> list[dict[str, str]]:
    with product_census_path.open(encoding="utf-8", newline="") as handle:
        products = list(csv.DictReader(handle))
    cohort = [
        row
        for row in products
        if is_live_product(row)
        and str(row.get("category_id") or "").strip()
        and is_tx_owner_scope_category(int(row["category_id"]))
    ]
    expected_ids = tx_owner_scope_product_ids(products)
    found_ids = {int(r["product_id"]) for r in cohort}
    if found_ids != expected_ids:
        raise RuntimeError(
            f"cohort_id_mismatch expected={len(expected_ids)} found={len(found_ids)}"
        )
    if len(found_ids) != 262:
        raise RuntimeError(f"cohort_count_expected_262 got={len(found_ids)}")
    by_cat: dict[int, int] = {}
    for row in cohort:
        cid = int(row["category_id"])
        by_cat[cid] = by_cat.get(cid, 0) + 1
    if by_cat.get(158) != 196 or by_cat.get(160) != 66:
        raise RuntimeError(f"cohort_category_counts_invalid by_cat={by_cat}")
    if category_census_path and category_census_path.is_file():
        with category_census_path.open(encoding="utf-8", newline="") as handle:
            cats = {int(r["category_id"]): r for r in csv.DictReader(handle)}
        for cid in (157, 159):
            if int(cats[cid]["direct_product_count"]) != 0:
                raise RuntimeError(f"parent_category_expected_zero_direct cid={cid}")
        if int(cats[158]["direct_product_count"]) != 196:
            raise RuntimeError("category_158_direct_count_mismatch")
        if int(cats[160]["direct_product_count"]) != 66:
            raise RuntimeError("category_160_direct_count_mismatch")
    return sorted(cohort, key=lambda r: int(r["product_id"]))


def _priced_flag(row: dict[str, str]) -> str:
    try:
        return "true" if float(row.get("base_price") or 0) > 0 else "false"
    except ValueError:
        return "false"


def _classify(row: dict[str, str]) -> ReviewRow:
    pid = int(row["product_id"])
    cid = int(row["category_id"])
    name = row.get("product_name", "")
    path = row.get("category_full_path", "")
    pt_code = row.get("product_type_code", "") or ""
    # Product meaning must not be inferred solely from TX-OWNER category labels (path).
    title_blob = f"{name} {pt_code}"
    norm = normalize_taxonomy_text(title_blob)

    evidence_source = (
        "PRESERVED_PRODUCTION_CENSUS_2026-10-15;"
        "fields=product_name,category_full_path,commerce_flags,product_type"
    )
    wood = bool(WOODWORKING_MARKERS.search(title_blob))
    hand = bool(HAND_WORKSHOP_MARKERS.search(title_blob))
    cutting = bool(CUTTING_MARKERS.search(title_blob))
    toolhold = bool(TOOLHOLDING_MARKERS.search(title_blob))
    workhold = bool(WORKHOLDING_MARKERS.search(title_blob))
    metro = bool(METROLOGY_MARKERS.search(title_blob))
    machine = bool(MACHINE_EQUIP_MARKERS.search(title_blob))
    thread = bool(THREAD_REPAIR_MARKERS.search(title_blob))
    fluid = bool(FLUID_MARKERS.search(title_blob))
    generic = bool(GENERIC_MARKERS.search(name.strip()))
    category_is_wood_labeled = "ابزار چوب" in path or "چوبی" in path

    domain_code = ""
    domain_name = ""
    disposition = "NEEDS_MORE_EVIDENCE"
    meaning = "نام و مسیر دسته‌بندی کافی برای تعیین قطعی کاربرد صنعتی نیست."
    function = "نامشخص"
    application = ""
    strength = "LOW"
    confidence = "LOW"
    rationale = ""
    owner_required = "YES"
    scope = "TX_OWNER_001_IN_SCOPE"

    if thread:
        disposition = "INDUSTRIAL_EXCEPTION_CANDIDATE"
        domain_code = "KZ.DOM.THREAD_REPAIR"
        domain_name = DOMAIN_BY_CODE[domain_code]
        meaning = "ابزار/قطعه مرتبط با تعمیر رزوه (استنباط از عنوان)."
        function = "Thread repair / insert installation"
        strength = "MEDIUM"
        confidence = "MEDIUM"
        rationale = (
            "عنوان نشان‌دهنده کارکرد تعمیر رزوه است؛ خارج از دامنه Workshop/Hand "
            "ولی نیازمند تأیید صریح Owner برای هرگونه rehome."
        )
    elif metro:
        disposition = "INDUSTRIAL_EXCEPTION_CANDIDATE"
        domain_code = "KZ.DOM.METROLOGY"
        domain_name = DOMAIN_BY_CODE[domain_code]
        meaning = "ابزار اندازه‌گیری/کنترل (استنباط از عنوان)."
        function = "Dimensional inspection"
        strength = "MEDIUM"
        confidence = "MEDIUM"
        rationale = "کارکرد اندازه‌گیری صنعتی؛ پیشنهاد استثناء صنعتی بدون مجوز rehome."
    elif toolhold:
        disposition = "OWNER_DECISION_REQUIRED"
        domain_code = "KZ.DOM.TOOLHOLDING"
        domain_name = DOMAIN_BY_CODE[domain_code]
        meaning = "احتمال ابزارگیر/نگهدارنده ابزار برشی."
        function = "Toolholding interface"
        strength = "MEDIUM"
        confidence = "LOW"
        rationale = (
            "نشانه‌های ابزارگیر در عنوان دیده می‌شود؛ "
            "با توجه به قرارگیری در دسته Workshop باید Owner تفکیک کند."
        )
    elif workhold and not hand:
        disposition = "OWNER_DECISION_REQUIRED"
        domain_code = "KZ.DOM.WORKHOLDING"
        domain_name = DOMAIN_BY_CODE[domain_code]
        meaning = "احتمال بست/گیره صنعتی یا جک ماشین‌کاری."
        function = "Workholding / machine support"
        strength = "MEDIUM"
        confidence = "LOW"
        rationale = "مرز Workholding و ابزار دستی کارگاهی مبهم است؛ تصمیم Owner لازم."
    elif machine:
        disposition = "INDUSTRIAL_EXCEPTION_CANDIDATE"
        domain_code = "KZ.DOM.MACHINES"
        domain_name = DOMAIN_BY_CODE[domain_code]
        meaning = "تجهیز/ماشین صنعتی (استنباط از عنوان)."
        function = "Industrial equipment"
        strength = "LOW"
        confidence = "LOW"
        rationale = "نیاز به تأیید Owner؛ استثناء صنعتی پیشنهادی بدون rehome خودکار."
    elif fluid:
        disposition = "INDUSTRIAL_EXCEPTION_CANDIDATE"
        domain_code = "KZ.DOM.FLUIDS"
        domain_name = DOMAIN_BY_CODE[domain_code]
        meaning = "سیال فلزکاری/روانکار صنعتی."
        function = "Metalworking fluid"
        strength = "MEDIUM"
        confidence = "MEDIUM"
        rationale = "خارج از دامنه Workshop Tools؛ استثناء پیشنهادی."
    elif re.search(r"پلیسه|deburr", title_blob, re.I):
        disposition = "CATALOG_EXIT_CANDIDATE"
        meaning = "ابزار/تیغ پلیسه‌گیری دستی (کارگاهی)."
        function = "Manual deburring"
        strength = "HIGH"
        confidence = "HIGH"
        rationale = "پلیسه‌گیری دستی در دامنه Workshop/Hand Tools است؛ پیشنهاد CATALOG_EXIT."
    elif cutting and not wood:
        disposition = "INDUSTRIAL_EXCEPTION_CANDIDATE"
        domain_code = "KZ.DOM.CUTTING"
        domain_name = DOMAIN_BY_CODE[domain_code]
        meaning = "قطعه برشی/اینسرت یا ابزار برشی قابل‌نصب ماشین (CNC/فلزکاری)."
        function = "Indexable cutting / metal removal"
        application = "CNC turning/milling/grooving (inferred)"
        strength = "MEDIUM" if "cnc" in norm or "بلیدکات" in norm else "LOW"
        confidence = "MEDIUM" if strength == "MEDIUM" else "LOW"
        if cid == 160 and category_is_wood_labeled:
            disposition = "SEMANTIC_CONFLICT"
            domain_code = "KZ.DOM.CUTTING"
            domain_name = DOMAIN_BY_CODE[domain_code]
            rationale = (
                "عنوان کارکرد برشی فلزکاری/CNC را نشان می‌دهد اما مسیر دسته "
                "«ابزار آلات چوبی» است؛ پیشنهاد: استثناء صنعتی Cutting Tools "
                "پس از تأیید Owner — بدون rehome خودکار."
            )
            owner_required = "YES"
        else:
            rationale = (
                "کارکرد برشی صنعتی در عنوان دیده می‌شود؛ "
                "پیشنهاد INDUSTRIAL_EXCEPTION (Cutting Tools) — نه مجوز rehome."
            )
    elif wood:
        disposition = "CATALOG_EXIT_CANDIDATE"
        meaning = "ابزار نجاری/چوب‌کاری یا مصرفی مرتبط با کارگاه نجاری."
        function = "Woodworking hand or bench tool"
        application = "Wood shop / carpentry (inferred)"
        strength = "HIGH" if wood else "MEDIUM"
        confidence = "HIGH" if wood else "MEDIUM"
        rationale = (
            "مطابق TX-OWNER-001 محصول در دامنه Workshop/Woodworking است؛ "
            "پیشنهاد خروج از کاتالوگ (بدون اجرای APPLY)."
        )
        owner_required = "YES"
    elif hand or cid == 158:
        disposition = "CATALOG_EXIT_CANDIDATE"
        meaning = "ابزار دستی عمومی یا کارگاهی (انبر، آچار، سنبه، بادی و مشابه)."
        function = "Manual workshop operation"
        strength = "HIGH" if hand else "MEDIUM"
        confidence = "HIGH" if hand else "MEDIUM"
        rationale = (
            "دسته 158 «ابزار دستی عمومی» و عنوان محصول با دامنه رد‌شده "
            "Workshop & Hand Tools هم‌خوان است؛ پیشنهاد CATALOG_EXIT."
        )
        owner_required = "YES"
    elif generic:
        disposition = "NEEDS_MORE_EVIDENCE"
        meaning = "عنوان بازاری/کد مدل بدون شرح فنی در شواهد حفظ‌شده."
        function = "Undocumented from census fields"
        strength = "LOW"
        confidence = "LOW"
        rationale = (
            "صرفاً از سرشمار SKU/برند نمی‌توان کارکرد مهندسی را اثبات کرد؛ "
            "نیاز به توضیحات فنی یا مستند OEM."
        )
    else:
        disposition = "OWNER_DECISION_REQUIRED"
        meaning = "کارکرد از عنوان قابل حدس است اما مرز governance روشن نیست."
        function = "Ambiguous workshop vs industrial accessory"
        strength = "LOW"
        confidence = "LOW"
        rationale = "نیاز به بررسی Owner با شواهد تکمیلی."

    if disposition not in PRIMARY_DISPOSITIONS:
        raise RuntimeError(f"invalid_disposition {disposition}")

    return ReviewRow(
        product_id=pid,
        sku=row.get("sku", ""),
        manufacturer_code=row.get("manufacturer_code", ""),
        current_name=name,
        brand=row.get("brand", ""),
        category_id=cid,
        category_path=path,
        is_active=row.get("is_active", ""),
        is_available=row.get("is_available", ""),
        is_priced=_priced_flag(row),
        image_present=row.get("image_present", ""),
        storefront_visible=row.get("storefront_visible", ""),
        sellable=row.get("sellable", ""),
        product_type_code=row.get("product_type_code", ""),
        product_type_name=row.get("product_type_name", ""),
        actual_product_meaning=meaning,
        engineering_function=function,
        industrial_application=application,
        evidence_source=evidence_source,
        evidence_strength=strength,
        scope_assessment=scope,
        proposed_disposition=disposition,
        proposed_industrial_domain_code=domain_code,
        proposed_industrial_domain_name=domain_name,
        decision_rationale=rationale,
        confidence=confidence,
        owner_review_required=owner_required,
        review_status="PROPOSED",
    )


def review_row_to_dict(row: ReviewRow) -> dict[str, str]:
    return {
        "product_id": str(row.product_id),
        "sku": row.sku,
        "manufacturer_code": row.manufacturer_code,
        "current_name": row.current_name,
        "brand": row.brand,
        "current_category_id": str(row.category_id),
        "current_category_path": row.category_path,
        "is_active": row.is_active,
        "is_available": row.is_available,
        "is_priced": row.is_priced,
        "image_present": row.image_present,
        "storefront_visible": row.storefront_visible,
        "sellable": row.sellable,
        "product_type_code": row.product_type_code,
        "product_type_name": row.product_type_name,
        "actual_product_meaning": row.actual_product_meaning,
        "engineering_function": row.engineering_function,
        "industrial_application": row.industrial_application,
        "evidence_source": row.evidence_source,
        "evidence_strength": row.evidence_strength,
        "scope_assessment": row.scope_assessment,
        "proposed_disposition": row.proposed_disposition,
        "proposed_industrial_domain_code": row.proposed_industrial_domain_code,
        "proposed_industrial_domain_name": row.proposed_industrial_domain_name,
        "decision_rationale": row.decision_rationale,
        "confidence": row.confidence,
        "owner_review_required": row.owner_review_required,
        "review_status": row.review_status,
    }


REVIEW_FIELDS = list(review_row_to_dict(ReviewRow(
    product_id=0,
    sku="",
    manufacturer_code="",
    current_name="",
    brand="",
    category_id=0,
    category_path="",
    is_active="",
    is_available="",
    is_priced="",
    image_present="",
    storefront_visible="",
    sellable="",
    product_type_code="",
    product_type_name="",
    actual_product_meaning="",
    engineering_function="",
    industrial_application="",
    evidence_source="",
    evidence_strength="",
    scope_assessment="",
    proposed_disposition="NEEDS_MORE_EVIDENCE",
    proposed_industrial_domain_code="",
    proposed_industrial_domain_name="",
    decision_rationale="",
    confidence="LOW",
    owner_review_required="YES",
    review_status="PROPOSED",
)).keys())


def build_product_reviews(cohort: list[dict[str, str]]) -> list[dict[str, str]]:
    return [review_row_to_dict(_classify(row)) for row in cohort]


def disposition_counts(reviews: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {d: 0 for d in PRIMARY_DISPOSITIONS}
    for row in reviews:
        disp = row["proposed_disposition"]
        if disp not in counts:
            raise RuntimeError(f"unexpected_disposition {disp}")
        counts[disp] += 1
    return counts


def validate_primary_partition(reviews: list[dict[str, str]]) -> None:
    if len(reviews) != 262:
        raise RuntimeError(f"review_row_count {len(reviews)}")
    ids = [int(r["product_id"]) for r in reviews]
    if len(set(ids)) != 262:
        raise RuntimeError("duplicate_product_ids_in_review")
    counts = disposition_counts(reviews)
    if sum(counts.values()) != 262:
        raise RuntimeError("disposition_sum_mismatch")
