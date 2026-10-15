"""Phase 1B read-only taxonomy baseline — pure transforms (no production I/O)."""

from __future__ import annotations

import csv
import hashlib
import re
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

HELICOIL_MARKERS: tuple[str, ...] = (
    "هلی کویل",
    "helicoil",
    "Helicoil",
)

SPECIAL_NUMERIC_IDS: tuple[int, ...] = (33, 34, 165, 166, 168, 186, 187, 188)

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


def is_storefront_visible_product(row: dict[str, str]) -> bool:
    return is_active_product(row) and is_imaged_flag(row.get("has_valid_image", ""))


def is_sellable_product(row: dict[str, str]) -> bool:
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


def owner_scope_candidate(name: str, full_path: str) -> bool:
    text = f"{name} {full_path}"
    return any(p.search(text) for p in OWNER_SCOPE_NAME_PATTERNS)


def catchall_candidate(name: str, full_path: str) -> bool:
    text = f"{name} {full_path}"
    return any(p.search(text) for p in CATCHALL_PATTERNS)


def mixed_semantic_parent(name: str, full_path: str) -> bool:
    return any(m in name or m in full_path for m in MIXED_SEMANTIC_PARENT_MARKERS)


def helicoil_related(name: str, full_path: str) -> bool:
    text = f"{name} {full_path}".lower()
    return any(m.lower() in text for m in HELICOIL_MARKERS)


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


def historical_drift(current: dict[str, Any], global_counts: dict[str, int]) -> dict[str, Any]:
    anchor = PHASE0B_ANCHOR
    return {
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
        owner_flag = owner_scope_candidate(row.name, row.full_path)
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


def scan_numeric_category_dependencies(repo_root: Path) -> list[dict[str, str]]:
    patterns = [
        re.compile(r"category_id\s*[=:]\s*(\d+)", re.I),
        re.compile(r"categories\.id\s*=\s*(\d+)", re.I),
        re.compile(r"parent_id\s*[=:]\s*(\d+).*#.*categor", re.I),
        re.compile(r"FORMER_HUB_ID\s*=\s*(\d+)", re.I),
        re.compile(r"DEPTH2[^0-9]*(\d{2,3})"),
    ]
    skip_dirs = {".git", "node_modules", ".venv", "audit", "work", ".cursor"}
    rows: list[dict[str, str]] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix not in {".py", ".ts", ".tsx", ".js", ".json", ".md", ".csv", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in patterns:
                for match in pattern.finditer(line):
                    cid = match.group(1)
                    rows.append(
                        {
                            "file": str(path.relative_to(repo_root)),
                            "line": str(lineno),
                            "numeric_id": cid,
                            "context": line.strip()[:240],
                            "runtime_relevance": "REVIEW_REQUIRED",
                            "risk": "MEDIUM",
                            "required_future_kz_cat": "",
                        }
                    )
    return rows


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
        if is_imaged_flag(row.get("has_valid_image", "")):
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
