"""Phase 1B read-only taxonomy baseline — pure transforms (no production I/O)."""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Phase 0B anchor (2026-09-27) — comparison only, not expected truth.
PHASE0B_ANCHOR: dict[str, Any] = {
    "snapshot_date": "2026-09-27",
    "categories": 138,
    "l1": 15,
    "l2": 81,
    "l3": 42,
    "depth_gt_3": 0,
    "leaves": 114,
    "selectable": 111,
    "empty_categories": 38,
    "categoryless_live_products": 0,
    "live_products": 6536,
    "sellable": 716,
    "storefront_visible": 1368,
}

MAX_CATEGORY_DEPTH = 3
MIN_PRODUCT_CATEGORY_DEPTH = 2

PLACEHOLDER_ILIKE = (
    "placeholder",
    "woocommerce-placeholder",
    "no-image",
    "no_image",
    "noimage",
    "default-image",
    "default_image",
    "karzar-editorial",
    "/images/placeholders/",
)

TARGET_DOMAINS: list[dict[str, str]] = [
    {"code": "KZ.DOM.METROLOGY", "en": "Metrology & Inspection"},
    {"code": "KZ.DOM.CUTTING", "en": "Cutting Tools"},
    {"code": "KZ.DOM.TOOLHOLDING", "en": "Toolholding"},
    {"code": "KZ.DOM.WORKHOLDING", "en": "Workholding & Fixturing"},
    {"code": "KZ.DOM.MACHINES", "en": "Industrial Machines & Equipment"},
    {"code": "KZ.DOM.THREAD_REPAIR", "en": "Thread Repair & Thread Inserts"},
    {"code": "KZ.DOM.FLUIDS", "en": "Metalworking Fluids & Lubricants"},
]

# TX-OWNER-001 scope signals (flag only — no APPLY).
OWNER_SCOPE_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ابزار\s*دستی", re.I),
    re.compile(r"ابزار\s*چوب", re.I),
    re.compile(r"چوبی", re.I),
    re.compile(r"کارگاه", re.I),
    re.compile(r"hand\s*tool", re.I),
    re.compile(r"wood\s*work", re.I),
    re.compile(r"workshop", re.I),
)

CATCHALL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"عمومی"),
    re.compile(r"متفرقه"),
    re.compile(r"سایر"),
    re.compile(r"miscellaneous", re.I),
    re.compile(r"general\s+tool", re.I),
    re.compile(r"other\s+tool", re.I),
)

MIXED_SEMANTIC_PARENT_MARKERS: tuple[str, ...] = (
    "لوازم جانبی صنعتی",
    "لوازم جانبی",
)

# TX-OWNER-001 steward-frozen scope categories (Phase 1B flag only).
TX_OWNER_SCOPE_CATEGORY_IDS: frozenset[int] = frozenset({157, 158, 159, 160})

REMOVED_L1_HELICOIL_ROOT_IDS: frozenset[int] = frozenset({186, 187, 188})

WATCHLIST_NUMERIC_CATEGORY_IDS: frozenset[int] = frozenset({33, 34, 186, 187, 188})

PHASE0B_CATEGORY_CENSUS_REL = Path("audit/taxonomy-phase0b/03-production-category-census.csv")

SPECIAL_NUMERIC_IDS: tuple[int, ...] = (33, 34, 165, 166, 168, 186, 187, 188)

DEPENDENCY_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".cursor",
        ".venv",
        ".mypy_cache",
        ".ruff_cache",
        ".next",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        "work",
        "audit",
    }
)

CCT1_ALLOWED = frozenset(
    {
        "KEEP_AS_CATEGORY",
        "BETTER_AS_FACET",
        "BETTER_AS_PRODUCT_TYPE",
        "BETTER_AS_APPLICATION",
        "BETTER_AS_SYNONYM",
        "DEPRECATE_REMOVE",
        "NOT_ENOUGH_EVIDENCE",
    }
)


@dataclass
class CategoryRow:
    category_id: int
    name: str
    slug: str
    parent_id: int | None
    parent_name: str
    full_path: str
    depth: int
    is_leaf: bool
    is_selectable: bool
    child_count: int
    megamenu_hidden: bool
    megamenu_as_leaf: bool
    hesabfa_category_code: str
    spec_template_key: str
    direct_live: int = 0
    descendant_live: int = 0
    active: int = 0
    available: int = 0
    priced: int = 0
    imaged: int = 0
    visible: int = 0
    sellable: int = 0
    pt_assigned: int = 0
    pt_missing: int = 0


def normalize_taxonomy_text(raw: str) -> str:
    """Fold Persian/Arabic variants, ZWNJ/ZWJ, and whitespace for stable token matching."""
    text = unicodedata.normalize("NFKC", raw or "")
    for ch in ("\u200c", "\u200d", "\u200e", "\u200f", "\ufeff"):
        text = text.replace(ch, "")
    text = re.sub(r"\s+", "", text)
    return text.lower()


def helicoil_token_present(text: str) -> bool:
    norm = normalize_taxonomy_text(text)
    if "هلیکویل" in norm or "helicoil" in norm:
        return True
    if "wirethreadinsert" in norm.replace("_", ""):
        return True
    return False


def helicoil_semantic_class(name: str, full_path: str, product_type_code: str = "") -> str:
    """Distinguish thread-repair/helicoil kits from indexable cutting inserts (review cohort)."""
    blob = normalize_taxonomy_text(f"{name} {full_path} {product_type_code}")
    cutting_markers = (
        "اینسرت",
        "insert",
        "indexable",
        "cutter",
        "carbide",
        "فرز",
        "تراش",
    )
    repair_markers = (
        "کیت",
        "فنر",
        "spring",
        "repair",
        "قلاویز",
        "tap",
    )
    if any(m in blob for m in cutting_markers) and "هلیکویل" not in blob and "helicoil" not in blob:
        return "THREAD_MACHINING_INSERT_REVIEW"
    if any(m in blob for m in repair_markers) or helicoil_token_present(blob):
        return "THREAD_REPAIR_HELICOIL_REVIEW"
    return "UNCLASSIFIED_REVIEW"


def is_tx_owner_scope_category(category_id: int) -> bool:
    return category_id in TX_OWNER_SCOPE_CATEGORY_IDS


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256sums(audit_dir: Path, filenames: list[str]) -> None:
    lines: list[str] = []
    for name in sorted(filenames):
        path = audit_dir / name
        if path.is_file():
            lines.append(f"{sha256_file(path)}  {name}")
    (audit_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _truthy(raw: str) -> bool:
    return str(raw or "").strip().lower() in {"t", "true", "1", "yes"}


def _priced(raw: str) -> bool:
    s = (raw or "").strip()
    if not s:
        return False
    try:
        return float(s) > 0
    except ValueError:
        return False


def is_imaged_flag(raw: str) -> bool:
    return _truthy(raw)


def is_live_product(row: dict[str, str]) -> bool:
    return not (row.get("deleted_at") or "").strip()


def is_active_product(row: dict[str, str]) -> bool:
    return is_live_product(row) and _truthy(row.get("is_active", ""))


def is_available_product(row: dict[str, str]) -> bool:
    return is_live_product(row) and _truthy(row.get("is_available", ""))


def is_priced_product(row: dict[str, str]) -> bool:
    return is_live_product(row) and _priced(row.get("base_price", ""))


def product_census_required_columns() -> tuple[str, ...]:
    return (
        "product_id",
        "is_active",
        "is_available",
        "base_price",
        "image_present",
        "storefront_visible",
        "sellable",
        "product_type_id",
    )


def validate_product_census_export(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise RuntimeError("product_census_empty")
    missing = [c for c in product_census_required_columns() if c not in rows[0]]
    if missing:
        raise RuntimeError(f"product_census_missing_columns={','.join(missing)}")


def product_image_flag(row: dict[str, str]) -> str:
    if (row.get("image_present") or "").strip():
        return row["image_present"]
    return row.get("has_valid_image", "")


def is_storefront_visible_product(row: dict[str, str]) -> bool:
    if "storefront_visible" in row and (row.get("storefront_visible") or "").strip():
        return is_imaged_flag(row["storefront_visible"])
    return is_active_product(row) and is_imaged_flag(product_image_flag(row))


def is_sellable_product(row: dict[str, str]) -> bool:
    if "sellable" in row and (row.get("sellable") or "").strip():
        return is_imaged_flag(row["sellable"])
    return (
        is_storefront_visible_product(row)
        and is_available_product(row)
        and is_priced_product(row)
    )


def build_category_metadata(
    categories: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    by_id = {int(c["id"]): c for c in categories}
    child_count: dict[int, int] = defaultdict(int)
    for cat in categories:
        pid = cat.get("parent_id")
        if pid not in (None, ""):
            child_count[int(pid)] += 1

    meta: dict[int, dict[str, Any]] = {}
    for cat in categories:
        cid = int(cat["id"])
        chain: list[dict[str, Any]] = []
        current: dict[str, Any] | None = cat
        seen: set[int] = set()
        while current is not None:
            cur_id = int(current["id"])
            if cur_id in seen:
                break
            seen.add(cur_id)
            chain.append(current)
            parent_id = current.get("parent_id")
            if parent_id in (None, ""):
                break
            current = by_id.get(int(parent_id))
        depth = len(chain)
        is_leaf = child_count[cid] == 0
        breadcrumb = [node["name"] for node in reversed(chain)]
        meta[cid] = {
            "depth": depth,
            "is_leaf": is_leaf,
            "breadcrumb": breadcrumb,
            "full_path": " › ".join(breadcrumb),
            "parent_name": breadcrumb[-2] if len(breadcrumb) > 1 else "",
            "child_count": child_count[cid],
            "is_selectable": is_leaf
            and MIN_PRODUCT_CATEGORY_DEPTH <= depth <= MAX_CATEGORY_DEPTH,
            "cycle": len(seen) < len(chain),
        }
    return meta


def detect_orphans_and_cycles(
    categories: list[dict[str, Any]],
    meta: dict[int, dict[str, Any]],
) -> tuple[list[int], list[int]]:
    by_id = {int(c["id"]): c for c in categories}
    orphans: list[int] = []
    for cat in categories:
        pid = cat.get("parent_id")
        if pid in (None, ""):
            continue
        if int(pid) not in by_id:
            orphans.append(int(cat["id"]))
    cycles = [cid for cid, m in meta.items() if m.get("cycle")]
    return orphans, cycles


def duplicate_sibling_names(categories: list[dict[str, Any]]) -> list[dict[str, str]]:
    buckets: dict[tuple[str | int, str], list[int]] = defaultdict(list)
    for cat in categories:
        pid = cat.get("parent_id")
        key = (pid if pid not in (None, "") else "ROOT", str(cat.get("name") or ""))
        buckets[key].append(int(cat["id"]))
    out: list[dict[str, str]] = []
    for (parent, name), ids in buckets.items():
        if len(ids) > 1:
            out.append(
                {
                    "parent_id": str(parent),
                    "name": name,
                    "category_ids": "|".join(str(i) for i in sorted(ids)),
                }
            )
    return out


def duplicate_slugs(categories: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_slug: dict[str, list[int]] = defaultdict(list)
    for cat in categories:
        by_slug[str(cat.get("slug") or "")].append(int(cat["id"]))
    return [
        {"slug": slug, "category_ids": "|".join(str(i) for i in ids)}
        for slug, ids in by_slug.items()
        if slug and len(ids) > 1
    ]


def owner_scope_candidate(name: str, full_path: str, *, category_id: int | None = None) -> bool:
    if category_id is not None and is_tx_owner_scope_category(category_id):
        return True
    text = f"{name} {full_path}"
    return any(p.search(text) for p in OWNER_SCOPE_NAME_PATTERNS)


def catchall_candidate(name: str, full_path: str) -> bool:
    text = f"{name} {full_path}"
    return any(p.search(text) for p in CATCHALL_PATTERNS)


def mixed_semantic_parent(name: str, full_path: str) -> bool:
    return any(m in name or m in full_path for m in MIXED_SEMANTIC_PARENT_MARKERS)


def helicoil_related(name: str, full_path: str) -> bool:
    return helicoil_token_present(f"{name} {full_path}")


def facet_like_category(name: str) -> bool:
    """Heuristic: short property-ish labels (review cohort F)."""
    n = (name or "").strip()
    if len(n) <= 12 and any(
        token in n for token in ("قطر", "سایز", "اندازه", "طول", "گام", "درجه")
    ):
        return True
    return False


def aggregate_category_metrics(
    categories: list[dict[str, Any]],
    products: list[dict[str, str]],
    meta: dict[int, dict[str, Any]],
) -> tuple[list[CategoryRow], dict[str, Any]]:
    direct: dict[int, Counter[str]] = defaultdict(Counter)
    for row in products:
        if not is_live_product(row):
            continue
        cid_raw = row.get("category_id") or ""
        if not str(cid_raw).strip():
            continue
        cid = int(cid_raw)
        bucket = direct[cid]
        bucket["live"] += 1
        if is_active_product(row):
            bucket["active"] += 1
        if is_available_product(row):
            bucket["available"] += 1
        if is_priced_product(row):
            bucket["priced"] += 1
        if is_imaged_flag(row.get("has_valid_image", "")):
            bucket["imaged"] += 1
        if is_storefront_visible_product(row):
            bucket["visible"] += 1
        if is_sellable_product(row):
            bucket["sellable"] += 1
        if (row.get("product_type_id") or "").strip():
            bucket["pt_assigned"] += 1
        else:
            bucket["pt_missing"] += 1

    descendant: dict[int, int] = {int(c["id"]): 0 for c in categories}

    def _desc_sum(cid: int) -> int:
        total = direct[cid]["live"]
        for cat in categories:
            pid = cat.get("parent_id")
            if pid not in (None, "") and int(pid) == cid:
                total += _desc_sum(int(cat["id"]))
        return total

    for cat in categories:
        descendant[int(cat["id"])] = _desc_sum(int(cat["id"]))

    rows: list[CategoryRow] = []
    for cat in categories:
        cid = int(cat["id"])
        m = meta[cid]
        counts = direct[cid]
        rows.append(
            CategoryRow(
                category_id=cid,
                name=str(cat.get("name") or ""),
                slug=str(cat.get("slug") or ""),
                parent_id=int(cat["parent_id"]) if cat.get("parent_id") not in (None, "") else None,
                parent_name=str(m.get("parent_name") or ""),
                full_path=str(m.get("full_path") or ""),
                depth=int(m["depth"]),
                is_leaf=bool(m["is_leaf"]),
                is_selectable=bool(m["is_selectable"]),
                child_count=int(m.get("child_count") or 0),
                megamenu_hidden=_truthy(str(cat.get("megamenu_hidden", ""))),
                megamenu_as_leaf=_truthy(str(cat.get("megamenu_as_leaf", ""))),
                hesabfa_category_code=str(cat.get("hesabfa_category_code") or ""),
                spec_template_key=str(cat.get("spec_template_key") or ""),
                direct_live=counts["live"],
                descendant_live=descendant[cid],
                active=counts["active"],
                available=counts["available"],
                priced=counts["priced"],
                imaged=counts["imaged"],
                visible=counts["visible"],
                sellable=counts["sellable"],
                pt_assigned=counts["pt_assigned"],
                pt_missing=counts["pt_missing"],
            )
        )

    structure = summarize_structure(rows, meta, products)
    return rows, structure


def summarize_structure(
    rows: list[CategoryRow],
    meta: dict[int, dict[str, Any]],
    products: list[dict[str, str]],
) -> dict[str, Any]:
    depth_counts = Counter(r.depth for r in rows)
    selectable = sum(1 for r in rows if r.is_selectable)
    leaves = sum(1 for r in rows if r.is_leaf)
    empty = sum(1 for r in rows if r.descendant_live == 0)
    non_leaf_assignments = 0
    invalid_assignments = 0
    categoryless = 0
    for row in products:
        if not is_live_product(row):
            continue
        cid_raw = row.get("category_id") or ""
        if not str(cid_raw).strip():
            categoryless += 1
            continue
        cid = int(cid_raw)
        m = meta.get(cid)
        if m is None:
            invalid_assignments += 1
        elif not m.get("is_selectable"):
            non_leaf_assignments += 1

    return {
        "total_categories": len(rows),
        "l1": depth_counts.get(1, 0),
        "l2": depth_counts.get(2, 0),
        "l3": depth_counts.get(3, 0),
        "depth_gt_3": sum(c for d, c in depth_counts.items() if d > 3),
        "leaves": leaves,
        "selectable": selectable,
        "empty_categories": empty,
        "categoryless_live_products": categoryless,
        "non_leaf_product_assignments": non_leaf_assignments,
        "invalid_category_assignments": invalid_assignments,
    }


def load_phase0b_category_index(repo_root: Path) -> dict[int, dict[str, str]]:
    path = repo_root / PHASE0B_CATEGORY_CENSUS_REL
    if not path.is_file():
        return {}
    rows: dict[int, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cid = int(row["id"])
            rows[cid] = row
    return rows


def compare_category_ids_phase0b(
    *,
    repo_root: Path,
    current_category_ids: set[int],
) -> dict[str, Any]:
    phase0b = load_phase0b_category_index(repo_root)
    phase0b_ids = set(phase0b)
    removed_ids = sorted(phase0b_ids - current_category_ids)
    added_ids = sorted(current_category_ids - phase0b_ids)
    removed_detail: list[dict[str, Any]] = []
    for cid in removed_ids:
        row = phase0b[cid]
        removed_detail.append(
            {
                "category_id": cid,
                "name": row.get("name", ""),
                "slug": row.get("slug", ""),
                "depth": row.get("depth", ""),
                "is_leaf": row.get("is_leaf", ""),
                "is_selectable": row.get("is_selectable", ""),
                "direct_live_product_count": row.get("direct_live_product_count", ""),
                "descendant_live_product_count": row.get("descendant_live_product_count", ""),
                "breadcrumb": row.get("breadcrumb", ""),
            }
        )
    return {
        "phase0b_category_count": len(phase0b_ids),
        "current_category_count": len(current_category_ids),
        "removed_category_ids": removed_ids,
        "added_category_ids": added_ids,
        "removed_categories": removed_detail,
        "reconciliation": {
            "category_total_delta_explained_by_removals": len(removed_ids) - len(added_ids),
            "l1_delta_explained_by_removed_empty_roots": [
                cid for cid in removed_ids if str(phase0b.get(cid, {}).get("depth")) == "1"
            ],
            "product_deletion_inferred": False,
            "narrative": (
                "Category-count drift is explained by removal of empty/non-selectable L1 roots "
                "(186/187/188 Helicoil megamenu roots in Phase 0B). Live product count unchanged "
                "at census level; do not infer product deletion from category-tree shrinkage."
            ),
        },
    }


def historical_drift(
    current: dict[str, Any],
    global_counts: dict[str, int],
    *,
    id_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    anchor = PHASE0B_ANCHOR
    payload: dict[str, Any] = {
        "anchor_snapshot": anchor["snapshot_date"],
        "category_total_delta": current["total_categories"] - anchor["categories"],
        "l1_delta": current["l1"] - anchor["l1"],
        "l2_delta": current["l2"] - anchor["l2"],
        "l3_delta": current["l3"] - anchor["l3"],
        "leaves_delta": current["leaves"] - anchor["leaves"],
        "selectable_delta": current["selectable"] - anchor["selectable"],
        "empty_delta": current["empty_categories"] - anchor["empty_categories"],
        "categoryless_delta": current["categoryless_live_products"] - anchor["categoryless_live_products"],
        "live_products_delta": global_counts.get("live", 0) - anchor["live_products"],
        "sellable_delta": global_counts.get("sellable", 0) - anchor["sellable"],
        "visible_delta": global_counts.get("visible", 0) - anchor["storefront_visible"],
        "anchor": anchor,
        "current_structure": current,
        "current_global": global_counts,
    }
    if id_comparison:
        payload["category_id_comparison"] = id_comparison
    return payload


def audit_megamenu_references(
    *,
    megamenu_groups: list[dict[str, str]],
    live_category_ids: set[int],
    category_depth_by_id: dict[int, int],
    category_name_by_id: dict[int, str],
    phase0b_removed_ids: set[int],
) -> dict[str, Any]:
    missing_refs: list[dict[str, str]] = []
    non_l1_refs: list[dict[str, str]] = []
    membership: dict[int, list[str]] = defaultdict(list)
    empty_groups: list[dict[str, str]] = []
    historical_dangling: list[dict[str, str]] = []

    for group in megamenu_groups:
        slug = group.get("slug", "")
        roots_raw = group.get("root_category_ids", "") or ""
        root_ids = [int(x) for x in roots_raw.split("|") if x.strip().isdigit()]
        if not root_ids:
            empty_groups.append({"nav_group_slug": slug, "issue": "no_root_category_ids"})
        resolved = 0
        for cid in root_ids:
            membership[cid].append(slug)
            if cid not in live_category_ids:
                missing_refs.append(
                    {
                        "nav_group_slug": slug,
                        "missing_category_id": str(cid),
                        "phase0b_removed": "YES" if cid in phase0b_removed_ids else "NO",
                        "historical_name": category_name_by_id.get(cid, ""),
                    }
                )
                if cid in phase0b_removed_ids:
                    historical_dangling.append(
                        {
                            "nav_group_slug": slug,
                            "removed_category_id": str(cid),
                            "issue": "references_removed_l1_helicoil_root",
                        }
                    )
            else:
                resolved += 1
                depth = category_depth_by_id.get(cid)
                if depth is not None and depth != 1:
                    non_l1_refs.append(
                        {
                            "nav_group_slug": slug,
                            "category_id": str(cid),
                            "depth": str(depth),
                            "name": category_name_by_id.get(cid, ""),
                        }
                    )
        if root_ids and resolved == 0:
            empty_groups.append({"nav_group_slug": slug, "issue": "all_root_ids_missing"})

    duplicate_membership = [
        {"category_id": str(cid), "nav_groups": "|".join(sorted(groups))}
        for cid, groups in membership.items()
        if len(groups) > 1
    ]
    live_l1_ids = {cid for cid, depth in category_depth_by_id.items() if depth == 1}
    covered_l1 = {cid for cid in membership if cid in live_l1_ids}

    return {
        "missing_category_references": missing_refs,
        "duplicate_root_memberships": duplicate_membership,
        "non_l1_root_references": non_l1_refs,
        "empty_or_unresolved_groups": empty_groups,
        "historical_removed_category_references": historical_dangling,
        "live_l1_count": len(live_l1_ids),
        "megamenu_covered_l1_count": len(covered_l1),
        "megamenu_uncovered_l1_ids": sorted(live_l1_ids - covered_l1),
        "proposed_future_action": (
            "Owner/merchandising review: update megamenu_nav_groups.root_category_ids for "
            "helicoil group to reference live taxonomy (e.g. category 55 under قلاویز) or retire "
            "the group. Do not auto-redirect removed 186/187/188 slugs to unrelated hubs."
        ),
    }


def product_type_summary_for_category(
    products: list[dict[str, str]],
    category_id: int,
) -> str:
    codes: Counter[str] = Counter()
    for row in products:
        if not is_live_product(row):
            continue
        if int(row.get("category_id") or 0) != category_id:
            continue
        code = (row.get("product_type_code") or "").strip() or "(missing)"
        codes[code] += 1
    if not codes:
        return ""
    return "; ".join(f"{code}:{count}" for code, count in codes.most_common(8))


def build_working_manifest(
    category_rows: list[CategoryRow],
    products: list[dict[str, str]],
) -> list[dict[str, str]]:
    manifest: list[dict[str, str]] = []
    for row in category_rows:
        owner_flag = owner_scope_candidate(row.name, row.full_path, category_id=row.category_id)
        mixed = mixed_semantic_parent(row.name, row.full_path)
        catchall = catchall_candidate(row.name, row.full_path)
        notes: list[str] = []
        if owner_flag:
            notes.append("TX-OWNER-001 scope candidate (flag only; no catalog exit)")
        if mixed:
            notes.append("mixed-semantic parent; requires product-level decomposition")
        if catchall:
            notes.append("catch-all/generic label risk")
        if row.category_id in SPECIAL_NUMERIC_IDS:
            notes.append(f"special numeric id watchlist ({row.category_id})")
        manifest.append(
            {
                "current_category_id": str(row.category_id),
                "current_name": row.name,
                "current_slug": row.slug,
                "current_full_path": row.full_path,
                "current_depth": str(row.depth),
                "direct_product_count": str(row.direct_live),
                "active_product_count": str(row.active),
                "visible_product_count": str(row.visible),
                "sellable_product_count": str(row.sellable),
                "current_product_type_summary": product_type_summary_for_category(
                    products, row.category_id
                ),
                "cct1_disposition": "NOT_ENOUGH_EVIDENCE",
                "target_domain_code": "",
                "target_domain_name": "",
                "target_category_code": "",
                "target_category_name": "",
                "target_parent_code": "",
                "product_disposition": "UNREVIEWED",
                "owner_scope_decision": "YES" if owner_flag else "NO",
                "requires_product_level_decomposition": "YES" if mixed else "NO",
                "seo_redirect_required": "UNKNOWN",
                "proposed_redirect_target": "",
                "import_dependency_detected": "UNKNOWN",
                "confidence": "LOW",
                "evidence_class": "PRODUCTION_CENSUS_BASELINE",
                "decision_rationale": "",
                "review_status": "UNREVIEWED",
                "notes": " | ".join(notes),
            }
        )
    return manifest


def classify_dependency_source(rel_path: str) -> str:
    rel = rel_path.replace("\\", "/")
    if "/.next/" in rel or rel.startswith(".next/"):
        return "GENERATED_EXCLUDED"
    if rel.startswith("tests/") or "/tests/" in rel:
        return "TEST_FIXTURE"
    if "fixture" in rel.lower() or "mock" in rel.lower() or "conftest" in rel:
        return "MOCK_DEMO"
    if rel.startswith("docs/") or rel.startswith("audit/"):
        return "HISTORICAL_DOCUMENTATION"
    if rel.startswith("scripts/"):
        if any(token in rel for token in ("zcc", "azarsanat", "mitutoyo", "insize", "supplier", "import")):
            return "SUPPLIER_IMPORT"
        return "ACTIVE_SCRIPT"
    if rel.startswith("app/"):
        return "ACTIVE_PRODUCTION_SOURCE"
    if rel.startswith("frontend/"):
        return "FRONTEND_SOURCE"
    return "UNRESOLVED_AMBIGUOUS"


def scan_numeric_category_dependencies(
    repo_root: Path,
    *,
    live_category_names: dict[int, str] | None = None,
) -> dict[str, Any]:
    patterns = [
        re.compile(r"category_id\s*[=:]\s*(\d+)", re.I),
        re.compile(r"categories\.id\s*=\s*(\d+)", re.I),
        re.compile(r"FORMER_HUB_ID\s*=\s*(\d+)", re.I),
        re.compile(r"root_category_ids.*?(\d{2,3})"),
    ]
    raw_hits: list[dict[str, str]] = []
    excluded_generated = 0
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in DEPENDENCY_SKIP_DIR_NAMES for part in path.parts):
            if ".next" in path.parts:
                excluded_generated += 1
            continue
        rel = str(path.relative_to(repo_root))
        if "/.next/" in rel:
            excluded_generated += 1
            continue
        if path.suffix not in {".py", ".ts", ".tsx", ".js", ".json", ".md", ".csv", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        bucket = classify_dependency_source(rel)
        if bucket == "GENERATED_EXCLUDED":
            excluded_generated += 1
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in patterns:
                for match in pattern.finditer(line):
                    cid = match.group(1)
                    raw_hits.append(
                        {
                            "file": rel,
                            "line": str(lineno),
                            "numeric_id": cid,
                            "context": line.strip()[:240],
                            "source_class": bucket,
                        }
                    )

    deduped: dict[tuple[str, str, str], dict[str, str]] = {}
    for hit in raw_hits:
        key = (hit["file"], hit["numeric_id"], hit["context"][:80])
        deduped[key] = hit

    rows: list[dict[str, str]] = []
    watchlist_hits: list[dict[str, str]] = []
    for hit in deduped.values():
        cid_int = int(hit["numeric_id"]) if hit["numeric_id"].isdigit() else -1
        resolved = ""
        if live_category_names and cid_int in live_category_names:
            resolved = live_category_names[cid_int]
        risk = "LOW"
        runtime = hit["source_class"]
        if hit["source_class"] in {"ACTIVE_PRODUCTION_SOURCE", "SUPPLIER_IMPORT", "ACTIVE_SCRIPT"}:
            risk = "HIGH" if cid_int in WATCHLIST_NUMERIC_CATEGORY_IDS else "MEDIUM"
        elif hit["source_class"] in {"TEST_FIXTURE", "MOCK_DEMO"}:
            risk = "LOW"
        row = {
            **hit,
            "resolved_live_category": resolved,
            "runtime_relevance": runtime,
            "risk": risk,
            "required_future_kz_cat": "",
        }
        rows.append(row)
        if cid_int in WATCHLIST_NUMERIC_CATEGORY_IDS:
            watchlist_hits.append(row)

    by_class = Counter(r["source_class"] for r in rows)
    return {
        "raw_hit_count": len(raw_hits),
        "deduped_hit_count": len(rows),
        "excluded_generated_path_skips": excluded_generated,
        "hits_by_source_class": dict(by_class),
        "dependencies": sorted(rows, key=lambda r: (r["source_class"], r["file"], int(r["line"]))),
        "watchlist_ids": sorted(WATCHLIST_NUMERIC_CATEGORY_IDS),
        "watchlist_unresolved_hits": watchlist_hits,
    }


def build_helicoil_cohort_reports(
    category_rows: list[CategoryRow],
    products: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    category_hits: list[dict[str, str]] = []
    product_hits: list[dict[str, str]] = []
    for row in category_rows:
        if helicoil_related(row.name, row.full_path):
            category_hits.append(
                {
                    **category_row_to_census_dict(row),
                    "cohort": "HELICOIL_THREAD_REPAIR",
                    "semantic_class": helicoil_semantic_class(row.name, row.full_path),
                }
            )
    for prod in products:
        if not is_live_product(prod):
            continue
        blob = " ".join(
            [
                prod.get("product_name", ""),
                prod.get("category_name", ""),
                prod.get("category_full_path", ""),
                prod.get("product_type_code", ""),
            ]
        )
        if not helicoil_token_present(blob):
            continue
        product_hits.append(
            {
                "product_id": prod.get("product_id", ""),
                "sku": prod.get("sku", ""),
                "category_id": prod.get("category_id", ""),
                "category_full_path": prod.get("category_full_path", ""),
                "product_type_code": prod.get("product_type_code", ""),
                "semantic_class": helicoil_semantic_class(
                    prod.get("product_name", ""),
                    prod.get("category_full_path", ""),
                    prod.get("product_type_code", ""),
                ),
            }
        )
    return category_hits, product_hits


def tx_owner_scope_product_ids(products: list[dict[str, str]]) -> set[int]:
    ids: set[int] = set()
    for row in products:
        if not is_live_product(row):
            continue
        cid_raw = row.get("category_id") or ""
        if not str(cid_raw).strip():
            continue
        if is_tx_owner_scope_category(int(cid_raw)):
            ids.add(int(row["product_id"]))
    return ids


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def category_census_csv_fields() -> list[str]:
    return [
        "category_id",
        "name",
        "slug",
        "parent_id",
        "parent_name",
        "full_path",
        "depth",
        "is_leaf",
        "is_selectable",
        "child_count",
        "direct_product_count",
        "descendant_product_count",
        "active_count",
        "available_count",
        "priced_count",
        "imaged_count",
        "visible_count",
        "sellable_count",
        "product_type_assigned_count",
        "product_type_missing_count",
        "hesabfa_category_code",
        "spec_template_key",
        "megamenu_hidden",
        "megamenu_as_leaf",
    ]


def category_row_to_census_dict(row: CategoryRow) -> dict[str, str]:
    return {
        "category_id": str(row.category_id),
        "name": row.name,
        "slug": row.slug,
        "parent_id": str(row.parent_id or ""),
        "parent_name": row.parent_name,
        "full_path": row.full_path,
        "depth": str(row.depth),
        "is_leaf": str(row.is_leaf),
        "is_selectable": str(row.is_selectable),
        "child_count": str(row.child_count),
        "direct_product_count": str(row.direct_live),
        "descendant_product_count": str(row.descendant_live),
        "active_count": str(row.active),
        "available_count": str(row.available),
        "priced_count": str(row.priced),
        "imaged_count": str(row.imaged),
        "visible_count": str(row.visible),
        "sellable_count": str(row.sellable),
        "product_type_assigned_count": str(row.pt_assigned),
        "product_type_missing_count": str(row.pt_missing),
        "hesabfa_category_code": row.hesabfa_category_code,
        "spec_template_key": row.spec_template_key,
        "megamenu_hidden": str(row.megamenu_hidden),
        "megamenu_as_leaf": str(row.megamenu_as_leaf),
    }


def global_product_counts(products: list[dict[str, str]]) -> dict[str, int]:
    validate_product_census_export(products)
    counts = Counter()
    for row in products:
        if not is_live_product(row):
            counts["deleted"] += 1
            continue
        counts["live"] += 1
        if is_active_product(row):
            counts["active"] += 1
        if is_available_product(row):
            counts["available"] += 1
        if is_priced_product(row):
            counts["priced"] += 1
        if is_imaged_flag(product_image_flag(row)):
            counts["imaged"] += 1
        if is_storefront_visible_product(row):
            counts["visible"] += 1
        if is_sellable_product(row):
            counts["sellable"] += 1
        if (row.get("product_type_id") or "").strip():
            counts["pt_assigned"] += 1
        else:
            counts["pt_missing"] += 1
        if not (row.get("category_id") or "").strip():
            counts["categoryless"] += 1
    return dict(counts)


CANONICAL_PRESERVED_PRODUCT_METRICS: dict[str, int] = {
    "live": 6536,
    "active": 1585,
    "available": 3811,
    "priced": 4272,
    "imaged": 1464,
    "visible": 1368,
    "sellable": 720,
    "pt_assigned": 658,
    "pt_missing": 5878,
}


def load_json_lines_export(raw: str) -> list[dict[str, str]]:
    """Parse psql tab output with header into dict rows."""
    lines = [line for line in raw.splitlines() if line.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) != len(header):
            continue
        rows.append(dict(zip(header, parts, strict=False)))
    return rows
