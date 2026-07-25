"""Default megamenu nav-group seed (mirrors Storefront nav-groups.ts)."""

from __future__ import annotations

from typing import Any

# Locked IA: same five merchandising groups as frontend/Storefront/src/config/nav-groups.ts
DEFAULT_NAV_GROUP_SEEDS: list[dict[str, Any]] = [
    {
        "slug": "metrology",
        "label": "اندازه‌گیری",
        "highlight": True,
        "sort_order": 0,
        "matchers": ["اندازه گیری", "اندازه‌گیری", "andaze", "measurement"],
    },
    {
        "slug": "cutting",
        "label": "براده‌برداری",
        "highlight": False,
        "sort_order": 1,
        "matchers": [
            "اینسرت",
            "ابزار اینسرتی",
            "ابزار انگشتی",
            "انگشتی",
            "مته",
            "قلاویز",
            "insert",
        ],
    },
    {
        "slug": "holding",
        "label": "ابزارگیری و گیرش",
        "highlight": False,
        "sort_order": 2,
        "matchers": ["ابزارگیر", "ابزار گیرشی"],
    },
    {
        "slug": "machines",
        "label": "ماشین‌ها و تجهیزات",
        "highlight": False,
        "sort_order": 3,
        "matchers": ["دستگاه‌های صنعتی", "دستگاه های صنعتی"],
    },
    {
        "slug": "accessories",
        "label": "لوازم جانبی",
        "highlight": False,
        "sort_order": 4,
        "matchers": ["لوازم جانبی صنعتی", "لوازم جانبی"],
    },
]


def normalize_label(value: str) -> str:
    return (
        value.strip()
        .replace("\u200c", "")
        .replace("ي", "ی")
        .replace("ك", "ک")
        .lower()
    )


def matches_root(*, name: str, slug: str, matcher: str) -> bool:
    m = normalize_label(matcher)
    n = normalize_label(name)
    s = normalize_label(slug)
    return n == m or m in n or m in s or s == m


def resolve_root_ids_for_matchers(
    roots: list[tuple[int, str, str]],
    matchers: list[str],
    *,
    assigned: set[int],
) -> list[int]:
    """Match L1 roots by name/slug; earliest matcher wins; skip already-assigned."""
    matched: list[tuple[int, int]] = []  # (matcher_rank, id)
    for root_id, name, slug in roots:
        if root_id in assigned:
            continue
        rank = next(
            (idx for idx, matcher in enumerate(matchers) if matches_root(name=name, slug=slug, matcher=matcher)),
            None,
        )
        if rank is None:
            continue
        matched.append((rank, root_id))
    matched.sort(key=lambda item: (item[0], item[1]))
    ids = [root_id for _, root_id in matched]
    assigned.update(ids)
    return ids
