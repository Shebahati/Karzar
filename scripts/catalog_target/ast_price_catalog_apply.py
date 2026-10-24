"""Guarded Category B APPLY for AST price UPDATE + product CREATE."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from catalog_target.ast_price_catalog_constants import (
    OWNER_AUTH_APPLY,
    OWNER_AUTH_ROLLBACK,
    SOURCE_ARCHIVE_SHA256,
)
from catalog_target.sales_wave_apply import ApplyAbort, normalize_database_url


class DbConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


MUTABLE_UPDATE_COLUMNS = ("base_price",)
FORBIDDEN_UPDATE_COLUMNS = (
    "sku",
    "name",
    "brand_id",
    "category_id",
    "is_available",
    "is_active",
    "original_price",
    "deleted_at",
)


@dataclass
class UpdatePlanRow:
    product_id: int
    sku: str
    expected_current_price: Decimal | None
    proposed_price: Decimal | None


@dataclass
class CreatePlanRow:
    sku: str
    brand_id: int
    category_id: int
    name: str
    base_price: Decimal | None
    is_available: bool = False
    is_active: bool = True


@dataclass
class StaleGuardResult:
    ok: bool
    expected_count: int
    match_count: int
    mismatches: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ApplyResult:
    mode: str
    committed: bool
    updates_written: int
    creates_written: int
    batch_id: str
    stale_guard: StaleGuardResult | None = None
    aborted_reason: str = ""
    journal_path: str = ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_price(raw: str) -> Decimal | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def load_update_plan(path: Path) -> list[UpdatePlanRow]:
    rows: list[UpdatePlanRow] = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("validation_result") or "OK") != "OK":
                continue
            rows.append(
                UpdatePlanRow(
                    product_id=int(r["product_id"]),
                    sku=str(r["sku"]),
                    expected_current_price=parse_price(r.get("expected_current_price") or r.get("current_price") or ""),
                    proposed_price=parse_price(r.get("proposed_price") or ""),
                )
            )
    return rows


def load_create_plan(path: Path) -> list[CreatePlanRow]:
    rows: list[CreatePlanRow] = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                CreatePlanRow(
                    sku=str(r["sku"]),
                    brand_id=int(r["brand_id"]),
                    category_id=int(r["category_id"]),
                    name=str(r["name"]),
                    base_price=parse_price(r.get("base_price") or ""),
                    is_available=str(r.get("is_available", "false")).lower() in {"1", "true", "t"},
                    is_active=str(r.get("is_active", "true")).lower() in {"1", "true", "t"},
                )
            )
    return rows


def assert_apply_gates(
    *,
    apply: bool,
    rollback: bool,
    owner_authorization: str,
    confirm_production_write: bool,
    confirm_source_sha256: str,
    confirm_update_manifest_sha256: str,
    confirm_create_manifest_sha256: str,
    update_manifest_sha256: str,
    create_manifest_sha256: str,
    confirm_update_count: int,
    confirm_create_count: int,
    update_count: int,
    create_count: int,
) -> None:
    if not apply and not rollback:
        return
    if apply:
        if owner_authorization != OWNER_AUTH_APPLY:
            raise ApplyAbort("owner_authorization_mismatch_apply")
        if confirm_source_sha256 != SOURCE_ARCHIVE_SHA256:
            raise ApplyAbort("confirm_source_sha256_mismatch")
        if confirm_update_manifest_sha256 != update_manifest_sha256:
            raise ApplyAbort("confirm_update_manifest_sha256_mismatch")
        if confirm_create_manifest_sha256 != create_manifest_sha256:
            raise ApplyAbort("confirm_create_manifest_sha256_mismatch")
        if confirm_update_count != update_count or confirm_create_count != create_count:
            raise ApplyAbort("confirm_mutation_count_mismatch")
    if rollback:
        if owner_authorization != OWNER_AUTH_ROLLBACK:
            raise ApplyAbort("owner_authorization_mismatch_rollback")
    if not confirm_production_write:
        raise ApplyAbort("missing_confirm_production_write")
    if os.getenv("KARZAR_ALLOW_PRODUCTION_WRITE", "").strip() != "1":
        raise ApplyAbort("missing_KARZAR_ALLOW_PRODUCTION_WRITE")
    if os.getenv("KARZAR_INGESTION_CATEGORY", "").strip().upper() != "B":
        raise ApplyAbort("missing_KARZAR_INGESTION_CATEGORY=B")


def verify_update_stale_guard(
    plan_rows: list[UpdatePlanRow],
    live_by_id: dict[int, dict[str, str]],
) -> StaleGuardResult:
    mismatches: list[dict[str, str]] = []
    matches = 0
    for row in plan_rows:
        live = live_by_id.get(row.product_id)
        if live is None:
            mismatches.append({"product_id": str(row.product_id), "reason": "missing"})
            continue
        if str(live.get("sku") or "") != row.sku:
            mismatches.append({"product_id": str(row.product_id), "reason": "sku_drift"})
            continue
        live_price = parse_price(str(live.get("base_price") or ""))
        if row.expected_current_price != live_price:
            mismatches.append(
                {
                    "product_id": str(row.product_id),
                    "reason": "price_drift",
                    "expected": str(row.expected_current_price),
                    "actual": str(live_price),
                }
            )
            continue
        matches += 1
    return StaleGuardResult(
        ok=matches == len(plan_rows) and not mismatches,
        expected_count=len(plan_rows),
        match_count=matches,
        mismatches=mismatches,
    )


def build_update_sql() -> str:
    return """
UPDATE products
SET base_price = %s, updated_at = NOW()
WHERE id = %s AND sku = %s AND deleted_at IS NULL
  AND base_price IS NOT DISTINCT FROM %s
"""


def apply_updates_sql(
    conn: DbConnection,
    plan_rows: list[UpdatePlanRow],
    *,
    dry_run: bool,
    product_id_allowlist: set[int] | None,
) -> tuple[int, StaleGuardResult]:
    scoped = plan_rows
    if product_id_allowlist is not None:
        scoped = [r for r in plan_rows if r.product_id in product_id_allowlist]
    if dry_run:
        return 0, StaleGuardResult(ok=True, expected_count=len(scoped), match_count=len(scoped))

    sql = build_update_sql()
    written = 0
    for row in scoped:
        conn.execute(
            sql,
            (
                row.proposed_price,
                row.product_id,
                row.sku,
                row.expected_current_price,
            ),
        )
        written += 1
    return written, StaleGuardResult(ok=True, expected_count=len(scoped), match_count=len(scoped))


async def apply_creates_via_service(
    plan_rows: list[CreatePlanRow],
    *,
    dry_run: bool,
    sku_allowlist: set[str] | None,
    session_factory: Any,
) -> int:
    from app.schemas.product import ProductCreate
    from app.services.product_service import ProductService

    scoped = plan_rows
    if sku_allowlist is not None:
        scoped = [r for r in plan_rows if r.sku in sku_allowlist]
    if dry_run:
        return 0

    written = 0
    async with session_factory() as db:
        for row in scoped:
            payload = ProductCreate(
                sku=row.sku,
                name=row.name,
                category_id=row.category_id,
                brand_id=row.brand_id,
                base_price=row.base_price,
                is_available=row.is_available,
                is_active=row.is_active,
            )
            await ProductService.create_product_with_validation(db, payload)
            written += 1
    return written


def write_journal(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def manifest_identity(update_path: Path, create_path: Path) -> dict[str, str]:
    return {
        "update_manifest_sha256": sha256_file(update_path),
        "create_manifest_sha256": sha256_file(create_path),
    }
