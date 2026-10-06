#!/usr/bin/env python3
"""INSIZE distributor workbook → live base_price sync (workbook USD × K6 rate).

Price rule (workbook already includes +20%):
  rial = ROUND_HALF_UP(usd * rate_cell_K6)
  base_price (Toman) = ROUND_HALF_UP(rial / 10)

Matching: brand_id=3 (INSIZE), exact normalize_sku(product.sku) == workbook CODE.
Mutates base_price only + product_change_logs. Never multiplies DB or workbook by 1.20.

Modes:
  default / --dry-run  — reconcile + gates, write artifacts, no DB writes
  --apply              — transactional apply (requires production guards)
  --rollback PATH      — restore from recovery snapshot JSON
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from collections import Counter, defaultdict
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
    INSIZE_BRAND_ID,
    PilotGateError,
    duplicate_workbook_codes,
    final_toman_from_usd,
    load_workbook_catalog,
    match_exact,
    normalize_sku,
    valid_workbook_price,
    workbook_sha256,
    write_recovery_snapshot,
)

EXPECTED_WORKBOOK_SHA256 = (
    "65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a"
)
EXPECTED_WORKBOOK_FILENAME = "موجودی توزیع کننده 11 شهریور - افزایش 20 درصدی.xlsx"
CANARY_SKU = "1106-1002"
CANARY_USD = Decimal("526.8")
CHANGE_REASON = "INSIZE distributor workbook +20% price sync owner-authorized 2026-10-06"
EXPECTED_HOST = "srv5944957438"
EXPECTED_DB = "karzar_staging"
DEFAULT_OUT = ROOT / "audit" / "insize-price-20-workbook"


@dataclass
class UpdateRow:
    product_id: int
    sku: str
    workbook_code: str
    workbook_row: int
    usd_price: Decimal
    rate: Decimal
    new_base_price: Decimal
    current_base_price: Decimal | None


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _require_production_guards(apply: bool) -> None:
    if not apply:
        return
    if os.getenv("KARZAR_ALLOW_PRODUCTION_WRITE", "").strip() != "1":
        raise PilotGateError("KARZAR_ALLOW_PRODUCTION_WRITE=1 required for --apply")
    if os.getenv("KARZAR_INGESTION_CATEGORY", "").strip().upper() != "B":
        raise PilotGateError("KARZAR_INGESTION_CATEGORY=B required for --apply")


def collect_runtime_identity() -> dict[str, Any]:
    host_proof = socket.gethostname()
    identity: dict[str, Any] = {
        "utc_timestamp": datetime.now(UTC).isoformat(),
        "host_proof": host_proof,
        "expected_host": EXPECTED_HOST,
        "expected_db": EXPECTED_DB,
        "container_proof": None,
        "volume_proof": None,
        "current_database": None,
        "git_sha": None,
    }
    try:
        identity["git_sha"] = (
            subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                text=True,
            ).strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        identity["git_sha"] = "UNKNOWN"

    identity["current_database"] = os.getenv("POSTGRES_DB")
    identity["app_env"] = os.getenv("APP_ENV")
    if os.getenv("KARZAR_INSIZE_WORKBOOK_SYNC_INSIDE_API") == "1":
        identity["container_proof"] = "lathe_api"
        identity["volume_proof"] = "karzar_postgres_data"
    return identity


def assert_cr011_identity(identity: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if identity.get("host_proof") != EXPECTED_HOST:
        errors.append(f"host_proof={identity.get('host_proof')}")
    if identity.get("container_proof") != "lathe_postgres":
        errors.append("lathe_postgres missing")
    if identity.get("current_database") != EXPECTED_DB:
        errors.append(f"database={identity.get('current_database')}")
    vol = (identity.get("volume_proof") or "").strip()
    if vol != "karzar_postgres_data":
        errors.append(f"volume={vol}")
    return errors


def assert_workbook_file(path: Path) -> tuple[str, Any]:
    if not path.is_file():
        raise PilotGateError(f"workbook missing: {path}")
    sha = workbook_sha256(path)
    if sha.lower() != EXPECTED_WORKBOOK_SHA256.lower():
        raise PilotGateError(f"workbook SHA mismatch: got {sha}")
    catalog = load_workbook_catalog(path)
    canary = catalog.by_code.get(normalize_sku(CANARY_SKU))
    if canary is None or canary.usd_price != CANARY_USD:
        raise PilotGateError(
            f"canary {CANARY_SKU} USD mismatch: "
            f"got {getattr(canary, 'usd_price', None)}, expected {CANARY_USD}"
        )
    if catalog.rate != Decimal("2500000"):
        raise PilotGateError(f"K6 rate mismatch: {catalog.rate}")
    dups = duplicate_workbook_codes(catalog.rows)
    if dups:
        price_conflicts: list[str] = []
        for code in dups:
            rows = [r for r in catalog.rows if normalize_sku(r.code) == code]
            usd_vals = {str(r.usd_price) for r in rows}
            if len(usd_vals) > 1:
                price_conflicts.append(code)
        if price_conflicts:
            raise PilotGateError(
                f"duplicate workbook CODE with conflicting USD: {sorted(price_conflicts)}"
            )
    return sha, catalog


def _open_db_session():
    url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not url:
        raise PilotGateError("DATABASE_URL not set (run inside lathe_api or export URL)")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(url)
    return sessionmaker(bind=engine)(), engine


def _load_insize_products(session: Any) -> list[Any]:
    from app.db.models.product import Product
    from sqlalchemy import select

    rows = (
        session.execute(
            select(Product).where(
                Product.brand_id == INSIZE_BRAND_ID,
                Product.deleted_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


def build_reconcile(
    catalog: Any,
    products: list[Any],
) -> dict[str, Any]:
    by_code = catalog.by_code
    ambiguous_db: list[dict[str, Any]] = []
    sku_groups: dict[str, list[Any]] = defaultdict(list)
    for p in products:
        sku_groups[normalize_sku(p.sku)].append(p)
    for sku, group in sku_groups.items():
        if sku and len(group) > 1:
            ambiguous_db.append(
                {
                    "normalized_sku": sku,
                    "product_ids": [int(g.id) for g in group],
                }
            )

    updates: list[UpdateRow] = []
    unmatched_products: list[dict[str, Any]] = []
    invalid_price: list[dict[str, Any]] = []
    already_aligned: list[dict[str, Any]] = []
    mismatch_preview: list[dict[str, Any]] = []

    for product in products:
        sku = normalize_sku(product.sku)
        if not sku:
            continue
        if len(sku_groups[sku]) > 1:
            continue
        match = match_exact(product.sku, by_code)
        if match.method != "exact" or not match.workbook_code:
            unmatched_products.append({"product_id": int(product.id), "sku": product.sku})
            continue
        wb = by_code[normalize_sku(match.workbook_code)]
        price_class, _rial, toman = valid_workbook_price(wb.usd_price, catalog.rate)
        if price_class != "VALID_WORKBOOK_PRICE" or toman is None:
            invalid_price.append(
                {
                    "product_id": int(product.id),
                    "sku": product.sku,
                    "class": price_class,
                    "usd": str(wb.usd_price),
                }
            )
            continue
        current = product.base_price
        cur_dec = None if current is None else Decimal(str(current))
        if cur_dec == toman:
            already_aligned.append({"product_id": int(product.id), "sku": product.sku})
            continue
        updates.append(
            UpdateRow(
                product_id=int(product.id),
                sku=str(product.sku),
                workbook_code=str(wb.code),
                workbook_row=int(wb.source_row),
                usd_price=wb.usd_price,
                rate=catalog.rate,
                new_base_price=toman,
                current_base_price=cur_dec,
            )
        )
        if len(mismatch_preview) < 25:
            mismatch_preview.append(
                {
                    "sku": product.sku,
                    "current": str(cur_dec) if cur_dec is not None else None,
                    "new": str(toman),
                    "usd": str(wb.usd_price),
                }
            )

    product_ids = [u.product_id for u in updates]
    if len(product_ids) != len(set(product_ids)):
        raise PilotGateError("duplicate product_id in update cohort")

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "brand_id": INSIZE_BRAND_ID,
        "workbook_rows": len(catalog.rows),
        "insize_products": len(products),
        "ambiguous_db_sku_groups": len(ambiguous_db),
        "unmatched_products": len(unmatched_products),
        "invalid_workbook_price": len(invalid_price),
        "already_aligned": len(already_aligned),
        "update_count": len(updates),
        "canary": {
            "sku": CANARY_SKU,
            "usd": str(CANARY_USD),
            "rate": str(catalog.rate),
            "toman": str(final_toman_from_usd(CANARY_USD, catalog.rate)),
        },
    }
    gates_ok = not ambiguous_db
    return {
        "summary": summary,
        "gates": {
            "ok": gates_ok,
            "ambiguous_db": ambiguous_db[:50],
        },
        "updates": updates,
        "mismatch_preview": mismatch_preview,
    }


def _rows_public(updates: list[UpdateRow]) -> list[dict[str, Any]]:
    return [
        {
            "product_id": u.product_id,
            "sku": u.sku,
            "workbook_code": u.workbook_code,
            "workbook_row": u.workbook_row,
            "usd_price": str(u.usd_price),
            "rate": str(u.rate),
            "current_base_price": None
            if u.current_base_price is None
            else str(u.current_base_price),
            "new_base_price": str(u.new_base_price),
        }
        for u in updates
    ]


def apply_updates(
    updates: list[UpdateRow],
    *,
    recovery_path: Path,
) -> dict[str, Any]:
    if not updates:
        return {"updated": 0, "skipped": 0}
    session, engine = _open_db_session()
    try:
        from app.db.models.product import Product
        from app.db.models.platform import ProductChangeLog
        from sqlalchemy import select

        ids = [u.product_id for u in updates]
        recovery_rows: list[dict[str, Any]] = []
        with session.begin():
            products = (
                session.execute(
                    select(Product)
                    .where(Product.id.in_(ids), Product.brand_id == INSIZE_BRAND_ID)
                    .with_for_update()
                )
                .scalars()
                .all()
            )
            by_id = {int(p.id): p for p in products}
            if len(by_id) != len(ids):
                raise PilotGateError("FOR UPDATE returned unexpected product count")
            for u in updates:
                p = by_id[u.product_id]
                if normalize_sku(p.sku) != normalize_sku(u.sku):
                    raise PilotGateError(f"SKU drift product_id={u.product_id}")
                recovery_rows.append(
                    {
                        "product_id": u.product_id,
                        "sku": u.sku,
                        "old_base_price": None
                        if p.base_price is None
                        else str(p.base_price),
                    }
                )
            snap_sha = write_recovery_snapshot(recovery_path, recovery_rows)
            updated = 0
            skipped = 0
            for u in updates:
                p = by_id[u.product_id]
                old = p.base_price
                old_str = None if old is None else str(old)
                if old is not None and Decimal(str(old)) == u.new_base_price:
                    skipped += 1
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
            "skipped_idempotent": skipped,
            "recovery_snapshot_path": str(recovery_path),
            "recovery_snapshot_sha256": snap_sha,
        }
    finally:
        session.close()
        engine.dispose()


def rollback_recovery(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    session, engine = _open_db_session()
    restored = 0
    try:
        from app.db.models.product import Product
        from app.db.models.platform import ProductChangeLog
        from sqlalchemy import select

        with session.begin():
            for row in rows:
                pid = int(row["product_id"])
                product = session.execute(
                    select(Product).where(Product.id == pid).with_for_update()
                ).scalar_one()
                if normalize_sku(product.sku) != normalize_sku(row.get("sku")):
                    raise PilotGateError(f"rollback SKU mismatch id={pid}")
                old_price = row.get("old_base_price")
                cur = product.base_price
                cur_str = None if cur is None else str(cur)
                new_val = None if old_price in (None, "") else Decimal(str(old_price))
                product.base_price = new_val
                session.add(
                    ProductChangeLog(
                        product_id=pid,
                        field_name="base_price",
                        old_value=cur_str,
                        new_value=None if new_val is None else str(new_val),
                        reason=f"rollback:{CHANGE_REASON}",
                        actor_user_id=None,
                    )
                )
                restored += 1
        return {"restored": restored}
    finally:
        session.close()
        engine.dispose()


def post_apply_reconcile_mismatches(catalog: Any, products: list[Any]) -> int:
    recon = build_reconcile(catalog, products)
    return recon["summary"]["update_count"]


def sample_api_products(product_ids: list[int], host: str = "api.karzartools.com") -> list[dict[str, Any]]:
    import urllib.request

    out: list[dict[str, Any]] = []
    for pid in product_ids[:8]:
        url = f"http://127.0.0.1:8000/api/v1/products/{pid}"
        req = urllib.request.Request(
            url,
            headers={"Host": host, "X-Forwarded-Proto": "https", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            out.append({"product_id": pid, "error": str(exc)})
            continue
        if isinstance(body, dict) and "data" in body:
            body = body["data"]
        out.append(
            {
                "product_id": pid,
                "http": 200,
                "sku": body.get("sku"),
                "base_price": body.get("base_price"),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm-production-write", action="store_true")
    ap.add_argument("--recovery-snapshot-path", type=Path, default=None)
    ap.add_argument("--rollback", type=Path, default=None)
    ap.add_argument("--skip-identity", action="store_true")
    args = ap.parse_args(argv)

    apply_mode = bool(args.apply)
    if args.rollback:
        _require_production_guards(True)
        if not args.confirm_production_write:
            raise SystemExit("rollback requires --confirm-production-write")
        result = rollback_recovery(args.rollback)
        print(json.dumps({"STATUS": "ROLLED_BACK", **result}))
        return 0

    identity = collect_runtime_identity()
    id_errors = [] if args.skip_identity else assert_cr011_identity(identity)
    sha, catalog = assert_workbook_file(args.xlsx)

    report: dict[str, Any] = {
        "STATUS": "DRY_RUN",
        "workbook_sha256": sha,
        "workbook_filename": EXPECTED_WORKBOOK_FILENAME,
        "K6_rate": str(catalog.rate),
        "identity": identity,
        "identity_ok": not id_errors,
        "identity_errors": id_errors,
    }
    if id_errors and not args.skip_identity:
        report["STATUS"] = "BLOCKED_IDENTITY"
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 10

    session, engine = _open_db_session()
    try:
        products = _load_insize_products(session)
    finally:
        session.close()
        engine.dispose()

    recon = build_reconcile(catalog, products)
    report["matching"] = recon["summary"]
    report["gates"] = recon["gates"]
    report["mismatch_preview"] = recon["mismatch_preview"]
    _json_write(args.out_dir / "RECONCILE.json", recon["summary"])
    _json_write(args.out_dir / "UPDATE_MANIFEST.json", _rows_public(recon["updates"]))

    if not recon["gates"]["ok"]:
        report["STATUS"] = "BLOCKED_GATES"
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 11

    if not apply_mode:
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 0

    if not args.confirm_production_write:
        print("FATAL: --apply requires --confirm-production-write", file=sys.stderr)
        return 2
    _require_production_guards(True)
    recovery = args.recovery_snapshot_path or (
        args.out_dir / f"RECOVERY_PREWRITE_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    apply_result = apply_updates(recon["updates"], recovery_path=recovery)
    report["apply"] = apply_result
    report["STATUS"] = "APPLIED"

    session, engine = _open_db_session()
    try:
        products_after = _load_insize_products(session)
    finally:
        session.close()
        engine.dispose()
    mismatch_count = post_apply_reconcile_mismatches(catalog, products_after)
    report["post_apply_mismatch_count"] = mismatch_count
    if mismatch_count:
        report["STATUS"] = "APPLIED_WITH_MISMATCHES"

    sample_ids = [u.product_id for u in recon["updates"][:5]]
    if sample_ids:
        report["api_samples"] = sample_api_products(sample_ids)

    _json_write(args.out_dir / "SYNC_REPORT.json", report)
    _json_write(args.out_dir / "APPLY_REPORT.json", report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if mismatch_count == 0 else 12


if __name__ == "__main__":
    raise SystemExit(main())
