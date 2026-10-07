#!/usr/bin/env python3
"""Apply PROVEN INSIZE identity-alias price updates (explicit registry only).

Precedence remains: exact → workbook-trailing-A → identity alias → unmatched.
Mutates base_price only. Never mutates SKU / manufacturer_code.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from insize_sales_activation_lib import (  # noqa: E402
    DEFAULT_INSIZE_IDENTITY_ALIAS_CSV,
    INSIZE_BRAND_ID,
    PilotGateError,
    final_toman_from_usd,
    load_insize_identity_aliases,
    load_workbook_catalog,
    match_exact,
    match_insize_identity_alias,
    match_insize_workbook_terminal_a_alias,
    normalize_sku,
    valid_workbook_price,
    workbook_sha256,
    write_recovery_snapshot,
)

EXPECTED_WORKBOOK_SHA256 = (
    "65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a"
)
CANARY_SKU = "1106-1002"
CANARY_USD = Decimal("526.8")
CHANGE_REASON = (
    "INSIZE proven identity-alias price reconcile owner-authorized 2026-10-06"
)
DEFAULT_OUT = ROOT / "audit" / "insize-price-20-four-likely"
MATCH_TYPE = "INSIZE_IDENTITY_ALIAS"
TARGET_SITE_SKUS = frozenset(
    {
        "0213-500A",
        "6297-1A",
        "7527-1D",
        "7527-2D",
    }
)


@dataclass
class AliasUpdateRow:
    product_id: int
    sku: str
    workbook_code: str
    mapping_rule: str
    evidence: str
    usd_price: Decimal
    rate: Decimal
    new_base_price: Decimal
    current_base_price: Decimal | None


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _csv_write(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _require_production_guards(apply: bool) -> None:
    if not apply:
        return
    if os.getenv("KARZAR_ALLOW_PRODUCTION_WRITE", "").strip() != "1":
        raise PilotGateError("KARZAR_ALLOW_PRODUCTION_WRITE=1 required for --apply")
    if os.getenv("KARZAR_INGESTION_CATEGORY", "").strip().upper() != "B":
        raise PilotGateError("KARZAR_INGESTION_CATEGORY=B required for --apply")


def assert_workbook(path: Path):
    sha = workbook_sha256(path)
    if sha.lower() != EXPECTED_WORKBOOK_SHA256.lower():
        raise PilotGateError(f"workbook SHA mismatch: {sha}")
    catalog = load_workbook_catalog(path)
    if catalog.rate != Decimal("2500000"):
        raise PilotGateError(f"K6 mismatch: {catalog.rate}")
    canary = catalog.by_code.get(normalize_sku(CANARY_SKU))
    if canary is None or canary.usd_price != CANARY_USD:
        raise PilotGateError("canary mismatch")
    return sha, catalog


def _async_engine_and_sessionmaker():
    from app.core.config import settings
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(settings.ASYNC_DATABASE_URI)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _load_insize_products() -> list[Any]:
    async def _run():
        from app.db.models.product import Product
        from sqlalchemy import select

        engine, sf = _async_engine_and_sessionmaker()
        try:
            async with sf() as session:
                r = await session.execute(
                    select(Product).where(
                        Product.brand_id == INSIZE_BRAND_ID,
                        Product.deleted_at.is_(None),
                    )
                )
                return list(r.scalars().all())
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def wave_health(catalog, products) -> dict[str, int]:
    by_code = catalog.by_code
    sku_groups: dict[str, list] = defaultdict(list)
    for p in products:
        sku_groups[normalize_sku(p.sku)].append(p)
    insize_skus = frozenset(sku_groups)
    exact_ok = exact_need = trailing_ok = trailing_need = 0
    for p in products:
        sku = normalize_sku(p.sku)
        if not sku or len(sku_groups[sku]) > 1:
            continue
        m = match_exact(p.sku, by_code)
        if m.method == "exact" and m.workbook_code:
            wb = by_code[normalize_sku(m.workbook_code)]
            cls, _, toman = valid_workbook_price(wb.usd_price, catalog.rate)
            if cls != "VALID_WORKBOOK_PRICE" or toman is None:
                continue
            cur = None if p.base_price is None else Decimal(str(p.base_price))
            if cur == toman:
                exact_ok += 1
            else:
                exact_need += 1
            continue
        am = match_insize_workbook_terminal_a_alias(
            p.sku, by_code, insize_db_skus=insize_skus, brand_is_insize=True
        )
        if am.method == "WORKBOOK_TRAILING_A_ALIAS" and am.workbook_code:
            wb = by_code[normalize_sku(am.workbook_code)]
            cls, _, toman = valid_workbook_price(wb.usd_price, catalog.rate)
            if cls != "VALID_WORKBOOK_PRICE" or toman is None:
                continue
            cur = None if p.base_price is None else Decimal(str(p.base_price))
            if cur == toman:
                trailing_ok += 1
            else:
                trailing_need += 1
    return {
        "exact_ok": exact_ok,
        "exact_need": exact_need,
        "trailing_ok": trailing_ok,
        "trailing_need": trailing_need,
    }


def build_proven_cohort(catalog, products, aliases) -> dict[str, Any]:
    by_code = catalog.by_code
    sku_groups: dict[str, list] = defaultdict(list)
    for p in products:
        sku_groups[normalize_sku(p.sku)].append(p)
    insize_skus = frozenset(k for k in sku_groups if k)

    proof_rows = []
    updates: list[AliasUpdateRow] = []
    already = []
    rejected = []

    for site in sorted(TARGET_SITE_SKUS):
        alias = aliases.get(normalize_sku(site))
        group = sku_groups.get(normalize_sku(site), [])
        if not alias:
            rejected.append({"site_sku": site, "reason": "ALIAS_NOT_IN_REGISTRY"})
            continue
        if len(group) != 1:
            rejected.append(
                {
                    "site_sku": site,
                    "reason": "SITE_SKU_NOT_UNIQUE_OR_MISSING",
                    "count": len(group),
                }
            )
            continue
        product = group[0]

        # Precedence: exact / trailing-A must not be stolen
        exact = match_exact(product.sku, by_code)
        if exact.method == "exact":
            rejected.append({"site_sku": site, "reason": "EXACT_MATCH_WINS"})
            continue
        trailing = match_insize_workbook_terminal_a_alias(
            product.sku, by_code, insize_db_skus=insize_skus, brand_is_insize=True
        )
        if trailing.method == "WORKBOOK_TRAILING_A_ALIAS":
            rejected.append({"site_sku": site, "reason": "TRAILING_A_WINS"})
            continue

        matched = match_insize_identity_alias(
            product.sku,
            by_code,
            aliases=aliases,
            insize_db_skus=insize_skus,
            brand_is_insize=True,
        )
        if matched.method != "INSIZE_IDENTITY_ALIAS" or not matched.workbook_code:
            rejected.append(
                {
                    "site_sku": site,
                    "reason": matched.method,
                    "candidates": matched.candidates,
                }
            )
            continue

        wb = by_code[normalize_sku(matched.workbook_code)]
        price_class, _, toman = valid_workbook_price(wb.usd_price, catalog.rate)
        if price_class != "VALID_WORKBOOK_PRICE" or toman is None:
            rejected.append(
                {
                    "site_sku": site,
                    "reason": "EXCLUDED_NON_NUMERIC",
                    "class": price_class,
                }
            )
            continue

        cur = None if product.base_price is None else Decimal(str(product.base_price))
        row = {
            "product_id": int(product.id),
            "site_SKU": product.sku,
            "workbook_CODE": wb.code,
            "mapping_rule": MATCH_TYPE,
            "USD": str(wb.usd_price),
            "K6": str(catalog.rate),
            "current_price": None if cur is None else str(cur),
            "target_price": str(toman),
            "delta": str(toman if cur is None else toman - cur),
            "identity_evidence": alias.evidence_refs,
            "reason": alias.reason,
            "verdict": "PROVEN",
        }
        proof_rows.append(row)
        if cur == toman:
            already.append(row)
        else:
            updates.append(
                AliasUpdateRow(
                    product_id=int(product.id),
                    sku=str(product.sku),
                    workbook_code=str(wb.code),
                    mapping_rule=MATCH_TYPE,
                    evidence=alias.evidence_refs,
                    usd_price=wb.usd_price,
                    rate=catalog.rate,
                    new_base_price=toman,
                    current_base_price=cur,
                )
            )

    return {
        "proof_rows": proof_rows,
        "updates": updates,
        "already": already,
        "rejected": rejected,
    }


async def _apply_async(updates: list[AliasUpdateRow], recovery_path: Path) -> dict[str, Any]:
    from app.db.models.platform import ProductChangeLog
    from app.db.models.product import Product
    from sqlalchemy import select

    engine, sf = _async_engine_and_sessionmaker()
    try:
        ids = [u.product_id for u in updates]
        recovery_rows = []
        async with sf() as session:
            async with session.begin():
                result = await session.execute(
                    select(Product)
                    .where(Product.id.in_(ids), Product.brand_id == INSIZE_BRAND_ID)
                    .with_for_update()
                )
                by_id = {int(p.id): p for p in result.scalars().all()}
                if len(by_id) != len(ids):
                    raise PilotGateError("FOR UPDATE count mismatch")
                for u in updates:
                    p = by_id[u.product_id]
                    if normalize_sku(p.sku) != normalize_sku(u.sku):
                        raise PilotGateError(f"SKU drift id={u.product_id}")
                    recovery_rows.append(
                        {
                            "product_id": u.product_id,
                            "sku": u.sku,
                            "workbook_CODE": u.workbook_code,
                            "old_base_price": None
                            if p.base_price is None
                            else str(p.base_price),
                            "target_base_price": str(u.new_base_price),
                            "identity_mapping_type": MATCH_TYPE,
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                    )
                if len(recovery_rows) != len(updates):
                    raise PilotGateError("ROLLBACK_ROWS != INTENDED_UPDATE_ROWS")
                snap = write_recovery_snapshot(recovery_path, recovery_rows)
                updated = 0
                for u in updates:
                    p = by_id[u.product_id]
                    old = p.base_price
                    old_str = None if old is None else str(old)
                    if old is not None and Decimal(str(old)) == u.new_base_price:
                        continue
                    p.base_price = u.new_base_price
                    session.add(
                        ProductChangeLog(
                            product_id=u.product_id,
                            field_name="base_price",
                            old_value=old_str,
                            new_value=str(u.new_base_price),
                            reason=CHANGE_REASON,
                            actor_user_id=None,
                        )
                    )
                    updated += 1
        return {
            "updated": updated,
            "rollback_rows": len(recovery_rows),
            "recovery_snapshot_path": str(recovery_path),
            "recovery_snapshot_sha256": snap,
        }
    finally:
        await engine.dispose()


def sample_api(product_ids: list[int]) -> list[dict[str, Any]]:
    import urllib.request

    out = []
    for pid in product_ids[:8]:
        req = urllib.request.Request(
            f"http://127.0.0.1:8000/api/v1/products/{pid}",
            headers={
                "Host": "api.karzartools.com",
                "X-Forwarded-Proto": "https",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
            data = body.get("data", body) if isinstance(body, dict) else body
            out.append(
                {
                    "product_id": pid,
                    "http": 200,
                    "sku": data.get("sku"),
                    "base_price": data.get("base_price"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            out.append({"product_id": pid, "error": str(exc)})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--alias-csv", type=Path, default=DEFAULT_INSIZE_IDENTITY_ALIAS_CSV)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm-production-write", action="store_true")
    ap.add_argument("--recovery-snapshot-path", type=Path, default=None)
    args = ap.parse_args(argv)

    sha, catalog = assert_workbook(args.xlsx)
    aliases = load_insize_identity_aliases(args.alias_csv, proven_only=True)
    missing = [s for s in TARGET_SITE_SKUS if normalize_sku(s) not in aliases]
    if missing:
        raise PilotGateError(f"missing PROVEN aliases: {missing}")

    products = _load_insize_products()
    health = wave_health(catalog, products)
    if health["exact_need"] != 0 or health["trailing_need"] != 0:
        report = {
            "STATUS": "BLOCKED_PRIOR_COHORT_DRIFT",
            "workbook_sha256": sha,
            "wave_health": health,
        }
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 11

    cohort = build_proven_cohort(catalog, products, aliases)
    dry_fields = [
        "product_id",
        "site_SKU",
        "workbook_CODE",
        "mapping_rule",
        "USD",
        "K6",
        "current_price",
        "target_price",
        "delta",
        "identity_evidence",
        "reason",
        "verdict",
    ]
    _csv_write(args.out_dir / "FOUR_LIKELY_PROOF_MATRIX.csv", dry_fields, cohort["proof_rows"])
    dry_rows = [
            {
                "product_id": u.product_id,
                "site_SKU": u.sku,
                "workbook_CODE": u.workbook_code,
                "mapping_rule": u.mapping_rule,
                "USD": str(u.usd_price),
                "K6": str(u.rate),
                "current_price": None
                if u.current_base_price is None
                else str(u.current_base_price),
                "target_price": str(u.new_base_price),
                "delta": str(
                    u.new_base_price
                    if u.current_base_price is None
                    else u.new_base_price - u.current_base_price
                ),
                "identity_evidence": u.evidence,
                "reason": "",
                "verdict": "PROVEN",
            }
            for u in cohort["updates"]
        ]
    # Preserve a prior non-empty dry-run when this pass has zero updates (idempotent rerun).
    dry_path = args.out_dir / "FOUR_LIKELY_PRICE_DRY_RUN.csv"
    if dry_rows or not dry_path.is_file() or dry_path.stat().st_size < 32:
        _csv_write(dry_path, dry_fields, dry_rows)

    report: dict[str, Any] = {
        "STATUS": "READY_TO_APPLY" if cohort["updates"] else "DRY_RUN_NO_UPDATES",
        "workbook_sha256": sha,
        "K6_rate": str(catalog.rate),
        "alias_csv": str(args.alias_csv),
        "wave_health": health,
        "canary": {
            "sku": CANARY_SKU,
            "usd": str(CANARY_USD),
            "toman": str(final_toman_from_usd(CANARY_USD, catalog.rate)),
        },
        "proof_summary": {
            "PROVEN": len(cohort["proof_rows"]),
            "already_correct": len(cohort["already"]),
            "requiring_update": len(cohort["updates"]),
            "rejected": cohort["rejected"],
        },
    }
    _json_write(args.out_dir / "SYNC_REPORT.json", report)

    if not args.apply:
        print(json.dumps(report, ensure_ascii=False))
        return 0

    if not args.confirm_production_write:
        print("FATAL: --apply requires --confirm-production-write", file=sys.stderr)
        return 2
    _require_production_guards(True)

    recovery = args.recovery_snapshot_path or (
        args.out_dir
        / f"RECOVERY_FOUR_LIKELY_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    apply_result = asyncio.run(_apply_async(cohort["updates"], recovery))
    recovery_payload = json.loads(Path(recovery).read_text(encoding="utf-8"))
    _csv_write(
        args.out_dir / "FOUR_LIKELY_ROLLBACK.csv",
        [
            "product_id",
            "sku",
            "workbook_CODE",
            "old_base_price",
            "target_base_price",
            "identity_mapping_type",
            "timestamp",
        ],
        recovery_payload.get("rows") or [],
    )
    rollback_sha = _sha256_file(args.out_dir / "FOUR_LIKELY_ROLLBACK.csv")

    products_after = _load_insize_products()
    health_after = wave_health(catalog, products_after)
    cohort_after = build_proven_cohort(catalog, products_after, aliases)
    api = sample_api([u.product_id for u in cohort["updates"]])

    report["apply"] = apply_result
    report["rollback"] = {
        "artifact": str(args.out_dir / "FOUR_LIKELY_ROLLBACK.csv"),
        "rows": apply_result.get("rollback_rows"),
        "sha256": rollback_sha,
        "recovery_json": str(recovery),
        "recovery_sha256": apply_result.get("recovery_snapshot_sha256"),
    }
    report["post_apply"] = {
        "new_requiring_update": len(cohort_after["updates"]),
        "new_already_correct": len(cohort_after["already"]),
        "exact_need": health_after["exact_need"],
        "trailing_need": health_after["trailing_need"],
    }
    report["idempotency"] = {
        "new_cohort_updates": len(cohort_after["updates"]),
        "exact_cohort_updates": health_after["exact_need"],
        "trailing_a_cohort_updates": health_after["trailing_need"],
    }
    report["api_samples"] = api
    if (
        report["post_apply"]["new_requiring_update"] == 0
        and health_after["exact_need"] == 0
        and health_after["trailing_need"] == 0
    ):
        report["STATUS"] = "APPLIED_VERIFIED"
    else:
        report["STATUS"] = "APPLIED_WITH_MISMATCHES"

    _json_write(args.out_dir / "SYNC_REPORT.json", report)
    _json_write(args.out_dir / "APPLY_REPORT.json", report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["STATUS"] == "APPLIED_VERIFIED" else 15


if __name__ == "__main__":
    raise SystemExit(main())
