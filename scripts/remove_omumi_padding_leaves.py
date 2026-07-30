#!/usr/bin/env python3
"""Remove padding «عمومی» category leaves and move products one layer up.

Matches storefront megamenu collapse (`isPaddingLeafName`): exact «عمومی»
or «… — عمومی» (dash variants), with Arabic Yeh/Kaf normalized to Persian.

Preferred apply path is --via-db (atomic reparent + delete). After this PR,
DELETE /categories/{id}?target_category_id={parent} also works when the
node is the sole child (parent becomes a selectable leaf).

Safety skips (reported, never forced):
  - Node has children
  - No parent (L1 named عمومی)
  - Parent depth < 2 (L1 cannot hold products)
  - Parent has other siblings remaining (parent stays non-leaf)
  - Does not match padding name pattern (e.g. «ابزار دستی عمومی»)

Does NOT touch price or stock.

Dry-run by default. Apply:
  docker compose exec -T app \\
    python scripts/remove_omumi_padding_leaves.py --via-db --apply --confirm

Usage:
  python scripts/remove_omumi_padding_leaves.py
  python scripts/remove_omumi_padding_leaves.py --api http://127.0.0.1:8000/api/v1
  # Category B (explicit production — never the default):
  python scripts/remove_omumi_padding_leaves.py --api https://api.karzartools.com/api/v1
  python scripts/remove_omumi_padding_leaves.py --via-db
  python scripts/remove_omumi_padding_leaves.py --via-db --apply --confirm
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.category_padding import plan_omumi_removals  # noqa: E402


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

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


async def apply_via_db(*, dry_run: bool) -> int:
    from sqlalchemy import func, select

    from app.crud.category import reassign_products_category
    from app.db.database import async_session_maker
    from app.db.models.product import Category, Product
    from app.utils.category_depth import (
        build_category_metadata,
        is_selectable_product_category,
    )

    async with async_session_maker() as db:
        cats_orm = list((await db.execute(select(Category))).scalars().all())
        meta = build_category_metadata(cats_orm)

        async def _direct_count(category_id: int) -> int:
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

        flat: list[dict[str, Any]] = []
        direct_counts: dict[int, int] = {}
        for c in cats_orm:
            m = meta[c.id]
            direct_counts[c.id] = await _direct_count(c.id)
            flat.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "parent_id": c.parent_id,
                    "depth": m["depth"],
                    "is_leaf": m["is_leaf"],
                    "product_count": direct_counts[c.id],
                    "breadcrumb": m["breadcrumb"],
                }
            )

        plan = plan_omumi_removals(flat, direct_product_counts=direct_counts)
        plan["mode"] = "via-db"
        plan["dry_run"] = dry_run
        print(json.dumps(plan, ensure_ascii=False, indent=2))

        if dry_run:
            print(
                "\n[dry-run] No DB writes. Use --via-db --apply --confirm",
                file=sys.stderr,
            )
            return 0

        by_orm = {c.id: c for c in cats_orm}
        moved_total = 0
        deleted = 0

        for row in plan["moves"]:
            cid = int(row["id"])
            pid = int(row["parent_id"])
            leaf = by_orm.get(cid)
            parent = by_orm.get(pid)
            if leaf is None or parent is None:
                print(f"[skip] missing rows id={cid} parent={pid}", file=sys.stderr)
                continue

            child_ids = list(
                (
                    await db.execute(
                        select(Category.id).where(Category.parent_id == cid)
                    )
                )
                .scalars()
                .all()
            )
            if child_ids:
                print(f"[skip] {cid} gained children {child_ids}", file=sys.stderr)
                continue

            sibs = list(
                (
                    await db.execute(
                        select(Category.id).where(Category.parent_id == pid)
                    )
                )
                .scalars()
                .all()
            )
            if set(sibs) != {cid}:
                print(
                    f"[skip] {cid} no longer sole child of {pid}: {sibs}",
                    file=sys.stderr,
                )
                continue

            n = await _direct_count(cid)
            moved = await reassign_products_category(db, cid, pid) if n else 0
            moved_total += moved

            await db.delete(leaf)
            deleted += 1
            print(
                f"[move+delete] {cid} «{row['name']}» → parent {pid} "
                f"«{row['parent_name']}» products={moved}"
            )

        await db.flush()

        refreshed = list((await db.execute(select(Category))).scalars().all())
        refreshed_meta = build_category_metadata(refreshed)
        bad: list[str] = []
        for row in plan["moves"]:
            pid = int(row["parent_id"])
            if pid not in refreshed_meta:
                continue
            m = refreshed_meta[pid]
            pc = await _direct_count(pid)
            if pc > 0 and not is_selectable_product_category(m):
                bad.append(
                    f"parent {pid} has {pc} products but not selectable "
                    f"(depth={m['depth']} leaf={m['is_leaf']})"
                )

        if bad:
            await db.rollback()
            print("FAIL post-condition; rolled back:", file=sys.stderr)
            for line in bad:
                print(f"  {line}", file=sys.stderr)
            return 2

        await db.commit()
        summary = {
            "deleted": deleted,
            "products_moved": moved_total,
            "skipped": plan["skip_count"],
            "near_misses": len(plan["near_misses"]),
        }
        print(json.dumps({"applied": summary}, ensure_ascii=False, indent=2))
        return 0


def report_via_api(api: str) -> int:
    st, cats_resp = http_json("GET", f"{api.rstrip('/')}/categories/")
    if st != 200:
        print(f"FAIL list categories: {st} {cats_resp}", file=sys.stderr)
        return 1

    cats: list[dict[str, Any]] = cats_resp.get("data") or []
    plan = plan_omumi_removals(cats)
    plan["mode"] = "api-report"
    plan["dry_run"] = True
    plan["notes"] = [
        "API product_count is subtree-aggregated; for sole-child L3 padding "
        "leaves it matches direct product placement.",
        "Preferred apply: --via-db --apply --confirm inside the app container.",
        "After deploy, DELETE with target_category_id=parent also works for "
        "sole children (parent becomes selectable).",
        "Price/stock fields are never written.",
    ]
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    print(
        "\n[dry-run] Report only. Apply with --via-db --apply --confirm "
        "inside the app container (or workflow_dispatch Remove Omumi Padding Leaves).",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api",
        default="http://127.0.0.1:8000/api/v1",
        help="Public API base for report-only dry-run",
    )
    parser.add_argument(
        "--via-db",
        action="store_true",
        help="Plan/apply via SQLAlchemy session (docker compose exec on VPS)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply moves+deletes (default dry-run); requires --via-db --confirm",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required safety flag alongside --apply",
    )
    args = parser.parse_args()

    if args.apply and not args.via_db:
        print(
            "--apply requires --via-db (use workflow or docker compose on VPS)",
            file=sys.stderr,
        )
        return 1
    if args.apply and not args.confirm:
        print("--apply requires --confirm", file=sys.stderr)
        return 1

    if args.via_db:
        return asyncio.run(apply_via_db(dry_run=not args.apply))

    return report_via_api(args.api)


if __name__ == "__main__":
    raise SystemExit(main())
