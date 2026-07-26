#!/usr/bin/env python3
"""Promote Measurement L2 categories to L1 and retarget megamenu metrology roots.

Live reshape (ids from production seed):
  - Promote 56 «اندازه گیری دقیق», 81 «CNC اندازه گیری», 87 «اندازه گیری آزمایشگاهی»
    to parent_id=null (new L1 roots).
  - Replace nav-group `metrology` root_category_ids with [56, 81, 87]
    (preserves other groups).
  - Delete empty former hub root id=7 «اندازه گیری» once childless.

Dry-run by default. Apply modes:
  - API: --apply --confirm --token <jwt> [--step-up-token <tok>]
  - DB (preferred on VPS): --via-db --apply --confirm
    (run inside app container; no JWT / step-up needed)

Prerequisites:
  Deploy the selectable-leaf rule change (depth 2|3) BEFORE applying on live DB,
  so former L3→L2 product leaves remain valid product categories.

Usage:
  python scripts/promote_measurement_to_l1.py
  python scripts/promote_measurement_to_l1.py --api http://localhost:8000/api/v1
  python scripts/promote_measurement_to_l1.py --apply --confirm --token <jwt> \\
      --step-up-token <step-up>
  docker compose exec app python scripts/promote_measurement_to_l1.py \\
      --via-db --apply --confirm
"""

from __future__ import annotations

import argparse
import asyncio
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


async def apply_via_db(*, dry_run: bool) -> int:
    """Promote + remap + prune empty hub orphans using the app DB session."""
    from sqlalchemy import func, select

    from app.db.database import async_session_maker
    from app.db.models.content import MegamenuNavGroup
    from app.db.models.product import Category, Product

    async with async_session_maker() as db:
        cats = list((await db.execute(select(Category))).scalars().all())
        by_id = {c.id: c for c in cats}
        hub = by_id.get(FORMER_HUB_ID)
        missing = [cid for cid in PROMOTE_IDS if cid not in by_id]
        if missing:
            print(f"FAIL missing promote targets: {missing}", file=sys.stderr)
            return 1

        metro = (
            await db.execute(
                select(MegamenuNavGroup).where(MegamenuNavGroup.slug == METROLOGY_SLUG)
            )
        ).scalar_one_or_none()

        hub_children = [c for c in cats if c.parent_id == FORMER_HUB_ID]
        empty_dup_l1 = [
            c
            for c in cats
            if c.parent_id is None
            and c.id not in PROMOTE_IDS
            and c.id != FORMER_HUB_ID
            and any(
                n.replace("\u200c", "").replace(" ", "") in c.name.replace("\u200c", "").replace(" ", "")
                or c.name.replace("\u200c", "").replace(" ", "") in n.replace("\u200c", "").replace(" ", "")
                for n in ("اندازه گیری دقیق", "اندازه گیری آزمایشگاهی", "اندازه‌گیری دقیق", "اندازه‌گیری آزمایشگاهی")
            )
        ]

        plan = {
            "mode": "via-db",
            "dry_run": dry_run,
            "promote": [
                {
                    "id": cid,
                    "name": by_id[cid].name,
                    "from_parent_id": by_id[cid].parent_id,
                    "to_parent_id": None,
                }
                for cid in PROMOTE_IDS
            ],
            "nav_metrology": {
                "from": list(metro.root_category_ids) if metro else None,
                "to": list(PROMOTE_IDS),
            },
            "prune_hub_children": [
                {"id": c.id, "name": c.name} for c in hub_children
            ],
            "prune_empty_dup_l1": [
                {"id": c.id, "name": c.name} for c in empty_dup_l1
            ],
            "delete_hub": {
                "id": FORMER_HUB_ID,
                "present": hub is not None,
                "name": hub.name if hub else None,
            },
        }
        print(json.dumps(plan, ensure_ascii=False, indent=2))

        if dry_run:
            print("\n[dry-run] No DB writes. Use --via-db --apply --confirm", file=sys.stderr)
            return 0

        for cid in PROMOTE_IDS:
            row = by_id[cid]
            if row.parent_id is None:
                print(f"[promote] skip {cid}: already L1 ({row.name})")
                continue
            row.parent_id = None
            print(f"[promote] {cid}: {row.name} parent_id → null")

        if metro is None:
            print(f"[nav] FAIL: slug={METROLOGY_SLUG} not found", file=sys.stderr)
            return 2
        metro.root_category_ids = list(PROMOTE_IDS)
        print(f"[nav] metrology root_category_ids → {list(PROMOTE_IDS)}")

        await db.flush()

        async def _direct_product_count(category_id: int) -> int:
            return int(
                await db.scalar(
                    select(func.count())
                    .select_from(Product)
                    .where(
                        Product.category_id == category_id,
                        Product.deleted_at.is_(None),
                    )
                )
                or 0
            )

        async def _child_ids(category_id: int) -> list[int]:
            return list(
                (
                    await db.execute(
                        select(Category.id).where(Category.parent_id == category_id)
                    )
                ).scalars().all()
            )

        # Prune empty leaf children recreated under former hub (ids 181–185 style).
        for child in list(hub_children):
            kids = await _child_ids(child.id)
            products = await _direct_product_count(child.id)
            if kids:
                print(
                    f"[prune] SKIP hub-child {child.id}: still has children {kids}",
                    file=sys.stderr,
                )
                continue
            if products > 0:
                print(
                    f"[prune] SKIP hub-child {child.id}: {products} products",
                    file=sys.stderr,
                )
                continue
            await db.delete(child)
            print(f"[prune] hub-child {child.id} «{child.name}» removed")

        await db.flush()

        # Prune empty duplicate L1 roots (e.g. 179/180) that shadow promoted metrology.
        for dup in empty_dup_l1:
            kids = await _child_ids(dup.id)
            products = await _direct_product_count(dup.id)
            if kids or products > 0:
                print(
                    f"[prune] SKIP dup L1 {dup.id}: kids={kids} products={products}",
                    file=sys.stderr,
                )
                continue
            # Do not delete if referenced by any nav group.
            nav_rows = list((await db.execute(select(MegamenuNavGroup))).scalars().all())
            referenced = [
                g.slug
                for g in nav_rows
                if dup.id in list(g.root_category_ids or [])
            ]
            if referenced:
                print(
                    f"[prune] SKIP dup L1 {dup.id}: in nav groups {referenced}",
                    file=sys.stderr,
                )
                continue
            await db.delete(dup)
            print(f"[prune] dup L1 {dup.id} «{dup.name}» removed")

        await db.flush()

        hub = (
            await db.execute(select(Category).where(Category.id == FORMER_HUB_ID))
        ).scalar_one_or_none()
        if hub is None:
            print("[delete] hub id=7 already gone")
            await db.commit()
            return 0

        remaining = await _child_ids(FORMER_HUB_ID)
        direct_products = await _direct_product_count(FORMER_HUB_ID)
        if remaining:
            print(f"[delete] SKIP hub: still has children {remaining}", file=sys.stderr)
            await db.commit()
            return 2
        if direct_products > 0:
            print(
                f"[delete] SKIP hub: {direct_products} products still on category_id=7",
                file=sys.stderr,
            )
            await db.commit()
            return 2

        await db.delete(hub)
        print(f"[delete] hub {FORMER_HUB_ID} «{hub.name}» removed")
        await db.commit()
        return 0


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
        "--via-db",
        action="store_true",
        help="Apply via SQLAlchemy session (for docker compose exec on VPS)",
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

    if args.via_db:
        if args.apply and not args.confirm:
            print("--apply requires --confirm", file=sys.stderr)
            return 1
        return asyncio.run(apply_via_db(dry_run=not args.apply))

    api = args.api.rstrip("/")
    st, cats_resp = http_json("GET", f"{api}/categories/")
    if st != 200:
        print(f"FAIL list categories: {st} {cats_resp}", file=sys.stderr)
        return 1

    cats: list[dict[str, Any]] = cats_resp.get("data") or []
    by_id = {int(c["id"]): c for c in cats if c.get("id") is not None}

    hub = by_id.get(FORMER_HUB_ID)
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
            "note": "Delete only after promote makes hub childless; count direct products only",
        },
        "notes": [
            "Deploy selectable depth 2|3 code before --apply on production.",
            "Products stay on former L3 leaves (become depth-2 after promote).",
            "Megamenu label «اندازه‌گیری» remains; it is not an L1 taxonomy root.",
            "Preferred on VPS: docker compose exec app python scripts/promote_measurement_to_l1.py "
            "--via-db --apply --confirm",
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
            "\n[dry-run] No changes written. Use --apply --confirm [--via-db|--token …]",
            file=sys.stderr,
        )
        return 0

    if not args.confirm:
        print("--apply requires --confirm", file=sys.stderr)
        return 1
    if not args.token:
        print("--apply requires --token (or use --via-db)", file=sys.stderr)
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
    # API product_count is subtree-aggregated; only block on direct products.
    # Prefer --via-db for accurate direct-product checks.
    if remaining_children:
        exit_code = 2
        print(
            f"[delete] SKIP hub {FORMER_HUB_ID}: still has children "
            f"{[c.get('id') for c in remaining_children]}",
            file=sys.stderr,
        )
        return exit_code

    if not args.step_up_token:
        exit_code = 2
        print(
            "[delete] hub ready but --step-up-token required for DELETE "
            "(or use --via-db)",
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
                "Hint: DELETE requires super_admin JWT + --step-up-token, or --via-db.",
                file=sys.stderr,
            )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
