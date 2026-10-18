"""Curated semantics and commerce-tree parent rules for Phase 1B Route B."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from catalog_target.taxonomy_phase1b_baseline import (
    REMOVED_L1_HELICOIL_ROOT_IDS,
    TARGET_DOMAINS,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    CategoryRow,
)

DATA = Path(__file__).resolve().parent / "data/route_b_category_semantics.csv"

DOMAIN_BY_CODE = {d["code"]: d for d in TARGET_DOMAINS}

# Buyer-facing commerce L1 hubs (not 1:1 with scientific domains; max depth budget).
BUYER_COMMERCE_L1: dict[str, tuple[str, str, str]] = {
    "KZ.CAT.BUYER_TOOLHOLDING": ("KZ.DOM.TOOLHOLDING", "Toolholding", "ابزارگیر"),
    "KZ.CAT.BUYER_CUTTING_TOOLS": ("KZ.DOM.CUTTING", "Cutting Tools", "ابزار برشی"),
    "KZ.CAT.BUYER_THREAD_REPAIR": ("KZ.DOM.THREAD_REPAIR", "Thread Repair & Inserts", "تعمیر رزوه"),
    "KZ.CAT.BUYER_METROLOGY": ("KZ.DOM.METROLOGY", "Metrology & Inspection", "اندازه‌گیری و بازرسی"),
    "KZ.CAT.BUYER_WORKHOLDING": ("KZ.DOM.WORKHOLDING", "Workholding & Fixturing", "گیرش و فیکسچر"),
    "KZ.CAT.BUYER_MACHINES": ("KZ.DOM.MACHINES", "Industrial Machines", "ماشین‌آلات صنعتی"),
    "KZ.CAT.BUYER_FLUIDS": ("KZ.DOM.FLUIDS", "Metalworking Fluids", "سیالات فلزکاری"),
}

METROLOGY_FAMILY = {
    56: "KZ.CAT.METROLOGY_FAMILY_PRECISION",
    81: "KZ.CAT.METROLOGY_FAMILY_CNC",
    87: "KZ.CAT.METROLOGY_FAMILY_LABORATORY",
}

METROLOGY_FAMILY_META: dict[str, tuple[str, str, str]] = {
    "KZ.CAT.METROLOGY_FAMILY_PRECISION": (
        "KZ.DOM.METROLOGY",
        "Precision Measuring Tools",
        "اندازه‌گیری دقیق",
    ),
    "KZ.CAT.METROLOGY_FAMILY_CNC": (
        "KZ.DOM.METROLOGY",
        "CNC Machine Metrology",
        "اندازه‌گیری فرز CNC",
    ),
    "KZ.CAT.METROLOGY_FAMILY_LABORATORY": (
        "KZ.DOM.METROLOGY",
        "Laboratory Metrology",
        "اندازه‌گیری آزمایشگاهی",
    ),
}

HISTORICAL_DEPRECATED_CODES: dict[int, str] = {
    186: "KZ.CAT.DEPRECATED_HELICOIL_L1_SPRING_INSERT_ROOT",
    187: "KZ.CAT.DEPRECATED_HELICOIL_L1_TAP_RANGE_ROOT",
    188: "KZ.CAT.DEPRECATED_HELICOIL_L1_INSTALL_TOOL_ROOT",
}

OWNER_DEPRECATED_CODES: dict[int, str] = {
    157: "KZ.CAT.DEPRECATED_TX_OWNER_HAND_TOOLS_157",
    158: "KZ.CAT.DEPRECATED_TX_OWNER_HAND_TOOLS_158",
    159: "KZ.CAT.DEPRECATED_TX_OWNER_WOODWORKING_159",
    160: "KZ.CAT.DEPRECATED_TX_OWNER_WOODWORKING_160",
}

TRANSITIONAL_HUB_CODES: dict[int, str] = {
    154: "KZ.CAT.TRANSITIONAL_INDUSTRIAL_ACCESSORIES_HUB_154",
    155: "KZ.CAT.TRANSITIONAL_LUBRICANTS_FACET_155",
    163: "KZ.CAT.TRANSITIONAL_MACHINE_ACCESSORIES_HUB_163",
}

MIXED_STAGING_CODES: dict[int, str] = {
    116: "KZ.CAT.STAGING_LATHE_CHUCK_MIXED_116",
    117: "KZ.CAT.STAGING_FOUR_JAW_MIXED_117",
    118: "KZ.CAT.STAGING_TWO_JAW_MIXED_118",
    164: "KZ.CAT.STAGING_TAPPING_MACHINE_ACCESSORIES_164",
}


@dataclass(frozen=True)
class CategorySemantic:
    category_id: int
    name_en: str
    kz_cat_code: str
    publish_in_commerce_tree: bool
    design_note: str


@lru_cache(maxsize=1)
def load_category_semantics() -> dict[int, CategorySemantic]:
    out: dict[int, CategorySemantic] = {}
    with DATA.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cid = int(row["category_id"])
            out[cid] = CategorySemantic(
                category_id=cid,
                name_en=row["name_en"].strip(),
                kz_cat_code=(row["kz_cat_code"] or "").strip(),
                publish_in_commerce_tree=row["publish_in_commerce_tree"].strip().upper() == "Y",
                design_note=row.get("design_note", "").strip(),
            )
    return out


def l1_ancestor(category_id: int, parent_of: dict[int, int | None]) -> int:
    cur = category_id
    seen: set[int] = set()
    while parent_of.get(cur) is not None:
        if cur in seen:
            break
        seen.add(cur)
        cur = parent_of[cur]  # type: ignore[assignment]
    return cur


def scientific_domain_for(row: CategoryRow, parent_of: dict[int, int | None]) -> str | None:
    if row.category_id == 55:
        return "KZ.DOM.THREAD_REPAIR"
    if row.category_id in {155, 156}:
        return "KZ.DOM.FLUIDS"
    if row.category_id in TX_OWNER_SCOPE_CATEGORY_IDS:
        return None
    l1 = l1_ancestor(row.category_id, parent_of)
    if l1 == 154:
        if row.category_id == 156:
            return "KZ.DOM.FLUIDS"
        return None
    mapping = {
        1: "KZ.DOM.TOOLHOLDING",
        2: "KZ.DOM.CUTTING",
        4: "KZ.DOM.CUTTING",
        5: "KZ.DOM.CUTTING",
        6: "KZ.DOM.CUTTING",
        8: "KZ.DOM.WORKHOLDING",
        9: "KZ.DOM.MACHINES",
        56: "KZ.DOM.METROLOGY",
        81: "KZ.DOM.METROLOGY",
        87: "KZ.DOM.METROLOGY",
        165: "KZ.DOM.CUTTING",
    }
    return mapping.get(l1)


def buyer_l1_for_domain(domain: str | None) -> str | None:
    if domain is None:
        return None
    for code, (dom, _en, _fa) in BUYER_COMMERCE_L1.items():
        if dom == domain:
            return code
    return None


def commerce_parent_for(
    row: CategoryRow,
    parent_of: dict[int, int | None],
    semantics: dict[int, CategorySemantic],
) -> str:
    """Return parent commerce code for publishable nodes (depth derived from graph)."""
    sem = semantics[row.category_id]
    if not sem.publish_in_commerce_tree or not sem.kz_cat_code:
        return ""
    domain = scientific_domain_for(row, parent_of)
    buyer_l1 = buyer_l1_for_domain(domain)
    if not buyer_l1:
        return ""

    l1 = l1_ancestor(row.category_id, parent_of)
    pid = row.parent_id

    if row.category_id == 55:
        return buyer_l1

    if row.category_id == 156:
        return buyer_l1

    # Metrology publishable leaves always hang under the L2 family hub (never legacy L1).
    if l1 in METROLOGY_FAMILY and row.category_id != l1:
        family = METROLOGY_FAMILY[l1]
        if pid is not None and semantics.get(pid) and semantics[pid].publish_in_commerce_tree:
            return semantics[pid].kz_cat_code
        return family

    if row.category_id in {12, 18, 21, 24, 28, 98, 114, 161}:
        return buyer_l1

    if pid is not None and semantics.get(pid) and semantics[pid].publish_in_commerce_tree:
        return semantics[pid].kz_cat_code

    if row.depth == 2:
        return buyer_l1

    return buyer_l1


def assign_commerce_depths(
    rows: list[dict[str, str]],
    *,
    code_key: str = "commerce_category_code",
    parent_key: str = "parent_commerce_code",
    depth_key: str = "commerce_depth",
) -> dict[str, int]:
    """Set depth from parent graph: roots=1, child=parent+1. Returns code→depth map."""
    parents = {r[code_key]: (r.get(parent_key) or "").strip() for r in rows}
    depth_cache: dict[str, int] = {}

    def depth_of(code: str) -> int:
        if code in depth_cache:
            return depth_cache[code]
        parent = parents.get(code, "")
        d = 1 if not parent else depth_of(parent) + 1
        depth_cache[code] = d
        return d

    for row in rows:
        d = depth_of(row[code_key])
        row[depth_key] = str(d)
    return depth_cache


def registry_code_for_category(row: CategoryRow) -> tuple[str, str]:
    """Return (code, identity_status) for manifest/registry — includes deprecated/staging."""
    cid = row.category_id
    if cid in HISTORICAL_DEPRECATED_CODES:
        return HISTORICAL_DEPRECATED_CODES[cid], "DEPRECATED_HISTORICAL"
    if cid in OWNER_DEPRECATED_CODES:
        return OWNER_DEPRECATED_CODES[cid], "DEPRECATED_OWNER_SCOPE"
    if cid in TRANSITIONAL_HUB_CODES:
        return TRANSITIONAL_HUB_CODES[cid], "TRANSITIONAL_EXCLUDED"
    if cid in MIXED_STAGING_CODES:
        return MIXED_STAGING_CODES[cid], "STAGING_EVIDENCE_GATED"
    sem = load_category_semantics()[cid]
    if sem.publish_in_commerce_tree and sem.kz_cat_code:
        return sem.kz_cat_code, "PUBLISHED_PROPOSED"
    if cid in REMOVED_L1_HELICOIL_ROOT_IDS:
        return HISTORICAL_DEPRECATED_CODES[cid], "DEPRECATED_HISTORICAL"
    return "", "LEGACY_HUB_RETIRED"
