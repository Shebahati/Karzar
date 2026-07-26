"""Detect storefront «عمومی» padding filler category names and plan removals.

Mirrors frontend `isPaddingLeafName` in megamenu-display.ts so backend
remediation stays consistent with megamenu collapse.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

_SEPARATORS = ("—", "-", "–", "ـ")

# Products attach to depth ≥ 2; L1 roots must never receive products.
MIN_PRODUCT_CATEGORY_DEPTH = 2


def norm_name(name: str) -> str:
    """Strip ZWNJ/space edges; normalize Arabic Yeh/Kaf → Persian."""
    return (
        (name or "")
        .strip()
        .replace("\u200c", "")
        .replace("ي", "ی")
        .replace("ك", "ک")
    )


def is_padding_leaf_name(name: str) -> bool:
    """True for exact «عمومی» or names ending with separator + «عمومی».

    Examples:
      «عمومی», «کولیس — عمومی», «برقو - عمومی»
    Non-matches (intentional real leaves):
      «ابزار دستی عمومی» (no separator before عمومی)
    """
    n = norm_name(name)
    if not n:
        return False
    if n == "عمومی":
        return True
    for sep in _SEPARATORS:
        idx = n.rfind(sep)
        if idx >= 0 and n[idx + len(sep) :].strip() == "عمومی":
            return True
    return False


def plan_omumi_removals(
    cats: list[dict[str, Any]],
    *,
    direct_product_counts: dict[int, int] | None = None,
) -> dict[str, Any]:
    """Build move/delete plan from flat category rows (API or ORM-serialized).

    `direct_product_counts` overrides API rolled-up `product_count` when provided
    (accurate via-db apply counts).
    """
    by_id = {int(c["id"]): c for c in cats if c.get("id") is not None}
    children: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for c in cats:
        children[c.get("parent_id")].append(c)

    candidates = [c for c in cats if is_padding_leaf_name(c.get("name") or "")]
    near_misses = [
        c
        for c in cats
        if "عموم" in norm_name(c.get("name") or "") and c not in candidates
    ]

    moves: list[dict[str, Any]] = []
    skips: list[dict[str, Any]] = []

    for c in sorted(candidates, key=lambda x: int(x.get("depth") or 0), reverse=True):
        cid = int(c["id"])
        name = c.get("name") or ""
        depth = int(c.get("depth") or 0)
        pid = c.get("parent_id")
        kids = children.get(cid, [])
        direct = (
            int(direct_product_counts[cid])
            if direct_product_counts is not None
            else int(c.get("product_count") or 0)
        )

        base: dict[str, Any] = {
            "id": cid,
            "name": name,
            "slug": c.get("slug"),
            "depth": depth,
            "product_count": direct,
            "parent_id": pid,
            "breadcrumb": c.get("breadcrumb"),
        }

        if kids:
            skips.append({**base, "reason": f"has_children {[k['id'] for k in kids]}"})
            continue
        if pid is None:
            skips.append({**base, "reason": "no_parent_l1_named_omumi"})
            continue

        parent = by_id.get(int(pid))
        if parent is None:
            skips.append({**base, "reason": "parent_missing"})
            continue

        parent_depth = int(parent.get("depth") or 0)
        siblings = children.get(pid, [])
        sole = len(siblings) == 1
        parent_direct = (
            int(direct_product_counts.get(int(pid), 0))
            if direct_product_counts is not None
            else None
        )

        if not sole:
            skips.append(
                {
                    **base,
                    "reason": "not_sole_child_parent_would_remain_non_leaf",
                    "sibling_ids": [int(s["id"]) for s in siblings],
                    "parent_name": parent.get("name"),
                }
            )
            continue

        if parent_depth < MIN_PRODUCT_CATEGORY_DEPTH:
            skips.append(
                {
                    **base,
                    "reason": "parent_depth_lt_2_not_selectable",
                    "parent_id": int(pid),
                    "parent_name": parent.get("name"),
                    "parent_depth": parent_depth,
                }
            )
            continue

        moves.append(
            {
                **base,
                "parent_id": int(pid),
                "parent_name": parent.get("name"),
                "parent_depth": parent_depth,
                "parent_direct_products": parent_direct,
                "is_sole_child": True,
                "action": "move_products_to_parent_then_delete",
            }
        )

    samples = []
    for m in moves[:5]:
        crumb = m.get("breadcrumb") or []
        samples.append(
            {
                "before": " > ".join(crumb) if crumb else m["name"],
                "after": " > ".join(crumb[:-1]) if crumb else m.get("parent_name"),
                "products": m["product_count"],
                "leaf_id": m["id"],
                "parent_id": m["parent_id"],
            }
        )

    return {
        "candidate_count": len(candidates),
        "move_count": len(moves),
        "skip_count": len(skips),
        "products_to_move": sum(m["product_count"] for m in moves),
        "moves": moves,
        "skips": skips,
        "near_misses": [
            {
                "id": int(c["id"]),
                "name": c.get("name"),
                "depth": c.get("depth"),
                "product_count": int(c.get("product_count") or 0),
                "note": "contains عموم but not padding-leaf pattern — left intact",
            }
            for c in near_misses
        ],
        "before_after_samples": samples,
    }
