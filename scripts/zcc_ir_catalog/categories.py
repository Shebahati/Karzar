"""Conservative zcc.ir → Karzar category mapping candidates. No category creates."""

from __future__ import annotations

from collections import Counter

from zcc_ir_catalog.models import CategoryMapRow, SourceProduct
from zcc_ir_catalog.normalize import fold_text

# Exact English path suffixes that are semantically unambiguous vs Karzar leaves.
# Anything that mixes grooving/parting, insert vs holder, or end-mill form stays REVIEW.
SAFE_PATH_RULES: tuple[tuple[tuple[str, ...], str, str, str], ...] = (
    (("turning", "turning-insert"), "33", "اینسرت › اینسرت تراش CNC", "turning inserts → CNC turning inserts"),
    (
        ("turning", "turning-tool-holder", "external-turning-holders"),
        "27",
        "ابزار اینسرتی › هولدر تراش CNC › رو تراش",
        "external turning holders → رو تراش",
    ),
    (
        ("turning", "turning-tool-holder", "internal-turning-holders"),
        "26",
        "ابزار اینسرتی › هولدر تراش CNC › داخل تراش",
        "internal turning holders → داخل تراش",
    ),
    (
        ("turning", "turning-tool-holder", "q-cut-holder"),
        "25",
        "ابزار اینسرتی › هولدر تراش CNC › برش(Q CUT)",
        "Q-cut holders → برش(Q CUT)",
    ),
    (
        ("drilling", "drill-bit", "insert-drill-bit"),
        "45",
        "مته › مته سی ان سی(U_Drill)",
        "insert drill bits → U-Drill",
    ),
    (
        ("milling", "milling-holders", "helder-floor-lathe"),
        "22",
        "ابزار اینسرتی › هولدر فرز CNC › کف تراش",
        "face-mill holders → کف تراش",
    ),
    (
        ("machines", "tool-sharpener"),
        "121",
        "دستگاه‌های صنعتی › دستگاه ابزار تیزکن",
        "tool sharpener machines → دستگاه ابزار تیزکن",
    ),
    (
        ("three-and-four-jaw-chuck", "three-jaw-chuck"),
        "116",
        "ابزار گیرشی › گیرشی تراش منوال و CNC › سه نظام و لوازم جانبی",
        "three-jaw chucks → سه نظام و لوازم جانبی",
    ),
    (
        ("three-and-four-jaw-chuck", "four-jaw-chuck"),
        "117",
        "ابزار گیرشی › گیرشی تراش منوال و CNC › چهار نظام و لوازم جانبی",
        "four-jaw chucks → چهار نظام و لوازم جانبی",
    ),
)

# Names that look similar but must stay REVIEW (machining distinctions).
REVIEW_PATH_MARKERS = (
    "cutting-and-grooving",
    "grooving",
    "parting",
    "diamond-milling",
    "insert-finger-mill",
    "carbide-end-mill",
    "four-blade",
    "pcd-pcbn",
    "milling-holders",
    "turning-tool-holder",
    "boring",
    "ream",
    "thread",
    "accessory",
    "accessories",
)


def _fold_name(value: str) -> str:
    return fold_text(value).casefold().replace(" ", "")


def _path_key(parts: list[str]) -> tuple[str, ...]:
    return tuple(p.casefold() for p in parts)


def _match_safe_rule(url_parts: list[str]) -> tuple[str, str, str] | None:
    key = _path_key(url_parts)
    best: tuple[str, str, str] | None = None
    best_len = 0
    for suffix, cat_id, cat_path, reason in SAFE_PATH_RULES:
        n = len(suffix)
        if n > best_len and len(key) >= n and key[-n:] == suffix:
            best = (cat_id, cat_path, reason)
            best_len = n
        elif n > best_len and len(key) >= n and key[:n] == suffix:
            best = (cat_id, cat_path, reason)
            best_len = n
        elif n > best_len and _contains_sequence(key, suffix):
            best = (cat_id, cat_path, reason)
            best_len = n
    return best


def _contains_sequence(haystack: tuple[str, ...], needle: tuple[str, ...]) -> bool:
    if not needle:
        return False
    n = len(needle)
    for i in range(0, len(haystack) - n + 1):
        if haystack[i : i + n] == needle:
            return True
    return False


def map_source_category(
    *,
    path_names: list[str],
    category_url: str | None,
    karzar_by_folded_name: dict[str, tuple[str, str]],
) -> tuple[str, str, str, str | None, str | None]:
    """Return status, confidence, reason, karzar_id, karzar_path."""
    url_parts: list[str] = []
    if category_url and "/product-category/" in category_url:
        after = category_url.split("/product-category/", 1)[1]
        url_parts = [p for p in after.strip("/").split("/") if p]

    leaf_name = path_names[-1] if path_names else ""
    if leaf_name:
        folded = _fold_name(leaf_name)
        exact = karzar_by_folded_name.get(folded)
        if exact:
            return "EXACT", "high", "folded source leaf name equals Karzar category name", exact[0], exact[1]

    joined_url = "/".join(p.casefold() for p in url_parts)
    if any(marker in joined_url for marker in REVIEW_PATH_MARKERS) and not _match_safe_rule(url_parts):
        return (
            "REVIEW",
            "low",
            "machining distinction is not unique enough for auto-map",
            None,
            None,
        )

    safe = _match_safe_rule(url_parts)
    if safe:
        cat_id, cat_path, reason = safe
        return "SAFE_RULE", "medium", reason, cat_id, cat_path

    if path_names or url_parts:
        return "UNMAPPED", "none", "no exact name match and no safe path rule", None, None
    return "UNMAPPED", "none", "missing source category", None, None


def build_karzar_name_index(categories: list[dict[str, object]]) -> dict[str, tuple[str, str]]:
    by_id = {str(c.get("id")): c for c in categories}
    index: dict[str, tuple[str, str]] = {}
    for cat in categories:
        cid = str(cat.get("id") or "")
        name = str(cat.get("name") or "")
        if not cid or not name:
            continue
        parts = [name]
        parent_id = cat.get("parent_id")
        guard = 0
        while parent_id is not None and guard < 12:
            parent = by_id.get(str(parent_id))
            if not parent:
                break
            parts.append(str(parent.get("name") or ""))
            parent_id = parent.get("parent_id")
            guard += 1
        path = " › ".join(reversed(parts))
        index[_fold_name(name)] = (cid, path)
    return index


def category_mapping_rows(
    products: list[SourceProduct],
    karzar_categories: list[dict[str, object]],
) -> list[CategoryMapRow]:
    index = build_karzar_name_index(karzar_categories)
    counts: Counter[tuple[str, ...]] = Counter()
    samples: dict[tuple[str, ...], SourceProduct] = {}
    for product in products:
        key = tuple(product.category_path) or ("(missing)",)
        counts[key] += 1
        samples.setdefault(key, product)
    rows: list[CategoryMapRow] = []
    for path, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        sample = samples[path]
        status, confidence, reason, kid, kpath = map_source_category(
            path_names=list(path) if path != ("(missing)",) else [],
            category_url=sample.source_category_url,
            karzar_by_folded_name=index,
        )
        rows.append(
            CategoryMapRow(
                source_category_path=" > ".join(path),
                source_category_name=path[-1] if path else "",
                source_product_count=count,
                karzar_category_id=kid,
                karzar_category_path=kpath,
                mapping_status=status,
                mapping_confidence=confidence,
                mapping_reason=reason,
            )
        )
    return rows
