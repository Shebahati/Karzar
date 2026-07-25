#!/usr/bin/env python3
"""Safe taxonomy remediation for استاندارد padding leaves and empty nodes.

Dry-run by default. Lists:
  - empty leaves (product_count == 0)
  - empty roots / non-leaves with no products and no non-empty descendants
  - استاندارد / استاندارد — leaves with product counts
  - rename suggestions (strip «استاندارد — » prefix when suffix is meaningful)

Apply modes:
  --apply                 rename استاندارد leaves with a safe distinguishing suffix
  --delete-empty          DELETE empty leaves (product_count == 0, is_leaf)
  --delete-empty-roots    DELETE empty root categories with no children
                          (e.g. dead «اینسرت» root). Implies leaf prune first
                          is NOT automatic — roots must already be childless.

Usage:
  python scripts/remediate_standard_leaves.py
  python scripts/remediate_standard_leaves.py --apply --token <jwt>
  python scripts/remediate_standard_leaves.py --delete-empty --token <jwt>
  python scripts/remediate_standard_leaves.py --delete-empty-roots --token <jwt>
  python scripts/remediate_standard_leaves.py --api http://localhost:8000/api/v1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Allow `python scripts/...` from repo root / backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

STANDARD_PREFIXES = ("استاندارد —", "استاندارد -", "استاندارد–")
STANDARD_EXACT = {"استاندارد"}


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
    return any(n.startswith(p) for p in STANDARD_PREFIXES) or n.startswith("استاندارد (")


def suggest_rename(name: str, parent_name: str | None) -> str | None:
    """Return a safer leaf name, or None if no automatic rename is safe."""
    n = (name or "").strip()
    for prefix in STANDARD_PREFIXES:
        if n.startswith(prefix):
            suffix = n[len(prefix) :].strip(" —-–")
            if not suffix:
                return None
            # If suffix only duplicates parent, keep parent-type label without استاندارد.
            if parent_name and suffix == parent_name.strip():
                return f"{parent_name} — عمومی"
            return suffix
    if n in STANDARD_EXACT and parent_name:
        return f"{parent_name} — عمومی"
    return None


def _row(c: dict[str, Any], by_id: dict[int, dict[str, Any]]) -> dict[str, Any]:
    parent = by_id.get(c.get("parent_id"))
    return {
        "id": c["id"],
        "name": c.get("name"),
        "slug": c.get("slug"),
        "depth": c.get("depth"),
        "product_count": int(c.get("product_count") or 0),
        "parent_id": c.get("parent_id"),
        "parent_name": parent.get("name") if parent else None,
        "breadcrumb": c.get("breadcrumb"),
        "is_leaf": bool(c.get("is_leaf")),
    }


def _child_ids(cats: list[dict[str, Any]], parent_id: int) -> list[int]:
    return [c["id"] for c in cats if c.get("parent_id") == parent_id]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--token", default="", help="Bearer JWT for write ops")
    parser.add_argument(
        "--step-up-token",
        default="",
        help="X-Step-Up-Token for DELETE (from POST /auth/step-up)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply safe renames (default is dry-run)",
    )
    parser.add_argument(
        "--delete-empty",
        action="store_true",
        help="DELETE empty leaf categories (product_count == 0)",
    )
    parser.add_argument(
        "--delete-empty-roots",
        action="store_true",
        help="DELETE empty root categories that have no children (e.g. dead Insert)",
    )
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="Required safety flag alongside --delete-empty / --delete-empty-roots",
    )
    args = parser.parse_args()

    api = args.api.rstrip("/")
    st, cats_resp = http_json("GET", f"{api}/categories/")
    if st != 200:
        print(f"FAIL list categories: {st} {cats_resp}", file=sys.stderr)
        return 1

    cats: list[dict[str, Any]] = cats_resp.get("data") or []
    by_id = {c["id"]: c for c in cats}

    empty_leaves: list[dict[str, Any]] = []
    empty_childless_roots: list[dict[str, Any]] = []
    standard_leaves: list[dict[str, Any]] = []
    rename_plan: list[tuple[dict[str, Any], str]] = []

    for c in cats:
        count = int(c.get("product_count") or 0)
        name = c.get("name") or ""
        parent_id = c.get("parent_id")
        is_root = parent_id is None
        children = _child_ids(cats, c["id"])

        if c.get("is_leaf") and count == 0:
            empty_leaves.append(_row(c, by_id))

        if is_root and count == 0 and not children:
            empty_childless_roots.append(_row(c, by_id))

        if c.get("is_leaf") and is_standard_name(name):
            parent = by_id.get(parent_id)
            parent_name = parent.get("name") if parent else None
            standard_leaves.append(_row(c, by_id))
            suggestion = suggest_rename(name, parent_name)
            if suggestion and suggestion != name:
                rename_plan.append((c, suggestion))

    mutating = args.apply or args.delete_empty or args.delete_empty_roots
    report = {
        "dry_run": not mutating,
        "empty_leaf_count": len(empty_leaves),
        "empty_childless_root_count": len(empty_childless_roots),
        "standard_leaf_count": len(standard_leaves),
        "rename_candidates": len(rename_plan),
        "empty_leaves_sample": empty_leaves[:30],
        "empty_childless_roots": empty_childless_roots,
        "standard_leaves": standard_leaves,
        "rename_plan": [
            {
                "id": c["id"],
                "from": c.get("name"),
                "to": new_name,
                "product_count": c.get("product_count"),
            }
            for c, new_name in rename_plan
        ],
        "notes": [
            "Storefront already hides product_count=0 via filterNonEmptyTree.",
            "Empty leaf/root hard-delete requires --delete-empty/--delete-empty-roots "
            "plus --confirm-delete and admin JWT (step-up may be required by API).",
            "Delete API never reassigns products to a parent — only to another depth-3 leaf.",
            "Only safe renames are applied with --apply.",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not mutating:
        print(
            "\n[dry-run] No changes written. "
            "Use --apply / --delete-empty / --delete-empty-roots (+ --confirm-delete).",
            file=sys.stderr,
        )
        return 0

    if not args.token:
        print("Write modes require --token", file=sys.stderr)
        return 1

    auth = {"Authorization": f"Bearer {args.token}"}
    if args.step_up_token:
        auth["X-Step-Up-Token"] = args.step_up_token
    exit_code = 0

    if args.apply:
        ok = 0
        failed = 0
        for c, new_name in rename_plan:
            st, body = http_json(
                "PUT",
                f"{api}/categories/{c['id']}",
                headers=auth,
                body={"name": new_name},
            )
            if st == 200:
                ok += 1
                print(f"[rename] {c['id']}: {c.get('name')} → {new_name}")
            else:
                failed += 1
                print(f"[rename] FAIL {c['id']}: {st} {body}", file=sys.stderr)
        print(f"[done] renamed={ok} failed={failed}")
        if failed:
            exit_code = 2

    if args.delete_empty or args.delete_empty_roots:
        if not args.confirm_delete:
            print(
                "--delete-empty / --delete-empty-roots require --confirm-delete",
                file=sys.stderr,
            )
            return 1

        targets: list[dict[str, Any]] = []
        if args.delete_empty:
            # Deepest first so parents become deletable in a later root pass.
            targets.extend(sorted(empty_leaves, key=lambda r: int(r.get("depth") or 0), reverse=True))
        if args.delete_empty_roots:
            targets.extend(empty_childless_roots)

        # De-dupe by id while preserving order.
        seen: set[int] = set()
        ordered: list[dict[str, Any]] = []
        for row in targets:
            cid = int(row["id"])
            if cid in seen:
                continue
            seen.add(cid)
            ordered.append(row)

        ok = 0
        failed = 0
        for row in ordered:
            cid = int(row["id"])
            # Empty delete: no target_category_id query param.
            url = f"{api}/categories/{cid}"
            st, body = http_json("DELETE", url, headers=auth)
            if st == 200:
                ok += 1
                print(
                    f"[delete] {cid}: {row.get('name')} "
                    f"(depth={row.get('depth')}, products={row.get('product_count')})"
                )
            else:
                failed += 1
                print(f"[delete] FAIL {cid}: {st} {body}", file=sys.stderr)
                # Hint for step-up
                if st in (401, 403):
                    print(
                        "Hint: DELETE requires super_admin JWT + --step-up-token "
                        "(POST /auth/step-up → X-Step-Up-Token).",
                        file=sys.stderr,
                    )
        print(f"[done] deleted={ok} failed={failed}")
        if failed:
            exit_code = 2

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
