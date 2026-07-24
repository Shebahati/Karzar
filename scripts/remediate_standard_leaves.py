#!/usr/bin/env python3
"""Safe taxonomy remediation for استاندارد padding leaves and empty leaves.

Dry-run by default. Lists:
  - empty leaves (product_count == 0)
  - استاندارد / استاندارد — leaves with product counts
  - rename suggestions (strip «استاندارد — » prefix when suffix is meaningful)

Apply mode only renames استاندارد leaves with a safe distinguishing suffix;
empty leaves are reported for FE hide-by-count (no hard delete).

Usage:
  python scripts/remediate_standard_leaves.py
  python scripts/remediate_standard_leaves.py --apply
  python scripts/remediate_standard_leaves.py --api http://localhost:8000 --token <jwt>
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--token", default="", help="Bearer JWT for write ops")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply safe renames (default is dry-run)",
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
    standard_leaves: list[dict[str, Any]] = []
    rename_plan: list[tuple[dict[str, Any], str]] = []

    for c in cats:
        if not c.get("is_leaf"):
            continue
        count = int(c.get("product_count") or 0)
        name = c.get("name") or ""
        parent = by_id.get(c.get("parent_id"))
        parent_name = parent.get("name") if parent else None
        row = {
            "id": c["id"],
            "name": name,
            "slug": c.get("slug"),
            "depth": c.get("depth"),
            "product_count": count,
            "parent_id": c.get("parent_id"),
            "parent_name": parent_name,
            "breadcrumb": c.get("breadcrumb"),
        }
        if count == 0:
            empty_leaves.append(row)
        if is_standard_name(name):
            standard_leaves.append(row)
            suggestion = suggest_rename(name, parent_name)
            if suggestion and suggestion != name:
                rename_plan.append((c, suggestion))

    report = {
        "dry_run": not args.apply,
        "empty_leaf_count": len(empty_leaves),
        "standard_leaf_count": len(standard_leaves),
        "rename_candidates": len(rename_plan),
        "empty_leaves_sample": empty_leaves[:30],
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
            "Empty leaves are left in DB; storefront hides product_count=0.",
            "Hard-delete of empty roots (e.g. Insert) requires manual confirmation.",
            "Only safe renames are applied with --apply.",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not args.apply:
        print("\n[dry-run] No changes written. Re-run with --apply to rename.", file=sys.stderr)
        return 0

    if not args.token:
        print("--apply requires --token", file=sys.stderr)
        return 1

    auth = {"Authorization": f"Bearer {args.token}"}
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

    print(f"\n[done] renamed={ok} failed={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
