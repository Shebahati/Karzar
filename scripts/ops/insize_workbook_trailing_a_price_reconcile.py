#!/usr/bin/env python3
"""INSIZE workbook trailing-A alias price reconciliation.

Direction (non-negotiable):
  workbook CODE ``XA`` → Karzar INSIZE SKU ``X``
  Exact match always wins. Never strip A from DB SKUs.
  Never apply another +20%; price authority is workbook USD × K6.

Modes:
  default / --dry-run  — discovery + CSVs, no DB writes
  --apply              — transactional base_price-only apply (Category B guards)
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import socket
import subprocess
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
    INSIZE_BRAND_ID,
    PilotGateError,
    duplicate_workbook_codes,
    final_toman_from_usd,
    load_workbook_catalog,
    match_exact,
    match_insize_workbook_terminal_a_alias,
    normalize_sku,
    strip_exactly_one_terminal_workbook_A,
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
CHANGE_REASON = (
    "INSIZE workbook trailing-A alias price reconcile owner-authorized 2026-10-06"
)
EXPECTED_HOST = "srv5944957438"
EXPECTED_DB = "karzar_staging"
DEFAULT_OUT = ROOT / "audit" / "insize-price-20-trailing-a"
MATCH_TYPE = "WORKBOOK_TRAILING_A_ALIAS"


@dataclass
class AliasUpdateRow:
    product_id: int
    sku: str
    manufacturer_code: str | None
    workbook_code: str
    alias_code: str
    workbook_row: int
    usd_price: Decimal
    rate: Decimal
    new_base_price: Decimal
    current_base_price: Decimal | None
    match_type: str = MATCH_TYPE


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _csv_write(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


def collect_runtime_identity() -> dict[str, Any]:
    identity: dict[str, Any] = {
        "utc_timestamp": datetime.now(UTC).isoformat(),
        "host_proof": socket.gethostname(),
        "expected_host": EXPECTED_HOST,
        "expected_db": EXPECTED_DB,
        "container_proof": None,
        "volume_proof": None,
        "current_database": os.getenv("POSTGRES_DB"),
        "git_sha": "UNKNOWN",
        "app_env": os.getenv("APP_ENV"),
    }
    try:
        identity["git_sha"] = (
            subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                text=True,
            ).strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    if os.getenv("KARZAR_INSIZE_WORKBOOK_SYNC_INSIDE_API") == "1":
        identity["container_proof"] = "lathe_api"
        identity["volume_proof"] = "karzar_postgres_data"
    return identity


def assert_cr011_identity(identity: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    inside_api = os.getenv("KARZAR_INSIZE_WORKBOOK_SYNC_INSIDE_API") == "1"
    if not inside_api and identity.get("host_proof") != EXPECTED_HOST:
        errors.append(f"host_proof={identity.get('host_proof')}")
    if inside_api:
        if identity.get("container_proof") != "lathe_api":
            errors.append("lathe_api context missing")
    elif identity.get("container_proof") != "lathe_postgres":
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


def _async_engine_and_sessionmaker():
    from app.core.config import settings
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(settings.ASYNC_DATABASE_URI)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def _load_insize_products_async(session: Any) -> list[Any]:
    from app.db.models.product import Product
    from sqlalchemy import select

    result = await session.execute(
        select(Product).where(
            Product.brand_id == INSIZE_BRAND_ID,
            Product.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


def _load_insize_products() -> list[Any]:
    async def _run() -> list[Any]:
        engine, session_factory = _async_engine_and_sessionmaker()
        try:
            async with session_factory() as session:
                return await _load_insize_products_async(session)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def build_trailing_a_reconcile(catalog: Any, products: list[Any]) -> dict[str, Any]:
    by_code = catalog.by_code
    sku_groups: dict[str, list[Any]] = defaultdict(list)
    for p in products:
        sku_groups[normalize_sku(p.sku)].append(p)
    insize_db_skus = frozenset(k for k in sku_groups if k)

    ambiguous_db = [
        {"normalized_sku": sku, "product_ids": [int(g.id) for g in group]}
        for sku, group in sku_groups.items()
        if sku and len(group) > 1
    ]

    exact_aligned: list[dict[str, Any]] = []
    exact_updates: list[dict[str, Any]] = []
    exact_invalid: list[dict[str, Any]] = []
    previous_unmatched: list[dict[str, Any]] = []

    alias_safe: list[AliasUpdateRow] = []
    alias_already_correct: list[dict[str, Any]] = []
    alias_ambiguous: list[dict[str, Any]] = []
    alias_excluded: list[dict[str, Any]] = []
    remaining_unmatched: list[dict[str, Any]] = []

    workbook_ending_a = [c for c in by_code if c.endswith("A")]
    exact_match_wins: list[dict[str, Any]] = []
    non_a_collisions: list[dict[str, Any]] = []
    multi_source_collisions: list[dict[str, Any]] = []
    alias_sku_missing: list[dict[str, Any]] = []

    # Workbook-centric Case C / D discovery for codes ending A
    for wb_code in workbook_ending_a:
        alias = strip_exactly_one_terminal_workbook_A(wb_code)
        if alias is None:
            continue
        if alias in by_code and alias in insize_db_skus:
            non_a_collisions.append(
                {
                    "workbook_code": by_code[wb_code].code,
                    "alias_code": alias,
                    "reason": "workbook_has_both_X_and_XA",
                }
            )
        if wb_code in insize_db_skus and alias in insize_db_skus:
            exact_match_wins.append(
                {
                    "workbook_code": by_code[wb_code].code,
                    "db_exact_sku": wb_code,
                    "alias_skipped": alias,
                    "reason": "exact_db_XA_wins",
                }
            )

    for product in products:
        sku = normalize_sku(product.sku)
        if not sku:
            remaining_unmatched.append(
                {
                    "product_id": int(product.id),
                    "sku": product.sku,
                    "manufacturer_code": product.manufacturer_code,
                    "current_base_price": None
                    if product.base_price is None
                    else str(product.base_price),
                    "previous_mismatch_reason": "EMPTY_SKU",
                    "reason": "EMPTY_SKU",
                }
            )
            continue
        if len(sku_groups[sku]) > 1:
            remaining_unmatched.append(
                {
                    "product_id": int(product.id),
                    "sku": product.sku,
                    "manufacturer_code": product.manufacturer_code,
                    "current_base_price": None
                    if product.base_price is None
                    else str(product.base_price),
                    "previous_mismatch_reason": "AMBIGUOUS_DB_SKU",
                    "reason": "AMBIGUOUS_DB_SKU",
                }
            )
            continue

        exact = match_exact(product.sku, by_code)
        if exact.method == "exact" and exact.workbook_code:
            wb = by_code[normalize_sku(exact.workbook_code)]
            price_class, _rial, toman = valid_workbook_price(wb.usd_price, catalog.rate)
            if price_class != "VALID_WORKBOOK_PRICE" or toman is None:
                exact_invalid.append(
                    {
                        "product_id": int(product.id),
                        "sku": product.sku,
                        "workbook_code": wb.code,
                        "class": price_class,
                        "usd": str(wb.usd_price),
                    }
                )
                continue
            cur = None if product.base_price is None else Decimal(str(product.base_price))
            row = {
                "product_id": int(product.id),
                "sku": product.sku,
                "workbook_code": wb.code,
                "current_base_price": None if cur is None else str(cur),
                "target_base_price": str(toman),
            }
            if cur == toman:
                exact_aligned.append(row)
            else:
                exact_updates.append(row)
            continue

        # Previous exact-unmatched cohort member
        previous_unmatched.append(
            {
                "product_id": int(product.id),
                "sku": product.sku,
                "manufacturer_code": product.manufacturer_code,
                "current_base_price": None
                if product.base_price is None
                else str(product.base_price),
                "previous_mismatch_reason": "NO_EXACT_WORKBOOK_CODE",
            }
        )

        alias_match = match_insize_workbook_terminal_a_alias(
            product.sku,
            by_code,
            insize_db_skus=insize_db_skus,
            brand_is_insize=True,
        )
        if alias_match.method == "WORKBOOK_TRAILING_A_AMBIGUOUS":
            alias_ambiguous.append(
                {
                    "product_id": int(product.id),
                    "sku": product.sku,
                    "workbook_code": alias_match.workbook_code,
                    "candidates": ",".join(alias_match.candidates),
                    "reason": "WORKBOOK_TRAILING_A_AMBIGUOUS",
                }
            )
            continue
        if alias_match.method != "WORKBOOK_TRAILING_A_ALIAS" or not alias_match.workbook_code:
            xa = sku + "A"
            if xa not in by_code:
                alias_sku_missing.append(
                    {
                        "product_id": int(product.id),
                        "sku": product.sku,
                        "manufacturer_code": product.manufacturer_code,
                        "looked_for_workbook": xa,
                        "reason": "ALIAS_SKU_MISSING",
                    }
                )
                remaining_unmatched.append(
                    {
                        "product_id": int(product.id),
                        "sku": product.sku,
                        "manufacturer_code": product.manufacturer_code,
                        "current_base_price": None
                        if product.base_price is None
                        else str(product.base_price),
                        "previous_mismatch_reason": "NO_EXACT_WORKBOOK_CODE",
                        "reason": "ALIAS_SKU_MISSING",
                    }
                )
            else:
                remaining_unmatched.append(
                    {
                        "product_id": int(product.id),
                        "sku": product.sku,
                        "manufacturer_code": product.manufacturer_code,
                        "current_base_price": None
                        if product.base_price is None
                        else str(product.base_price),
                        "previous_mismatch_reason": "NO_EXACT_WORKBOOK_CODE",
                        "reason": "ALIAS_NOT_ACCEPTED",
                    }
                )
            continue

        wb = by_code[normalize_sku(alias_match.workbook_code)]
        # Case C product-side: workbook also has exact non-A (should be unreachable after exact)
        if sku in by_code:
            non_a_collisions.append(
                {
                    "product_id": int(product.id),
                    "sku": product.sku,
                    "workbook_code": wb.code,
                    "reason": "workbook_has_both_X_and_XA",
                }
            )
            alias_ambiguous.append(
                {
                    "product_id": int(product.id),
                    "sku": product.sku,
                    "workbook_code": wb.code,
                    "reason": "workbook_has_both_X_and_XA",
                }
            )
            continue

        price_class, _rial, toman = valid_workbook_price(wb.usd_price, catalog.rate)
        if price_class != "VALID_WORKBOOK_PRICE" or toman is None:
            alias_excluded.append(
                {
                    "product_id": int(product.id),
                    "sku": product.sku,
                    "workbook_code": wb.code,
                    "alias_code": sku,
                    "usd": str(wb.usd_price),
                    "class": price_class,
                    "reason": "EXCLUDED_NON_NUMERIC",
                }
            )
            continue

        cur = None if product.base_price is None else Decimal(str(product.base_price))
        row = AliasUpdateRow(
            product_id=int(product.id),
            sku=str(product.sku),
            manufacturer_code=product.manufacturer_code,
            workbook_code=str(wb.code),
            alias_code=sku,
            workbook_row=int(wb.source_row),
            usd_price=wb.usd_price if wb.usd_price is not None else Decimal("0"),
            rate=catalog.rate,
            new_base_price=toman,
            current_base_price=cur,
        )
        if cur == toman:
            alias_already_correct.append(
                {
                    "product_id": row.product_id,
                    "sku": row.sku,
                    "workbook_CODE": row.workbook_code,
                    "alias_code": row.alias_code,
                    "source_USD": str(row.usd_price),
                    "K6": str(row.rate),
                    "current_base_price": str(cur),
                    "target_base_price": str(toman),
                    "delta": "0",
                    "match_type": MATCH_TYPE,
                }
            )
        else:
            alias_safe.append(row)

    # Case D: multiple distinct workbook sources collapsing to same alias (defense)
    alias_targets: dict[str, list[str]] = defaultdict(list)
    for row in alias_safe:
        alias_targets[row.alias_code].append(row.workbook_code)
    for already in alias_already_correct:
        alias_targets[already["alias_code"]].append(already["workbook_CODE"])
    for alias, sources in alias_targets.items():
        uniq = list(dict.fromkeys(sources))
        if len(uniq) > 1:
            multi_source_collisions.append(
                {"alias_code": alias, "workbook_codes": ",".join(uniq)}
            )

    if multi_source_collisions:
        blocked = {c["alias_code"] for c in multi_source_collisions}
        alias_safe = [r for r in alias_safe if r.alias_code not in blocked]
        alias_already_correct = [
            r for r in alias_already_correct if r["alias_code"] not in blocked
        ]
        for c in multi_source_collisions:
            alias_ambiguous.append(
                {
                    "sku": c["alias_code"],
                    "workbook_codes": c["workbook_codes"],
                    "reason": "MULTIPLE_SOURCE_TO_ONE_DB",
                }
            )

    product_ids = [u.product_id for u in alias_safe]
    if len(product_ids) != len(set(product_ids)):
        raise PilotGateError("duplicate product_id in trailing-A update cohort")

    discovery = {
        "previous_exact_aligned": len(exact_aligned),
        "previous_unmatched": len(previous_unmatched),
        "exact_updates_required": len(exact_updates),
        "exact_invalid_workbook_price": len(exact_invalid),
        "workbook_codes_ending_A": len(workbook_ending_a),
        "safe_workbook_a_to_db_no_a": len(alias_safe) + len(alias_already_correct),
        "exact_match_wins": len(exact_match_wins),
        "non_a_workbook_collisions": len(non_a_collisions),
        "multiple_source_collisions": len(multi_source_collisions),
        "source_na_excluded": len(alias_excluded),
        "alias_sku_missing": len(alias_sku_missing),
        "ambiguous": len(alias_ambiguous),
        "remaining_genuine_unmatched": len(remaining_unmatched),
        "alias_already_correct": len(alias_already_correct),
        "alias_requiring_update": len(alias_safe),
    }

    return {
        "discovery": discovery,
        "gates": {"ok": not ambiguous_db and len(exact_updates) == 0, "ambiguous_db": ambiguous_db[:50]},
        "exact_aligned": exact_aligned,
        "exact_updates": exact_updates,
        "exact_invalid": exact_invalid,
        "previous_unmatched": previous_unmatched,
        "alias_updates": alias_safe,
        "alias_already_correct": alias_already_correct,
        "alias_ambiguous": alias_ambiguous,
        "alias_excluded": alias_excluded,
        "alias_sku_missing": alias_sku_missing,
        "remaining_unmatched": remaining_unmatched,
        "exact_match_wins": exact_match_wins,
        "non_a_collisions": non_a_collisions,
        "multi_source_collisions": multi_source_collisions,
        "canary": {
            "sku": CANARY_SKU,
            "usd": str(CANARY_USD),
            "rate": str(catalog.rate),
            "toman": str(final_toman_from_usd(CANARY_USD, catalog.rate)),
        },
    }


def _alias_row_public(u: AliasUpdateRow) -> dict[str, Any]:
    cur = u.current_base_price
    delta = None if cur is None else str(u.new_base_price - cur)
    if cur is None:
        delta = str(u.new_base_price)
    return {
        "product_id": u.product_id,
        "sku": u.sku,
        "Karzar_SKU": u.sku,
        "workbook_CODE": u.workbook_code,
        "alias_code": u.alias_code,
        "source_USD": str(u.usd_price),
        "K6": str(u.rate),
        "current_base_price": None if cur is None else str(cur),
        "target_base_price": str(u.new_base_price),
        "delta": delta,
        "match_type": u.match_type,
        "manufacturer_code": u.manufacturer_code,
        "workbook_row": u.workbook_row,
    }


async def _apply_updates_async(
    updates: list[AliasUpdateRow],
    *,
    recovery_path: Path,
) -> dict[str, Any]:
    if not updates:
        return {"updated": 0, "skipped_idempotent": 0}
    from app.db.models.platform import ProductChangeLog
    from app.db.models.product import Product
    from sqlalchemy import select

    engine, session_factory = _async_engine_and_sessionmaker()
    try:
        ids = [u.product_id for u in updates]
        recovery_rows: list[dict[str, Any]] = []
        async with session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Product)
                    .where(Product.id.in_(ids), Product.brand_id == INSIZE_BRAND_ID)
                    .with_for_update()
                )
                products = list(result.scalars().all())
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
                            "workbook_CODE": u.workbook_code,
                            "alias_code": u.alias_code,
                            "old_base_price": None
                            if p.base_price is None
                            else str(p.base_price),
                            "target_base_price": str(u.new_base_price),
                            "timestamp": datetime.now(UTC).isoformat(),
                            "match_type": MATCH_TYPE,
                        }
                    )
                snap_sha = write_recovery_snapshot(recovery_path, recovery_rows)
                if len(recovery_rows) != len(updates):
                    raise PilotGateError("ROLLBACK_ROWS != NEW_UPDATE_ROWS")
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
            "rollback_rows": len(recovery_rows),
        }
    finally:
        await engine.dispose()


def apply_updates(
    updates: list[AliasUpdateRow],
    *,
    recovery_path: Path,
) -> dict[str, Any]:
    return asyncio.run(_apply_updates_async(updates, recovery_path=recovery_path))


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


def write_artifacts(out_dir: Path, recon: dict[str, Any], catalog: Any) -> dict[str, str]:
    dry_rows = [_alias_row_public(u) for u in recon["alias_updates"]]
    dry_fields = [
        "product_id",
        "Karzar_SKU",
        "workbook_CODE",
        "alias_code",
        "source_USD",
        "K6",
        "current_base_price",
        "target_base_price",
        "delta",
        "match_type",
    ]
    _csv_write(out_dir / "WORKBOOK_TRAILING_A_DRY_RUN.csv", dry_fields, dry_rows)
    _csv_write(
        out_dir / "WORKBOOK_TRAILING_A_AMBIGUOUS.csv",
        ["product_id", "sku", "workbook_code", "workbook_codes", "candidates", "reason"],
        recon["alias_ambiguous"],
    )
    _csv_write(
        out_dir / "WORKBOOK_TRAILING_A_EXCLUDED.csv",
        ["product_id", "sku", "workbook_code", "alias_code", "usd", "class", "reason"],
        recon["alias_excluded"],
    )
    _csv_write(
        out_dir / "REMAINING_UNMATCHED.csv",
        [
            "product_id",
            "sku",
            "manufacturer_code",
            "current_base_price",
            "previous_mismatch_reason",
            "reason",
        ],
        recon["remaining_unmatched"],
    )
    _csv_write(
        out_dir / "PREVIOUS_UNMATCHED_171.csv",
        [
            "product_id",
            "sku",
            "manufacturer_code",
            "current_base_price",
            "previous_mismatch_reason",
        ],
        recon["previous_unmatched"],
    )
    _json_write(out_dir / "DISCOVERY.json", recon["discovery"])
    _json_write(
        out_dir / "SAMPLES.json",
        {
            "safe_alias_samples": dry_rows[:15],
            "exact_match_wins": recon["exact_match_wins"][:50],
            "non_a_collisions": recon["non_a_collisions"][:50],
            "multi_source_collisions": recon["multi_source_collisions"],
            "K6": str(catalog.rate),
        },
    )
    return {
        "dry_run": str(out_dir / "WORKBOOK_TRAILING_A_DRY_RUN.csv"),
        "ambiguous": str(out_dir / "WORKBOOK_TRAILING_A_AMBIGUOUS.csv"),
        "excluded": str(out_dir / "WORKBOOK_TRAILING_A_EXCLUDED.csv"),
        "remaining": str(out_dir / "REMAINING_UNMATCHED.csv"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm-production-write", action="store_true")
    ap.add_argument("--recovery-snapshot-path", type=Path, default=None)
    ap.add_argument("--skip-identity", action="store_true")
    args = ap.parse_args(argv)

    apply_mode = bool(args.apply)
    identity = collect_runtime_identity()
    id_errors = [] if args.skip_identity else assert_cr011_identity(identity)
    sha, catalog = assert_workbook_file(args.xlsx)

    report: dict[str, Any] = {
        "STATUS": "DRY_RUN",
        "workbook_sha256": sha,
        "workbook_filename": EXPECTED_WORKBOOK_FILENAME,
        "K6_rate": str(catalog.rate),
        "price_rule": "ROUND_HALF_UP(USD×K6)/10 Toman; workbook already +20%",
        "identity": identity,
        "identity_ok": not id_errors,
        "identity_errors": id_errors,
        "matcher_direction": "WORKBOOK CODE ending A -> DB SKU without A",
    }
    if id_errors and not args.skip_identity:
        report["STATUS"] = "BLOCKED_IDENTITY"
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 10

    products = _load_insize_products()
    recon = build_trailing_a_reconcile(catalog, products)
    report["discovery"] = recon["discovery"]
    report["gates"] = recon["gates"]
    report["canary"] = recon["canary"]
    artifacts = write_artifacts(args.out_dir, recon, catalog)
    report["artifacts"] = artifacts

    # Hard stop if exact cohort suddenly needs updates (must stay 0)
    if recon["discovery"]["exact_updates_required"] != 0:
        report["STATUS"] = "BLOCKED_EXACT_COHORT_DRIFT"
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 11

    if not recon["gates"]["ok"]:
        report["STATUS"] = "BLOCKED_GATES"
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 12

    # Pattern support gate: need clear trailing-A evidence
    if recon["discovery"]["safe_workbook_a_to_db_no_a"] < 10:
        report["STATUS"] = "BLOCKED_PATTERN_UNSUPPORTED"
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 13

    if not apply_mode:
        report["STATUS"] = "READY_TO_APPLY" if recon["alias_updates"] else "DRY_RUN_NO_UPDATES"
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False))
        return 0

    if not args.confirm_production_write:
        print("FATAL: --apply requires --confirm-production-write", file=sys.stderr)
        return 2
    _require_production_guards(True)

    recovery = args.recovery_snapshot_path or (
        args.out_dir
        / f"RECOVERY_TRAILING_A_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    apply_result = apply_updates(recon["alias_updates"], recovery_path=recovery)
    if apply_result.get("rollback_rows") != len(recon["alias_updates"]):
        report["STATUS"] = "BLOCKED_ROLLBACK_MISMATCH"
        report["apply"] = apply_result
        _json_write(args.out_dir / "SYNC_REPORT.json", report)
        return 14

    # Freeze rollback CSV copy
    recovery_payload = json.loads(Path(recovery).read_text(encoding="utf-8"))
    _csv_write(
        args.out_dir / "WORKBOOK_TRAILING_A_ROLLBACK.csv",
        [
            "product_id",
            "sku",
            "workbook_CODE",
            "alias_code",
            "old_base_price",
            "target_base_price",
            "timestamp",
            "match_type",
        ],
        recovery_payload.get("rows") or [],
    )
    rollback_sha = _sha256_file(args.out_dir / "WORKBOOK_TRAILING_A_ROLLBACK.csv")

    report["apply"] = apply_result
    report["rollback"] = {
        "artifact": str(args.out_dir / "WORKBOOK_TRAILING_A_ROLLBACK.csv"),
        "rows": apply_result.get("rollback_rows"),
        "sha256": rollback_sha,
        "recovery_json": str(recovery),
        "recovery_sha256": apply_result.get("recovery_snapshot_sha256"),
    }
    report["STATUS"] = "APPLIED"

    products_after = _load_insize_products()
    post = build_trailing_a_reconcile(catalog, products_after)
    report["post_apply"] = {
        "exact_aligned": post["discovery"]["previous_exact_aligned"],
        "exact_updates_required": post["discovery"]["exact_updates_required"],
        "alias_requiring_update": post["discovery"]["alias_requiring_update"],
        "alias_already_correct": post["discovery"]["alias_already_correct"],
        "remaining_unmatched": post["discovery"]["remaining_genuine_unmatched"],
        "WORKBOOK_TRAILING_A_PRICE_MISMATCH_COUNT": post["discovery"][
            "alias_requiring_update"
        ],
    }
    if post["discovery"]["alias_requiring_update"] != 0:
        report["STATUS"] = "APPLIED_WITH_MISMATCHES"

    # Idempotent second pass counts
    report["idempotency"] = {
        "exact_cohort_updates": post["discovery"]["exact_updates_required"],
        "workbook_trailing_a_updates": post["discovery"]["alias_requiring_update"],
    }

    sample_ids = [u.product_id for u in recon["alias_updates"][:8]]
    api_samples = sample_api_products(sample_ids) if sample_ids else []
    # Attach workbook/DB proof for samples
    by_id_after = {int(p.id): p for p in products_after}
    enriched = []
    for sample in api_samples:
        pid = sample.get("product_id")
        p = by_id_after.get(pid)
        update = next((u for u in recon["alias_updates"] if u.product_id == pid), None)
        enriched.append(
            {
                **sample,
                "workbook_CODE": None if update is None else update.workbook_code,
                "workbook_USD": None if update is None else str(update.usd_price),
                "K6": None if update is None else str(update.rate),
                "target_toman": None if update is None else str(update.new_base_price),
                "db_base_price": None
                if p is None or p.base_price is None
                else str(p.base_price),
                "db_api_agree": (
                    p is not None
                    and sample.get("base_price") is not None
                    and Decimal(str(p.base_price)) == Decimal(str(sample["base_price"]))
                )
                if p is not None and sample.get("base_price") is not None
                else False,
            }
        )
    report["api_samples"] = enriched

    if (
        report["post_apply"]["WORKBOOK_TRAILING_A_PRICE_MISMATCH_COUNT"] == 0
        and report["idempotency"]["exact_cohort_updates"] == 0
        and report["idempotency"]["workbook_trailing_a_updates"] == 0
    ):
        report["STATUS"] = "APPLIED_VERIFIED"

    _json_write(args.out_dir / "SYNC_REPORT.json", report)
    _json_write(args.out_dir / "APPLY_REPORT.json", report)
    # Preserve pre-apply dry-run cohort; write post-apply discovery separately.
    _json_write(args.out_dir / "POST_APPLY_DISCOVERY.json", post["discovery"])
    _csv_write(
        args.out_dir / "REMAINING_UNMATCHED.csv",
        [
            "product_id",
            "sku",
            "manufacturer_code",
            "current_base_price",
            "previous_mismatch_reason",
            "reason",
        ],
        post["remaining_unmatched"],
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["STATUS"] == "APPLIED_VERIFIED" else 15


if __name__ == "__main__":
    raise SystemExit(main())
