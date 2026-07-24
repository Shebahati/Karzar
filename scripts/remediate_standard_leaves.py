#!/usr/bin/env python3
"""Safe taxonomy remediation for استاندارد padding leaves and empty Insert.

Dry-run by default. Lists:
  - استاندارد / «عمومی» padding leaves with direct + subtree product counts
  - rename plan for redundant «استاندارد — {Parent}» names
  - empty استاندارد leaves eligible for safe delete (0 products, 0 children)
  - Insert root decision (collapse padding-only empty tree vs keep for later fill)

Apply mode (--apply):
  - Renames only (never moves products to depth-2 parents)
  - Deletes empty استاندارد leaves (no products, no children) via DELETE API
  - Optionally collapses padding-only empty Insert subtree bottom-up

Depth-3 product assignment rule is never broken: non-empty استاندارد leaves
are renamed in place and kept as L3.

Usage:
  python scripts/remediate_standard_leaves.py
  python scripts/remediate_standard_leaves.py --apply --token <jwt> [--step-up <token>]
  python scripts/remediate_standard_leaves.py --apply --token <jwt> --step-up <token> --collapse-insert
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Allow `python scripts/...` from repo root / backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

STANDARD_PREFIXES = ("استاندارد —", "استاندارد -", "استاندارد–")
STANDARD_EXACT = {"استاندارد"}
GENERAL_SUFFIXES = ("— عمومی", "- عمومی", "– عمومی")
INSERT_ROOT_NAMES = {"اینسرت", "insert"}


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    data = None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return exc.code, payload
    except URLError as exc:
        return 0, {"error": str(exc)}


def is_standard_name(name: str) -> bool:
    n = (name or "").strip()
    if n in STANDARD_EXACT:
        return True
    if any(n.startswith(p) for p in STANDARD_PREFIXES) or n.startswith("استاندارد ("):
        return True
    return False


def is_padding_name(name: str) -> bool:
    """استاندارد padding or residual «— عمومی» leaf labels."""
    n = (name or "").strip()
    if is_standard_name(n):
        return True
    return any(n.endswith(s) for s in GENERAL_SUFFIXES) or n in {"عمومی", "سری عمومی"}


def suggest_rename(name: str, parent_name: str | None) -> str | None:
    """Return a safer buyer-facing leaf name, or None if no automatic rename is safe.

    Rules:
    - Strip «استاندارد — » when the suffix is a meaningful distinguishing label.
    - If suffix only duplicates the parent (depth-3 padding), rename to
      «{Parent} — عمومی» — keep as L3; never suggest moving products up.
    - Exact «استاندارد» under a parent → «{Parent} — عمومی».
    - Do not rename residual «— عمومی» names (already remediated).
    """
    n = (name or "").strip()
    parent = (parent_name or "").strip() or None

    if any(n.endswith(s) for s in GENERAL_SUFFIXES) or n in {"عمومی", "سری عمومی"}:
        return None

    for prefix in STANDARD_PREFIXES:
        if n.startswith(prefix):
            suffix = n[len(prefix) :].strip(" —-–")
            if not suffix:
                return f"{parent} — عمومی" if parent else None
            if parent and suffix == parent:
                return f"{parent} — عمومی"
            return suffix

    if n in STANDARD_EXACT:
        return f"{parent} — عمومی" if parent else None

    if n.startswith("استاندارد ("):
        return f"{parent} — عمومی" if parent else None

    return None


def unique_rename(
    suggested: str,
    *,
    category_id: int,
    sibling_names: set[str],
    used_names: set[str],
) -> str:
    """Ensure rename does not collide with siblings / global names."""
    candidate = suggested.strip()
    if candidate and candidate not in sibling_names and candidate not in used_names:
        return candidate
    # Prefer parent-scoped uniqueness with id suffix as last resort.
    base = candidate or "عمومی"
    alt = f"{base} ({category_id})"
    if alt not in sibling_names and alt not in used_names:
        return alt
    return f"سری عمومی ({category_id})"


def build_children_index(cats: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    children: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for c in cats:
        pid = c.get("parent_id")
        if pid is not None:
            children[int(pid)].append(c)
    return children


def direct_counts_from_flat(cats: list[dict[str, Any]]) -> dict[int, int]:
    """API product_count is subtree; recover direct for leaves (= subtree).

    For non-leaves, direct is approximated as subtree minus children subtrees.
    """
    by_id = {int(c["id"]): c for c in cats}
    children = build_children_index(cats)
    direct: dict[int, int] = {}
    for c in cats:
        cid = int(c["id"])
        subtree = int(c.get("product_count") or 0)
        child_sum = sum(int(ch.get("product_count") or 0) for ch in children.get(cid, []))
        # Clamp at 0 in case of stale counts.
        direct[cid] = max(0, subtree - child_sum) if children.get(cid) else subtree
        _ = by_id  # silence unused in some linters
    return direct


def is_empty_deletable_leaf(cat: dict[str, Any], *, child_count: int, direct_count: int) -> bool:
    """Safe delete: leaf, no children, no direct products."""
    if child_count > 0:
        return False
    if direct_count > 0:
        return False
    if int(cat.get("product_count") or 0) > 0:
        return False
    # Prefer explicit leaf flag; also allow depth-3 with no kids.
    if cat.get("is_leaf") is False and child_count == 0:
        # Still deletable empty node with no children.
        pass
    return True


def analyze_insert_root(
    cats: list[dict[str, Any]],
    *,
    children: dict[int, list[dict[str, Any]]],
    direct: dict[int, int],
) -> dict[str, Any]:
    """Decide what to do with dead Insert root (اینسرت)."""
    roots = [
        c
        for c in cats
        if c.get("parent_id") is None
        and (c.get("name") or "").strip().lower() in INSERT_ROOT_NAMES
    ]
    if not roots:
        return {
            "found": False,
            "decision": "no_insert_root",
            "notes": ["No Insert/اینسرت root found."],
        }

    root = roots[0]
    rid = int(root["id"])
    subtree_pc = int(root.get("product_count") or 0)
    descendants: list[dict[str, Any]] = []

    def walk(cid: int) -> None:
        for ch in children.get(cid, []):
            descendants.append(ch)
            walk(int(ch["id"]))

    walk(rid)

    padding_only = True
    non_padding: list[dict[str, Any]] = []
    for d in descendants:
        name = (d.get("name") or "").strip()
        # Structural L2 family names under Insert are OK to keep if we are not
        # collapsing; padding leaves are استاندارد / عمومی only.
        if int(d.get("depth") or 0) >= 3 and not is_padding_name(name):
            padding_only = False
            non_padding.append(d)
        elif int(d.get("depth") or 0) == 2 and int(d.get("product_count") or 0) > 0:
            padding_only = False
            non_padding.append(d)

    empty_padding_leaves = [
        d
        for d in descendants
        if is_padding_name(d.get("name") or "")
        and is_empty_deletable_leaf(
            d,
            child_count=len(children.get(int(d["id"]), [])),
            direct_count=direct.get(int(d["id"]), 0),
        )
    ]

    if subtree_pc > 0:
        decision = "keep_structure_has_products"
        notes = [
            "Insert root has products in subtree; only rename/delete empty استاندارد leaves.",
            "Do not delete root or non-empty branches.",
        ]
    elif padding_only and descendants:
        decision = "collapse_padding_only_empty"
        notes = [
            "Insert root has 0 products and only padding/empty descendants.",
            "Safe plan: delete empty استاندارد leaves, then empty L2 parents, then empty root.",
            "Sibling root «ابزار اینسرتی» already holds real insert-tooling SKUs.",
        ]
    elif not descendants and subtree_pc == 0:
        decision = "delete_empty_root"
        notes = ["Insert root is empty with no children; safe to delete."]
    else:
        decision = "keep_structure_for_later_fill"
        notes = [
            "Insert has non-padding structure but 0 products.",
            "Leave taxonomy for later fill; storefront already hides product_count=0.",
            "Only delete truly empty استاندارد padding leaves.",
        ]

    return {
        "found": True,
        "decision": decision,
        "root": {
            "id": rid,
            "name": root.get("name"),
            "slug": root.get("slug"),
            "product_count": subtree_pc,
            "direct_count": direct.get(rid, 0),
            "child_count": len(children.get(rid, [])),
        },
        "descendant_count": len(descendants),
        "empty_padding_leaves": [
            {"id": d["id"], "name": d.get("name"), "depth": d.get("depth")}
            for d in empty_padding_leaves
        ],
        "non_padding_nodes": [
            {"id": d["id"], "name": d.get("name"), "depth": d.get("depth")}
            for d in non_padding[:20]
        ],
        "collapse_order_ids": _collapse_order(rid, children, direct)
        if decision in {"collapse_padding_only_empty", "delete_empty_root"}
        else [],
        "notes": notes,
    }


def _collapse_order(
    root_id: int,
    children: dict[int, list[dict[str, Any]]],
    direct: dict[int, int],
) -> list[int]:
    """Bottom-up delete order for an empty tree (leaves first)."""
    order: list[int] = []

    def walk(cid: int) -> None:
        for ch in children.get(cid, []):
            walk(int(ch["id"]))
        # Only include nodes that are empty (no direct products). Callers must
        # re-check after prior deletes; initial plan assumes whole subtree empty.
        if direct.get(cid, 0) == 0:
            order.append(cid)

    walk(root_id)
    return order


def build_plan(cats: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {int(c["id"]): c for c in cats}
    children = build_children_index(cats)
    direct = direct_counts_from_flat(cats)
    used_names = {(c.get("name") or "").strip() for c in cats}

    empty_leaves: list[dict[str, Any]] = []
    padding_leaves: list[dict[str, Any]] = []
    rename_plan: list[dict[str, Any]] = []
    delete_plan: list[dict[str, Any]] = []

    for c in cats:
        cid = int(c["id"])
        name = (c.get("name") or "").strip()
        parent = by_id.get(c.get("parent_id"))
        parent_name = (parent.get("name") if parent else None) or None
        child_count = len(children.get(cid, []))
        is_leaf = bool(c.get("is_leaf")) or child_count == 0
        dcount = direct.get(cid, 0)
        subtree = int(c.get("product_count") or 0)

        row = {
            "id": cid,
            "name": name,
            "slug": c.get("slug"),
            "depth": c.get("depth"),
            "product_count": subtree,
            "direct_count": dcount,
            "subtree_count": subtree,
            "parent_id": c.get("parent_id"),
            "parent_name": parent_name,
            "child_count": child_count,
            "is_leaf": is_leaf,
            "breadcrumb": c.get("breadcrumb"),
        }

        if is_leaf and subtree == 0:
            empty_leaves.append(row)

        if is_leaf and is_padding_name(name):
            padding_leaves.append(row)
            suggestion = suggest_rename(name, parent_name)
            if suggestion and suggestion != name and dcount > 0:
                siblings = {
                    (ch.get("name") or "").strip()
                    for ch in children.get(int(c["parent_id"]), [])
                    if int(ch["id"]) != cid
                } if c.get("parent_id") is not None else set()
                final = unique_rename(
                    suggestion,
                    category_id=cid,
                    sibling_names=siblings,
                    used_names=used_names - {name},
                )
                rename_plan.append(
                    {
                        "id": cid,
                        "from": name,
                        "to": final,
                        "product_count": subtree,
                        "direct_count": dcount,
                        "reason": "rename_padding_keep_l3",
                    }
                )
                used_names.add(final)

            if is_standard_name(name) and is_empty_deletable_leaf(
                c, child_count=child_count, direct_count=dcount
            ):
                delete_plan.append(
                    {
                        "id": cid,
                        "name": name,
                        "depth": c.get("depth"),
                        "reason": "empty_standard_leaf",
                        "product_count": 0,
                    }
                )

    insert_analysis = analyze_insert_root(cats, children=children, direct=direct)

    return {
        "empty_leaf_count": len(empty_leaves),
        "padding_leaf_count": len(padding_leaves),
        "standard_leaf_count": sum(
            1 for r in padding_leaves if is_standard_name(r["name"])
        ),
        "rename_candidates": len(rename_plan),
        "delete_candidates": len(delete_plan),
        "empty_leaves_sample": empty_leaves[:30],
        "padding_leaves": padding_leaves,
        "rename_plan": rename_plan,
        "delete_plan": delete_plan,
        "insert_root": insert_analysis,
        "notes": [
            "Non-empty استاندارد leaves are renamed in place and kept as depth-3.",
            "Products are never moved to depth-2 parents.",
            "Empty استاندارد leaves (0 products, 0 children) are delete candidates.",
            "Storefront already hides product_count=0; is_nav_visible schema skipped.",
            "Insert collapse only when decision=collapse_padding_only_empty and --collapse-insert.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--token", default="", help="Bearer JWT for write ops")
    parser.add_argument(
        "--step-up",
        default="",
        help="Step-up token (X-Step-Up-Token) required for deletes",
    )
    parser.add_argument(
        "--pin",
        default="",
        help="Admin step-up PIN; mint a fresh single-use token before each DELETE",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply safe renames and empty-standard deletes (default is dry-run)",
    )
    parser.add_argument(
        "--collapse-insert",
        action="store_true",
        help="When Insert is padding-only empty, delete empty descendants then root",
    )
    parser.add_argument(
        "--skip-deletes",
        action="store_true",
        help="With --apply, only rename (no DELETE calls)",
    )
    args = parser.parse_args()

    api = args.api.rstrip("/")
    st, cats_resp = http_json("GET", f"{api}/categories/")
    if st != 200:
        print(f"FAIL list categories: {st} {cats_resp}", file=sys.stderr)
        return 1

    cats: list[dict[str, Any]] = cats_resp.get("data") or []
    plan = build_plan(cats)
    report = {
        "dry_run": not args.apply,
        "collapse_insert_requested": bool(args.collapse_insert),
        **plan,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not args.apply:
        print(
            "\n[dry-run] No changes written. Re-run with --apply "
            "(+ --step-up for deletes, optional --collapse-insert).",
            file=sys.stderr,
        )
        return 0

    if not args.token:
        print("--apply requires --token", file=sys.stderr)
        return 1

    auth = {"Authorization": f"Bearer {args.token}"}
    rename_ok = rename_fail = 0
    for item in plan["rename_plan"]:
        st, body = http_json(
            "PUT",
            f"{api}/categories/{item['id']}",
            headers=auth,
            body={"name": item["to"]},
        )
        if st == 200:
            rename_ok += 1
            print(f"[rename] {item['id']}: {item['from']} → {item['to']}")
        else:
            rename_fail += 1
            print(f"[rename] FAIL {item['id']}: {st} {body}", file=sys.stderr)

    delete_ok = delete_fail = 0
    deleted_ids: list[int] = []

    def mint_step_up() -> str | None:
        """Step-up tokens are single-use; mint fresh when --pin is provided."""
        if args.pin:
            st_pin, body_pin = http_json(
                "POST",
                f"{api}/auth/verify-pin",
                headers=auth,
                body={"pin": args.pin},
            )
            if st_pin != 200:
                print(f"[step-up] FAIL mint: {st_pin} {body_pin}", file=sys.stderr)
                return None
            token = (body_pin or {}).get("secure_token") or ""
            return token or None
        return args.step_up or None

    def delete_category(category_id: int, label: str) -> bool:
        nonlocal delete_ok, delete_fail
        step = mint_step_up()
        if not step:
            delete_fail += 1
            print(f"[delete] FAIL {category_id}: missing step-up token", file=sys.stderr)
            return False
        st, body = http_json(
            "DELETE",
            f"{api}/categories/{category_id}",
            headers={**auth, "X-Step-Up-Token": step},
        )
        if st == 200:
            delete_ok += 1
            deleted_ids.append(int(category_id))
            print(f"[delete] {category_id}: {label}")
            return True
        delete_fail += 1
        print(f"[delete] FAIL {category_id}: {st} {body}", file=sys.stderr)
        return False

    if not args.skip_deletes:
        if plan["delete_plan"] and not (args.step_up or args.pin):
            print(
                "--apply deletes require --step-up or --pin (skipping deletes; renames done)",
                file=sys.stderr,
            )
        else:
            for item in plan["delete_plan"]:
                # Skip already-deleted from a prior partial apply.
                delete_category(int(item["id"]), f"{item['name']} ({item['reason']})")

            insert = plan["insert_root"]
            if (
                args.collapse_insert
                and insert.get("decision") == "collapse_padding_only_empty"
                and (args.step_up or args.pin)
            ):
                # Refresh tree after leaf deletes, then delete remaining empty nodes bottom-up.
                st, cats_resp2 = http_json("GET", f"{api}/categories/")
                if st != 200:
                    print(f"[insert] FAIL refresh: {st}", file=sys.stderr)
                    delete_fail += 1
                else:
                    cats2 = cats_resp2.get("data") or []
                    children2 = build_children_index(cats2)
                    direct2 = direct_counts_from_flat(cats2)
                    by_id2 = {int(c["id"]): c for c in cats2}
                    root_id = int(insert["root"]["id"])
                    if root_id in by_id2:
                        order = _collapse_order(root_id, children2, direct2)
                        for cid in order:
                            if cid in deleted_ids:
                                continue
                            node = by_id2.get(cid)
                            if not node:
                                continue
                            # Recompute children after prior deletes in this loop.
                            still_children = [
                                ch
                                for ch in children2.get(cid, [])
                                if int(ch["id"]) not in deleted_ids
                            ]
                            if still_children:
                                print(
                                    f"[insert] skip {cid}: still has children",
                                    file=sys.stderr,
                                )
                                continue
                            if direct2.get(cid, 0) > 0 or int(node.get("product_count") or 0) > 0:
                                print(
                                    f"[insert] skip {cid}: not empty",
                                    file=sys.stderr,
                                )
                                continue
                            delete_category(cid, f"{node.get('name')} (insert-collapse)")
            elif args.collapse_insert:
                print(
                    f"[insert] collapse skipped (decision={insert.get('decision')})",
                    file=sys.stderr,
                )

    summary = {
        "renamed": rename_ok,
        "rename_failed": rename_fail,
        "deleted": delete_ok,
        "delete_failed": delete_fail,
        "deleted_ids": deleted_ids,
    }
    print(f"\n[done] {json.dumps(summary, ensure_ascii=False)}")
    return 0 if rename_fail == 0 and delete_fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
