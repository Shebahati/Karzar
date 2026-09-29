#!/usr/bin/env python3
"""Read-only reconciliation of Hesabfa item activation for Karzar products.

Default mode is dry-run. It may read the local database and Hesabfa
``item/getItems`` (or a JSON snapshot of that read). It never calls
``item/save`` and never commits database writes.

Population is every site product with ``deleted_at IS NULL``. Rows are not
filtered by ``is_active``, ``is_available``, price, images, or sellability.

``--apply`` is refused with BLOCKED_PENDING_API_CONFIRMATION. The refusal
stands even when ``--confirm-production-write``, ``KARZAR_ALLOW_PRODUCTION_WRITE=1``,
and ``KARZAR_INGESTION_CATEGORY=B`` are all present, because item/save update
semantics are not proven in this repository.

Examples::

    python scripts/hesabfa_product_activation_reconcile.py --dry-run --batch-size 250
    python scripts/hesabfa_product_activation_reconcile.py --dry-run --resume
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.hesabfa.activation_reconcile import (  # noqa: E402
    ACTIVATION_APPLY_STATUS,
    ActivationApplyBlocked,
    DryRunHesabfaClient,
    DryRunSession,
    MappingView,
    ReconciliationRow,
    SiteProductView,
    assert_dry_run_safe,
    classify_catalog,
    load_remote_items,
    refuse_activation_apply,
    rows_from_csv,
    summarize,
    write_artifacts,
)

DEFAULT_OUTPUT = ROOT / "artifacts" / "hesabfa_product_activation"
CHECKPOINT_NAME = "checkpoint.json"


def _load_json(path: Path) -> Any:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    return data


def _products_from_snapshot(path: Path) -> list[SiteProductView]:
    raw = _load_json(path)
    if not isinstance(raw, list):
        raise SystemExit(f"products snapshot must be a list: {path}")
    products: list[SiteProductView] = []
    for item in raw:
        products.append(
            SiteProductView(
                id=int(item["id"]),
                sku=str(item["sku"]),
                is_active=bool(item["is_active"]),
                is_available=bool(item["is_available"]),
                price_present=bool(item["price_present"]),
            )
        )
    return products


def _mappings_from_snapshot(path: Path | None) -> list[MappingView]:
    if path is None:
        return []
    raw = _load_json(path)
    if not isinstance(raw, list):
        raise SystemExit(f"mappings snapshot must be a list: {path}")
    return [
        MappingView(
            product_id=int(item["product_id"]),
            sku=str(item["sku"]),
            hesabfa_code=str(item["hesabfa_code"]),
            hesabfa_product_code=item.get("hesabfa_product_code"),
        )
        for item in raw
    ]


def _remote_from_snapshot(path: Path) -> list[dict[str, Any]]:
    raw = _load_json(path)
    if not isinstance(raw, list):
        raise SystemExit(f"remote snapshot must be a list: {path}")
    return [dict(item) for item in raw]


def _row_from_csv(data: dict[str, str]) -> ReconciliationRow:
    active_text = data.get("hesabfa_active_current") or ""
    active: bool | None
    if active_text == "true":
        active = True
    elif active_text == "false":
        active = False
    else:
        active = None
    return ReconciliationRow(
        site_product_id=int(data["site_product_id"]),
        sku=data["sku"],
        site_is_active=data["site_is_active"] == "true",
        site_is_available=data["site_is_available"] == "true",
        site_price_present=data["site_price_present"] == "true",
        hesabfa_mapping_present=data["hesabfa_mapping_present"] == "true",
        hesabfa_item_present=data["hesabfa_item_present"] == "true",
        hesabfa_code=data.get("hesabfa_code") or "",
        hesabfa_product_code=data.get("hesabfa_product_code") or "",
        hesabfa_active_current=active,
        desired_hesabfa_active=data["desired_hesabfa_active"] == "true",
        action=data["action"],
        reason=data.get("reason") or "",
        price_risk=(data.get("price_risk") or "") == "true",
    )


def _read_checkpoint(path: Path) -> int:
    if not path.is_file():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    return int(payload.get("last_product_id") or 0)


def _write_checkpoint(path: Path, last_product_id: int) -> None:
    path.write_text(
        json.dumps(
            {
                "last_product_id": last_product_id,
                "DRY_RUN": True,
                "REMOTE_WRITES": 0,
                "DATABASE_WRITES": 0,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _existing_rows(csv_path: Path) -> list[ReconciliationRow]:
    if not csv_path.is_file():
        return []
    return [_row_from_csv(row) for row in rows_from_csv(csv_path)]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read-only classification (this is the default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Refused. Activation writes are BLOCKED_PENDING_API_CONFIRMATION",
    )
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Required future flag for APPLY. Not sufficient while APPLY is blocked",
    )
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--after-id", type=int, default=0)
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Stop after this many batches (default: scan until exhausted)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue after checkpoint.json last_product_id",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--products-snapshot", type=Path, default=None)
    parser.add_argument("--mappings-snapshot", type=Path, default=None)
    parser.add_argument("--remote-snapshot", type=Path, default=None)
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args(argv)
    if args.batch_size < 1:
        parser.error("--batch-size must be >= 1")
    if args.page_size < 1:
        parser.error("--page-size must be >= 1")
    if args.after_id < 0:
        parser.error("--after-id must be >= 0")
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run are mutually exclusive")
    return args


def _refuse_apply(args: argparse.Namespace) -> int | None:
    if not args.apply:
        return None
    missing: list[str] = []
    if not args.confirm_production_write:
        missing.append("--confirm-production-write")
    if os.getenv("KARZAR_ALLOW_PRODUCTION_WRITE", "").strip() != "1":
        missing.append("KARZAR_ALLOW_PRODUCTION_WRITE=1")
    if os.getenv("KARZAR_INGESTION_CATEGORY", "").strip().upper() != "B":
        missing.append("KARZAR_INGESTION_CATEGORY=B")
    if missing:
        print(
            "FATAL: activation apply refused; missing " + "; ".join(missing),
            file=sys.stderr,
        )
        return 2
    try:
        refuse_activation_apply()
    except ActivationApplyBlocked as exc:
        print(ACTIVATION_APPLY_STATUS, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 3
    print("FATAL: apply returned without blocking", file=sys.stderr)
    return 3


async def _load_live_remote(page_size: int) -> tuple[Any, DryRunHesabfaClient]:
    from app.services.hesabfa.client import get_hesabfa_client, hesabfa_integration_active

    if not hesabfa_integration_active():
        raise SystemExit(
            "FATAL: Hesabfa credentials are not configured. Refusing to treat "
            "every product as remote-missing. Pass --remote-snapshot for an "
            "offline read-only index."
        )
    client = DryRunHesabfaClient(get_hesabfa_client())
    page = await load_remote_items(client, page_size=page_size)
    return page, client


async def _scan_database(
    *,
    after_id: int,
    batch_size: int,
    max_batches: int | None,
    remote_items: list[dict[str, Any]],
    prior_rows: list[ReconciliationRow],
    output: Path,
) -> tuple[list[ReconciliationRow], int, int, dict[str, Any]]:
    from app.db.database import async_session_maker
    from app.services.hesabfa.activation_reconcile import (
        enforce_database_read_only,
        fetch_catalog_snapshot,
        release_database_read_only,
    )

    rows = list(prior_rows)
    seen = {row.site_product_id for row in rows}
    remote_writes = 0
    database_writes = 0
    async with async_session_maker() as session:
        guard = DryRunSession(session)
        mode = await enforce_database_read_only(guard)
        snapshot = await fetch_catalog_snapshot(guard)
        database_writes = guard.database_writes
        await release_database_read_only(guard, mode)
    products = snapshot["products"]
    mappings = snapshot["mappings"]
    duplicate_skus = snapshot["duplicate_skus"]
    population = int(snapshot["baseline"]["TOTAL_NON_DELETED"])
    if population != len(products):
        raise RuntimeError("TOTAL_SITE_NON_DELETED does not match the product row count")
    pending = [product for product in products if product.id > after_id]
    batches = 0
    offset = 0
    while offset < len(pending) and (max_batches is None or batches < max_batches):
        chunk = pending[offset : offset + batch_size]
        offset += batch_size
        fresh = [product for product in chunk if product.id not in seen]
        classified = classify_catalog(
            fresh,
            mappings,
            remote_items,
            duplicate_skus=duplicate_skus,
        )
        rows.extend(classified)
        seen.update(row.site_product_id for row in classified)
        batches += 1
        if chunk:
            _write_checkpoint(output / CHECKPOINT_NAME, chunk[-1].id)
        summary = summarize(
            rows,
            population_total=population,
            remote_writes=remote_writes,
            database_writes=database_writes,
        )
        summary["CATALOG_BASELINE"] = snapshot["baseline"]
        summary["DATABASE_READ_ONLY"] = mode
        assert_dry_run_safe(remote_writes=remote_writes, database_writes=database_writes)
        write_artifacts(output, rows, summary)
    if not pending and not rows:
        summary = summarize(
            [],
            population_total=population,
            remote_writes=0,
            database_writes=database_writes,
        )
        summary["CATALOG_BASELINE"] = snapshot["baseline"]
        summary["DATABASE_READ_ONLY"] = mode
        write_artifacts(output, rows, summary)
    return rows, population, database_writes, snapshot["baseline"]


def _scan_snapshots(
    *,
    products: list[SiteProductView],
    mappings: list[MappingView],
    remote_items: list[dict[str, Any]],
    after_id: int,
    batch_size: int,
    max_batches: int | None,
    prior_rows: list[ReconciliationRow],
    output: Path,
) -> tuple[list[ReconciliationRow], int]:
    from app.services.hesabfa.mapping import _normalize_sku

    pending = [product for product in sorted(products, key=lambda row: row.id) if product.id > after_id]
    rows = list(prior_rows)
    seen = {row.site_product_id for row in rows}
    population = len(products)
    sku_counts: dict[str, int] = defaultdict(int)
    for product in products:
        key = _normalize_sku(product.sku)
        if key:
            sku_counts[key] += 1
    duplicate_skus = {key for key, count in sku_counts.items() if count > 1}
    batches = 0
    offset = 0
    while offset < len(pending) and (max_batches is None or batches < max_batches):
        chunk = pending[offset : offset + batch_size]
        offset += batch_size
        fresh = [product for product in chunk if product.id not in seen]
        classified = classify_catalog(
            fresh,
            mappings,
            remote_items,
            duplicate_skus=duplicate_skus,
        )
        rows.extend(classified)
        seen.update(row.site_product_id for row in classified)
        batches += 1
        if chunk:
            _write_checkpoint(output / CHECKPOINT_NAME, chunk[-1].id)
        summary = summarize(
            rows,
            population_total=population,
            remote_writes=0,
            database_writes=0,
        )
        write_artifacts(output, rows, summary)
    if not pending and not rows:
        summary = summarize([], population_total=population, remote_writes=0, database_writes=0)
        write_artifacts(output, [], summary)
    return rows, population


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    blocked = _refuse_apply(args)
    if blocked is not None:
        return blocked

    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    after_id = args.after_id
    if args.resume:
        after_id = max(after_id, _read_checkpoint(output / CHECKPOINT_NAME))
    elif after_id == 0 and not args.resume:
        # A fresh full scan replaces the previous report.
        for name in (
            "reconciliation.csv",
            "errors.csv",
            "ambiguous.csv",
            "summary.json",
            "sha256sums.txt",
            CHECKPOINT_NAME,
        ):
            path = output / name
            if path.exists():
                path.unlink()

    prior: list[ReconciliationRow] = []
    if after_id > 0:
        prior = [row for row in _existing_rows(output / "reconciliation.csv") if row.site_product_id <= after_id]

    if args.products_snapshot is not None:
        if args.remote_snapshot is None:
            print(
                "FATAL: --products-snapshot requires --remote-snapshot "
                "(refusing to classify remote items as missing).",
                file=sys.stderr,
            )
            return 2
        products = _products_from_snapshot(args.products_snapshot)
        mappings = _mappings_from_snapshot(args.mappings_snapshot)
        remote_items = _remote_from_snapshot(args.remote_snapshot)
        rows, population = _scan_snapshots(
            products=products,
            mappings=mappings,
            remote_items=remote_items,
            after_id=after_id,
            batch_size=args.batch_size,
            max_batches=args.max_batches,
            prior_rows=prior,
            output=output,
        )
        remote_writes = 0
        database_writes = 0
        live_extra: dict[str, Any] = {}
    else:
        remote_page, client = asyncio.run(_load_live_remote(args.page_size))
        remote_items = list(remote_page.items)
        rows, population, database_writes, baseline = asyncio.run(
            _scan_database(
                after_id=after_id,
                batch_size=args.batch_size,
                max_batches=args.max_batches,
                remote_items=remote_items,
                prior_rows=prior,
                output=output,
            )
        )
        remote_writes = client.remote_writes
        if int(baseline["TOTAL_NON_DELETED"]) != population:
            raise SystemExit("FATAL: reconciliation population disagrees with the database count")
        from app.services.hesabfa.activation_reconcile import remote_inventory_stats

        live_extra = {
            "CATALOG_BASELINE": baseline,
            "HESABFA_REPORTED_TOTAL": remote_page.reported_total,
            "HESABFA_ITEMS_FETCHED": len(remote_page.items),
            "HESABFA_PAGES_FETCHED": remote_page.pages_fetched,
            "HESABFA_INDEX": remote_inventory_stats(remote_page.items),
            "PAGINATION_COMPLETE": len(remote_page.items) == remote_page.reported_total,
            "LAST_PRODUCT_ID": max((row.site_product_id for row in rows), default=None),
        }

    assert_dry_run_safe(remote_writes=remote_writes, database_writes=database_writes)
    summary = summarize(
        rows,
        population_total=population,
        remote_writes=remote_writes,
        database_writes=database_writes,
    )
    summary.update(live_extra)
    write_artifacts(output, rows, summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
