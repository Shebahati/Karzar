#!/usr/bin/env python3
"""Promote Measurement L2 categories to L1 and retarget megamenu metrology roots.

Live reshape (ids from production seed):
  - Promote 56 «اندازه گیری دقیق», 81 «CNC اندازه گیری», 87 «اندازه گیری آزمایشگاهی»
    to parent_id=null (new L1 roots).
  - Replace nav-group `metrology` root_category_ids with [56, 81, 87]
    (preserves other groups).
  - Delete empty former hub root id=7 «اندازه گیری» once childless.

Dry-run by default. Apply requires --apply --confirm plus admin JWT.
Deleting id=7 also needs --step-up-token (POST /auth/step-up).

Prerequisites:
  Deploy the selectable-leaf rule change (depth 2|3) BEFORE applying on live DB,
  so former L3→L2 product leaves remain valid product categories.

Usage:
  python scripts/promote_measurement_to_l1.py
  python scripts/promote_measurement_to_l1.py --api http://localhost:8000/api/v1
  python scripts/promote_measurement_to_l1.py --apply --confirm --token <jwt> \\
      --step-up-token <step-up>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FORMER_HUB_ID = 7
PROMOTE_IDS = (56, 81, 87)
METROLOGY_SLUG = "metrology"


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


def _row(c: dict[str, Any] | None) -> dict[str, Any] | None:
    if not c:
        return None
    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "slug": c.get("slug"),
        "parent_id": c.get("parent_id"),
        "depth": c.get("depth"),
        "is_leaf": c.get("is_leaf"),
        "product_count": int(c.get("product_count") or 0),
        "breadcrumb": c.get("breadcrumb"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--token", default="", help="Bearer JWT for write ops")
    parser.add_argument(
        "--step-up-token",
        default="",
        help="X-Step-Up-Token for DELETE of former hub (from POST /auth/step-up)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply promote + nav-group remap + delete hub (default dry-run)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required safety flag alongside --apply",
    )
    args = parser.parse_args()

    api = args.api.rstrip("/")
    st, cats_resp = http_json("GET", f"{api}/categories/")
    if st != 200:
        print(f"FAIL list categories: {st} {cats_resp}", file=sys.stderr)
        return 1

    cats: list[dict[str, Any]] = cats_resp.get("data") or []
    by_id = {int(c["id"]): c for c in cats if c.get("id") is not None}

    hub = by_id.get(FORMER_HUB_ID)
    promote_rows = [by_id.get(cid) for cid in PROMOTE_IDS]
    children_of_hub = [c for c in cats if c.get("parent_id") == FORMER_HUB_ID]

    st_nav, nav_resp = http_json("GET", f"{api}/nav-groups/")
    # Public storefront endpoint; admin list also works with token via /cms/nav-groups.
    if st_nav != 200:
        st_nav, nav_resp = http_json(
            "GET",
            f"{api}/cms/nav-groups",
            headers={"Authorization": f"Bearer {args.token}"} if args.token else None,
        )
    if st_nav != 200:
        print(f"FAIL list nav-groups: {st_nav} {nav_resp}", file=sys.stderr)
        return 1

    nav_groups: list[dict[str, Any]] = nav_resp.get("data") or []
    metrology = next((g for g in nav_groups if g.get("slug") == METROLOGY_SLUG), None)

    plan = {
        "dry_run": not args.apply,
        "promote": [
            {
                "id": cid,
                "from_parent_id": (by_id.get(cid) or {}).get("parent_id"),
                "to_parent_id": None,
                "current": _row(by_id.get(cid)),
            }
            for cid in PROMOTE_IDS
        ],
        "nav_metrology": {
            "from_root_category_ids": list((metrology or {}).get("root_category_ids") or []),
            "to_root_category_ids": list(PROMOTE_IDS),
            "group": {
                "slug": (metrology or {}).get("slug"),
                "label": (metrology or {}).get("label"),
            },
        },
        "delete_hub": {
            "id": FORMER_HUB_ID,
            "current": _row(hub),
            "remaining_children_before_promote": [_row(c) for c in children_of_hub],
            "note": "Delete only after promote makes hub childless and product_count==0",
        },
        "notes": [
            "Deploy selectable depth 2|3 code before --apply on production.",
            "Products stay on former L3 leaves (become depth-2 after promote).",
            "Megamenu label «اندازه‌گیری» remains; it is not an L1 taxonomy root.",
            "After merge: docker compose exec app python scripts/promote_measurement_to_l1.py "
            "--apply --confirm --token <jwt> --step-up-token <tok>",
        ],
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    missing = [cid for cid in PROMOTE_IDS if cid not in by_id]
    if missing:
        print(f"FAIL missing promote targets: {missing}", file=sys.stderr)
        return 1
    if hub is None:
        print(
            "WARN former hub id=7 already absent — will still promote children + remap nav.",
            file=sys.stderr,
        )

    if not args.apply:
        print(
            "\n[dry-run] No changes written. Use --apply --confirm --token …",
            file=sys.stderr,
        )
        return 0

    if not args.confirm:
        print("--apply requires --confirm", file=sys.stderr)
        return 1
    if not args.token:
        print("--apply requires --token", file=sys.stderr)
        return 1

    auth = {"Authorization": f"Bearer {args.token}"}
    if args.step_up_token:
        auth["X-Step-Up-Token"] = args.step_up_token

    exit_code = 0

    # 1) Promote L2 → L1
    for cid in PROMOTE_IDS:
        row = by_id[cid]
        if row.get("parent_id") is None:
            print(f"[promote] skip {cid}: already L1 ({row.get('name')})")
            continue
        st, body = http_json(
            "PUT",
            f"{api}/categories/{cid}",
            headers=auth,
            body={"parent_id": None},
        )
        if st == 200:
            print(f"[promote] {cid}: {row.get('name')} parent_id → null")
        else:
            exit_code = 2
            print(f"[promote] FAIL {cid}: {st} {body}", file=sys.stderr)

    # Refresh categories for nav validation / hub child check
    st, cats_resp = http_json("GET", f"{api}/categories/")
    if st != 200:
        print(f"FAIL re-list categories: {st} {cats_resp}", file=sys.stderr)
        return 2
    cats = cats_resp.get("data") or []
    by_id = {int(c["id"]): c for c in cats if c.get("id") is not None}

    # 2) Remap metrology nav roots (preserve other groups)
    st_nav, nav_resp = http_json("GET", f"{api}/cms/nav-groups", headers=auth)
    if st_nav != 200:
        print(f"FAIL admin list nav-groups: {st_nav} {nav_resp}", file=sys.stderr)
        return 2
    nav_groups = nav_resp.get("data") or []
    if not nav_groups:
        print("FAIL no nav groups returned from admin API", file=sys.stderr)
        return 2

    replace_payload = {
        "groups": [
            {
                "slug": g["slug"],
                "label": g["label"],
                "sort_order": int(g.get("sort_order") or 0),
                "is_enabled": bool(g.get("is_enabled", True)),
                "highlight": bool(g.get("highlight", False)),
                "root_category_ids": (
                    list(PROMOTE_IDS)
                    if g.get("slug") == METROLOGY_SLUG
                    else list(g.get("root_category_ids") or [])
                ),
            }
            for g in nav_groups
        ]
    }
    st, body = http_json(
        "PUT",
        f"{api}/cms/nav-groups",
        headers=auth,
        body=replace_payload,
    )
    if st == 200:
        print(f"[nav] metrology root_category_ids → {list(PROMOTE_IDS)}")
    else:
        exit_code = 2
        print(f"[nav] FAIL: {st} {body}", file=sys.stderr)

    # 3) Delete former hub if present and childless
    hub = by_id.get(FORMER_HUB_ID)
    if hub is None:
        print("[delete] hub id=7 already gone")
        return exit_code

    remaining_children = [c for c in cats if c.get("parent_id") == FORMER_HUB_ID]
    hub_products = int(hub.get("product_count") or 0)
    if remaining_children:
        exit_code = 2
        print(
            f"[delete] SKIP hub {FORMER_HUB_ID}: still has children "
            f"{[c.get('id') for c in remaining_children]}",
            file=sys.stderr,
        )
        return exit_code
    if hub_products > 0:
        exit_code = 2
        print(
            f"[delete] SKIP hub {FORMER_HUB_ID}: product_count={hub_products}",
            file=sys.stderr,
        )
        return exit_code

    if not args.step_up_token:
        exit_code = 2
        print(
            "[delete] hub ready but --step-up-token required for DELETE",
            file=sys.stderr,
        )
        return exit_code

    st, body = http_json("DELETE", f"{api}/categories/{FORMER_HUB_ID}", headers=auth)
    if st == 200:
        print(f"[delete] hub {FORMER_HUB_ID} «{hub.get('name')}» removed")
    else:
        exit_code = 2
        print(f"[delete] FAIL hub {FORMER_HUB_ID}: {st} {body}", file=sys.stderr)
        if st in (401, 403):
            print(
                "Hint: DELETE requires super_admin JWT + --step-up-token.",
                file=sys.stderr,
            )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
