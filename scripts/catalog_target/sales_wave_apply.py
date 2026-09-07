"""Guarded INSIZE Sales Wave 1 APPLY (dry-run default).

Implements the reviewed allowlist writer contract. Production mutation requires
explicit Category B authorization and never runs by default.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from catalog_target.apply_contract import APPLY_REQUIRED_LIVE_FIELDS, StaleSnapshotGuard

# Runtime DB client pinned in requirements.txt (API image). Do not use psycopg.
RUNTIME_DB_DRIVER = "asyncpg"
RUNTIME_DB_DEPENDENCY = "asyncpg==0.29.0"


# Reviewed plan identity from PR #285 (immutable contract for this wave).
REVIEWED_SNAPSHOT_TIMESTAMP = "20260907T102823Z"
REVIEWED_SNAPSHOT_SHA256 = (
    "4823ea7e39ffe6dc057c329a9387343ad77f369a8506925bf96cdb75c3b99cbf"
)
REVIEWED_ALLOWLIST_COUNT = 158
REVIEWED_PRICE_CHANGES = 158
REVIEWED_AVAILABILITY_CHANGES = 22
REVIEWED_ACTIVE_CHANGES = 0
REVIEWED_PLAN_CSV_RELATIVE = "data/catalog-target/insize_sales_wave_1_plan.csv"
# Frozen after merge of #285 onto main @ 6d36327.
REVIEWED_PLAN_CSV_SHA256 = (
    "222c7975852bb49367b211aa53cc021dd8784f2602281fb5893ef0736d8d639b"
)
REVIEWED_PLAN_JSON_SHA256 = (
    "97afdb8bf31348692d6e30122cc67a49cd0a0aad6a51099d996ca28a8c71a6f2"
)

MUTABLE_COLUMNS = ("base_price", "is_available")
FORBIDDEN_MUTATION_COLUMNS = (
    "sku",
    "slug",
    "name",
    "brand_id",
    "category_id",
    "is_active",
    "deleted_at",
)

REQUIRED_PLAN_FIELDS = (
    "id",
    "sku",
    "normalized_sku",
    "current_brand",
    "current_base_price",
    "proposed_base_price",
    "base_price_change",
    "current_is_available",
    "proposed_is_available",
    "is_available_change",
    "current_is_active",
    "proposed_is_active",
    "is_active_change",
    "media_ready",
    "commerce_ready",
    "public_sell_ready",
    "reconciliation_state",
    "inventory_status",
    "inclusion_reasons",
    "source_price",
    "source_inventory",
)

ALLOW_ENV = "KARZAR_ALLOW_PRODUCTION_WRITE"
CATEGORY_ENV = "KARZAR_INGESTION_CATEGORY"
PROD_HOST_MARKER = "karzartools.com"


class ApplyAbort(Exception):
    """Fail-closed abort before or during APPLY (always implies no commit)."""


class DbConnection(Protocol):
    def cursor(self, *args: Any, **kwargs: Any) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@dataclass(frozen=True)
class PlanRow:
    product_id: int
    sku: str
    normalized_sku: str
    current_brand: str
    expected_base_price: Decimal | None
    proposed_base_price: Decimal
    base_price_change: bool
    expected_is_available: bool
    proposed_is_available: bool
    is_available_change: bool
    expected_is_active: bool
    proposed_is_active: bool
    is_active_change: bool
    media_ready: bool
    commerce_ready: bool
    public_sell_ready: bool
    reconciliation_state: str
    inventory_status: str
    inclusion_reasons: str
    source_price: str
    source_inventory: str
    image_count: int | None = None
    primary_image_url: str = ""
    target_provenance: str = ""

    @property
    def price_delta_pct(self) -> Decimal | None:
        if self.expected_base_price is None or self.expected_base_price <= 0:
            return None
        return (
            (self.proposed_base_price - self.expected_base_price)
            / self.expected_base_price
            * Decimal("100")
        ).quantize(Decimal("0.01"))


@dataclass
class LiveProduct:
    id: int
    sku: str
    base_price: Decimal | None
    is_active: bool | None
    is_available: bool | None
    deleted_at: str | None
    brand_id: str | None = None
    category_id: str | None = None
    name: str | None = None
    slug: str | None = None


@dataclass
class DriftItem:
    product_id: int
    sku: str
    field: str
    expected: str
    observed: str
    reason: str


@dataclass
class StaleGuardResult:
    ok: bool
    expected_count: int
    observed_count: int
    drifts: list[DriftItem] = field(default_factory=list)
    missing_ids: list[int] = field(default_factory=list)
    extra_ids: list[int] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "expected_count": self.expected_count,
            "observed_count": self.observed_count,
            "drift_count": len(self.drifts),
            "drifts": [asdict(d) for d in self.drifts],
            "missing_ids": self.missing_ids,
            "extra_ids": self.extra_ids,
        }


@dataclass
class DryRunLine:
    product_id: int
    sku: str
    current_base_price: str
    proposed_base_price: str
    current_is_available: str
    proposed_is_available: str
    current_is_active: str
    proposed_is_active: str
    price_delta_pct: str
    will_update_price: bool
    will_update_availability: bool
    unchanged_fields: list[str]


@dataclass
class ApplyRunResult:
    mode: str
    production_apply_executed: bool
    aborted: bool
    abort_reason: str = ""
    plan_path: str = ""
    plan_csv_sha256: str = ""
    plan_json_sha256: str = ""
    allowlist_count: int = 0
    expected_price_changes: int = 0
    expected_availability_changes: int = 0
    expected_active_changes: int = 0
    stale_guard: dict[str, Any] = field(default_factory=dict)
    dry_run_lines: list[dict[str, Any]] = field(default_factory=list)
    price_change_stats: dict[str, Any] = field(default_factory=dict)
    backup_path: str = ""
    backup_sha256: str = ""
    rollback_sql_path: str = ""
    updated_count: int = 0
    transaction_safeguards: dict[str, Any] = field(default_factory=dict)
    implementation_ready: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_bool(raw: str | None, *, field_name: str) -> bool:
    text = (raw or "").strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise ApplyAbort(f"malformed_bool:{field_name}:{raw!r}")


def _parse_decimal(raw: str | None, *, field_name: str) -> Decimal:
    text = (raw or "").strip()
    if not text:
        raise ApplyAbort(f"missing_decimal:{field_name}")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ApplyAbort(f"malformed_decimal:{field_name}:{raw!r}") from exc
    return value


def _parse_bool_change(raw: str | None, *, field_name: str) -> bool:
    return _parse_bool(raw, field_name=field_name)


def default_plan_csv_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    return root / REVIEWED_PLAN_CSV_RELATIVE


def load_and_validate_plan(
    path: Path,
    *,
    expected_csv_sha256: str = REVIEWED_PLAN_CSV_SHA256,
    require_checksum: bool = True,
) -> list[PlanRow]:
    if not path.is_file():
        raise ApplyAbort(f"plan_missing:{path}")
    digest = sha256_file(path)
    if require_checksum and digest != expected_csv_sha256:
        raise ApplyAbort(
            f"plan_checksum_mismatch:expected={expected_csv_sha256}:observed={digest}"
        )

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        missing = [f for f in REQUIRED_PLAN_FIELDS if f not in fieldnames]
        if missing:
            raise ApplyAbort(f"plan_missing_columns:{','.join(missing)}")
        raw_rows = list(reader)

    if len(raw_rows) != REVIEWED_ALLOWLIST_COUNT:
        raise ApplyAbort(
            f"plan_count_mismatch:expected={REVIEWED_ALLOWLIST_COUNT}:observed={len(raw_rows)}"
        )

    rows: list[PlanRow] = []
    seen_ids: set[int] = set()
    seen_skus: set[str] = set()
    price_changes = 0
    avail_changes = 0
    active_changes = 0

    # current_base_price may be empty in the reviewed plan when production is NULL.
    nullable_plan_fields = {"current_base_price"}
    for raw in raw_rows:
        for field_name in REQUIRED_PLAN_FIELDS:
            if field_name in nullable_plan_fields:
                continue
            if str(raw.get(field_name) or "").strip() == "":
                raise ApplyAbort(f"plan_empty_required_field:{field_name}")
        try:
            product_id = int(str(raw["id"]).strip())
        except ValueError as exc:
            raise ApplyAbort(f"malformed_product_id:{raw.get('id')!r}") from exc

        sku = str(raw["sku"]).strip()
        normalized = str(raw["normalized_sku"]).strip().upper()
        brand = str(raw["current_brand"]).strip()
        if "INSIZE" not in brand.upper():
            raise ApplyAbort(f"wrong_brand:{sku}:{brand}")

        if product_id in seen_ids:
            raise ApplyAbort(f"duplicate_product_id:{product_id}")
        if normalized in seen_skus:
            raise ApplyAbort(f"duplicate_sku:{normalized}")
        seen_ids.add(product_id)
        seen_skus.add(normalized)

        state = str(raw["reconciliation_state"]).strip()
        if state == "REVIEW":
            raise ApplyAbort(f"review_row_forbidden:{sku}")
        if state in {"CREATE", "DEACTIVATE", "NOOP_INACTIVE_NON_TARGET", "KEEP"}:
            raise ApplyAbort(f"state_forbidden:{sku}:{state}")
        if state != "UPDATE":
            raise ApplyAbort(f"unexpected_state:{sku}:{state}")

        if str(raw["public_sell_ready"]).strip().lower() != "true":
            raise ApplyAbort(f"not_public_sell_ready:{sku}")
        if str(raw["commerce_ready"]).strip().lower() != "true":
            raise ApplyAbort(f"not_commerce_ready:{sku}")
        if str(raw["media_ready"]).strip().lower() != "true":
            raise ApplyAbort(f"not_media_ready:{sku}")
        if str(raw["inventory_status"]).strip() != "موجود":
            raise ApplyAbort(f"inventory_not_available:{sku}:{raw.get('inventory_status')!r}")

        proposed_price = _parse_decimal(raw.get("proposed_base_price"), field_name="proposed_base_price")
        if proposed_price <= 0:
            raise ApplyAbort(f"non_positive_proposed_price:{sku}")
        current_price_raw = str(raw.get("current_base_price") or "").strip()
        expected_price = (
            None
            if not current_price_raw
            else _parse_decimal(current_price_raw, field_name="current_base_price")
        )

        proposed_available = _parse_bool(raw.get("proposed_is_available"), field_name="proposed_is_available")
        if proposed_available is not True:
            raise ApplyAbort(f"proposed_unavailable:{sku}")
        expected_available = _parse_bool(raw.get("current_is_available"), field_name="current_is_available")
        expected_active = _parse_bool(raw.get("current_is_active"), field_name="current_is_active")
        proposed_active = _parse_bool(raw.get("proposed_is_active"), field_name="proposed_is_active")

        price_change = _parse_bool_change(raw.get("base_price_change"), field_name="base_price_change")
        avail_change = _parse_bool_change(raw.get("is_available_change"), field_name="is_available_change")
        active_change = _parse_bool_change(raw.get("is_active_change"), field_name="is_active_change")
        if active_change:
            raise ApplyAbort(f"active_change_not_authorized:{sku}")
        if price_change:
            price_changes += 1
        if avail_change:
            avail_changes += 1
        if active_change:
            active_changes += 1

        image_count_raw = str(raw.get("image_count") or "").strip()
        image_count = int(image_count_raw) if image_count_raw.isdigit() else None

        rows.append(
            PlanRow(
                product_id=product_id,
                sku=sku,
                normalized_sku=normalized,
                current_brand=brand,
                expected_base_price=expected_price,
                proposed_base_price=proposed_price,
                base_price_change=price_change,
                expected_is_available=expected_available,
                proposed_is_available=proposed_available,
                is_available_change=avail_change,
                expected_is_active=expected_active,
                proposed_is_active=proposed_active,
                is_active_change=active_change,
                media_ready=True,
                commerce_ready=True,
                public_sell_ready=True,
                reconciliation_state=state,
                inventory_status=str(raw["inventory_status"]).strip(),
                inclusion_reasons=str(raw.get("inclusion_reasons") or ""),
                source_price=str(raw.get("source_price") or ""),
                source_inventory=str(raw.get("source_inventory") or ""),
                image_count=image_count,
                primary_image_url=str(raw.get("primary_image_url") or ""),
                target_provenance=str(raw.get("target_provenance") or ""),
            )
        )

    if price_changes != REVIEWED_PRICE_CHANGES:
        raise ApplyAbort(
            f"price_change_count_mismatch:expected={REVIEWED_PRICE_CHANGES}:observed={price_changes}"
        )
    if avail_changes != REVIEWED_AVAILABILITY_CHANGES:
        raise ApplyAbort(
            f"availability_change_count_mismatch:expected={REVIEWED_AVAILABILITY_CHANGES}:observed={avail_changes}"
        )
    if active_changes != REVIEWED_ACTIVE_CHANGES:
        raise ApplyAbort(
            f"active_change_count_mismatch:expected={REVIEWED_ACTIVE_CHANGES}:observed={active_changes}"
        )
    return rows


def _decimal_equal(left: Decimal | None, right: Decimal | None) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return left == right


def compare_live_to_plan(plan: PlanRow, live: LiveProduct) -> list[DriftItem]:
    drifts: list[DriftItem] = []
    if live.deleted_at:
        drifts.append(
            DriftItem(
                product_id=plan.product_id,
                sku=plan.sku,
                field="deleted_at",
                expected="",
                observed=str(live.deleted_at),
                reason="deleted_current",
            )
        )
    if live.id != plan.product_id:
        drifts.append(
            DriftItem(
                product_id=plan.product_id,
                sku=plan.sku,
                field="id",
                expected=str(plan.product_id),
                observed=str(live.id),
                reason="id_mismatch",
            )
        )
    if live.sku.strip().upper() != plan.sku.strip().upper():
        drifts.append(
            DriftItem(
                product_id=plan.product_id,
                sku=plan.sku,
                field="sku",
                expected=plan.sku,
                observed=live.sku,
                reason="sku_mismatch",
            )
        )
    if not _decimal_equal(live.base_price, plan.expected_base_price):
        drifts.append(
            DriftItem(
                product_id=plan.product_id,
                sku=plan.sku,
                field="base_price",
                expected=str(plan.expected_base_price),
                observed="" if live.base_price is None else str(live.base_price),
                reason="stale_price",
            )
        )
    if live.is_available is not plan.expected_is_available:
        drifts.append(
            DriftItem(
                product_id=plan.product_id,
                sku=plan.sku,
                field="is_available",
                expected=str(plan.expected_is_available).lower(),
                observed="" if live.is_available is None else str(live.is_available).lower(),
                reason="stale_availability",
            )
        )
    if live.is_active is not plan.expected_is_active:
        drifts.append(
            DriftItem(
                product_id=plan.product_id,
                sku=plan.sku,
                field="is_active",
                expected=str(plan.expected_is_active).lower(),
                observed="" if live.is_active is None else str(live.is_active).lower(),
                reason="stale_active",
            )
        )
    return drifts


def stale_guard(plan_rows: list[PlanRow], live_rows: list[LiveProduct]) -> StaleGuardResult:
    by_id = {row.id: row for row in live_rows}
    if len(by_id) != len(live_rows):
        raise ApplyAbort("duplicate_live_product_id")
    expected_ids = [row.product_id for row in plan_rows]
    missing = [pid for pid in expected_ids if pid not in by_id]
    extra = [pid for pid in by_id if pid not in set(expected_ids)]
    drifts: list[DriftItem] = []
    for plan in plan_rows:
        live = by_id.get(plan.product_id)
        if live is None:
            continue
        drifts.extend(compare_live_to_plan(plan, live))
    ok = not drifts and not missing and not extra and len(live_rows) == len(plan_rows)
    return StaleGuardResult(
        ok=ok,
        expected_count=len(plan_rows),
        observed_count=len(live_rows),
        drifts=drifts,
        missing_ids=missing,
        extra_ids=extra,
    )


def build_dry_run_lines(plan_rows: list[PlanRow]) -> list[DryRunLine]:
    lines: list[DryRunLine] = []
    for row in plan_rows:
        unchanged = [col for col in FORBIDDEN_MUTATION_COLUMNS]
        lines.append(
            DryRunLine(
                product_id=row.product_id,
                sku=row.sku,
                current_base_price=""
                if row.expected_base_price is None
                else str(row.expected_base_price),
                proposed_base_price=str(row.proposed_base_price),
                current_is_available=str(row.expected_is_available).lower(),
                proposed_is_available=str(row.proposed_is_available).lower(),
                current_is_active=str(row.expected_is_active).lower(),
                proposed_is_active=str(row.proposed_is_active).lower(),
                price_delta_pct="" if row.price_delta_pct is None else str(row.price_delta_pct),
                will_update_price=row.base_price_change,
                will_update_availability=row.is_available_change,
                unchanged_fields=unchanged,
            )
        )
    return lines


def price_change_stats(plan_rows: list[PlanRow]) -> dict[str, Any]:
    deltas = [row.price_delta_pct for row in plan_rows if row.price_delta_pct is not None]
    if not deltas:
        return {"count": 0}
    outliers = [
        {"sku": row.sku, "pct": str(row.price_delta_pct)}
        for row in plan_rows
        if row.price_delta_pct is not None and abs(row.price_delta_pct) >= Decimal("50")
    ]
    return {
        "count": len(deltas),
        "min_pct": str(min(deltas)),
        "max_pct": str(max(deltas)),
        "median_pct": str(sorted(deltas)[len(deltas) // 2]),
        "outliers_abs_pct_ge_50": outliers,
        "note": "Outliers are reported only; no hardcoded reject threshold in this wave.",
    }


def write_pre_apply_backup(
    live_rows: list[LiveProduct],
    *,
    output_dir: Path,
    stamp: str | None = None,
) -> tuple[Path, str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = output_dir / f"insize_sales_wave_1_pre_apply_{stamp}.csv"
    rollback_path = output_dir / f"insize_sales_wave_1_rollback_{stamp}.sql"
    fields = ["id", "sku", "base_price", "is_active", "is_available", "deleted_at"]
    with backup_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in sorted(live_rows, key=lambda item: item.id):
            writer.writerow(
                {
                    "id": row.id,
                    "sku": row.sku,
                    "base_price": "" if row.base_price is None else str(row.base_price),
                    "is_active": "" if row.is_active is None else str(row.is_active).lower(),
                    "is_available": ""
                    if row.is_available is None
                    else str(row.is_available).lower(),
                    "deleted_at": row.deleted_at or "",
                }
            )
    lines = [
        "-- Rollback for INSIZE Sales Wave 1. Generated from pre-write backup.",
        "-- Restores ONLY writer-mutable columns: base_price, is_available.",
        "-- Active flag is audited in the CSV backup but intentionally excluded from SET.",
        "BEGIN;",
    ]
    for row in sorted(live_rows, key=lambda item: item.id):
        price = "NULL" if row.base_price is None else str(row.base_price)
        available = (
            "NULL" if row.is_available is None else ("TRUE" if row.is_available else "FALSE")
        )
        lines.append(
            "UPDATE products SET "
            f"base_price = {price}, is_available = {available} "
            f"WHERE id = {row.id} AND sku = '{row.sku.replace(chr(39), chr(39)+chr(39))}';"
        )
    lines.append(f"-- expected_row_count={len(live_rows)}")
    lines.append("COMMIT;")
    rollback_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return backup_path, sha256_file(backup_path), rollback_path


SELECT_ALLOWLIST_SQL = """
SELECT p.id, p.sku, p.base_price, p.is_active, p.is_available, p.deleted_at,
       p.brand_id, p.category_id, p.name, p.slug
FROM products p
WHERE p.id = ANY(%s)
ORDER BY p.id
FOR UPDATE
"""

SELECT_ALLOWLIST_SQL_NO_LOCK = """
SELECT p.id, p.sku, p.base_price, p.is_active, p.is_available, p.deleted_at,
       p.brand_id, p.category_id, p.name, p.slug
FROM products p
WHERE p.id = ANY(%s)
ORDER BY p.id
"""

UPDATE_SQL = """
UPDATE products
SET base_price = %s, is_available = %s
WHERE id = %s AND sku = %s AND deleted_at IS NULL
  AND base_price IS NOT DISTINCT FROM %s
  AND is_available IS NOT DISTINCT FROM %s
  AND is_active IS NOT DISTINCT FROM %s
"""


def normalize_database_url(url: str) -> str:
    """Strip SQLAlchemy asyncpg driver suffixes for asyncpg.connect()."""
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix) :]
    return url


def _percent_s_to_asyncpg(sql: str) -> str:
    """Convert psycopg-style %s placeholders to asyncpg $1..$n."""
    parts = sql.split("%s")
    if len(parts) == 1:
        return sql
    out: list[str] = []
    for index, part in enumerate(parts[:-1]):
        out.append(part)
        out.append(f"${index + 1}")
    out.append(parts[-1])
    return "".join(out)


def _record_to_live_product(payload: dict[str, Any]) -> LiveProduct:
    price = payload.get("base_price")
    deleted = payload.get("deleted_at")
    return LiveProduct(
        id=int(payload["id"]),
        sku=str(payload["sku"]),
        base_price=None if price is None else Decimal(str(price)),
        is_active=None if payload.get("is_active") is None else bool(payload["is_active"]),
        is_available=None
        if payload.get("is_available") is None
        else bool(payload["is_available"]),
        deleted_at=None if not deleted else str(deleted),
        brand_id=None if payload.get("brand_id") is None else str(payload["brand_id"]),
        category_id=None if payload.get("category_id") is None else str(payload["category_id"]),
        name=None if payload.get("name") is None else str(payload["name"]),
        slug=None if payload.get("slug") is None else str(payload["slug"]),
    )


def rows_from_db(cursor: Any, product_ids: list[int], *, for_update: bool) -> list[LiveProduct]:
    sql = SELECT_ALLOWLIST_SQL if for_update else SELECT_ALLOWLIST_SQL_NO_LOCK
    cursor.execute(sql, (product_ids,))
    out: list[LiveProduct] = []
    for row in cursor.fetchall():
        if isinstance(row, dict):
            payload = row
        else:
            payload = {
                "id": row[0],
                "sku": row[1],
                "base_price": row[2],
                "is_active": row[3],
                "is_available": row[4],
                "deleted_at": row[5],
                "brand_id": row[6],
                "category_id": row[7],
                "name": row[8],
                "slug": row[9],
            }
        out.append(_record_to_live_product(payload))
    return out


class AsyncpgApplyConnection:
    """Sync facade over asyncpg (requirements.txt) for one APPLY transaction.

    Matches the DbConnection protocol used by apply_allowlist / FakeConn tests.
    """

    def __init__(self, database_url: str):
        try:
            import asyncpg
        except ImportError as exc:  # pragma: no cover
            raise ApplyAbort(
                f"asyncpg_not_installed:required={RUNTIME_DB_DEPENDENCY}"
            ) from exc
        self._asyncpg = asyncpg
        self._loop = asyncio.new_event_loop()
        self._conn = self._loop.run_until_complete(
            asyncpg.connect(normalize_database_url(database_url))
        )
        self._tx: Any | None = None

    def cursor(self, *args: Any, **kwargs: Any) -> AsyncpgApplyCursor:
        del args, kwargs
        if self._tx is None:
            self._tx = self._conn.transaction()
            self._loop.run_until_complete(self._tx.start())
        return AsyncpgApplyCursor(self)

    def commit(self) -> None:
        if self._tx is not None:
            self._loop.run_until_complete(self._tx.commit())
            self._tx = None

    def rollback(self) -> None:
        if self._tx is not None:
            self._loop.run_until_complete(self._tx.rollback())
            self._tx = None

    def close(self) -> None:
        try:
            if self._tx is not None:
                self._loop.run_until_complete(self._tx.rollback())
                self._tx = None
            self._loop.run_until_complete(self._conn.close())
        finally:
            self._loop.close()


class AsyncpgApplyCursor:
    def __init__(self, owner: AsyncpgApplyConnection):
        self._owner = owner
        self.rowcount = 0
        self._rows: list[tuple[Any, ...]] = []

    def execute(self, sql: str, params: Any = None) -> None:
        converted = _percent_s_to_asyncpg(sql)
        args = tuple(params) if params is not None else ()
        sql_l = " ".join(sql.lower().split())
        if sql_l.startswith("select "):
            records = self._owner._loop.run_until_complete(
                self._owner._conn.fetch(converted, *args)
            )
            self._rows = [tuple(record[key] for key in record.keys()) for record in records]
            self.rowcount = len(self._rows)
            return
        if sql_l.startswith("update "):
            status = self._owner._loop.run_until_complete(
                self._owner._conn.execute(converted, *args)
            )
            # asyncpg returns e.g. "UPDATE 1"
            parts = str(status).split()
            self.rowcount = int(parts[-1]) if parts and parts[-1].isdigit() else 0
            self._rows = []
            return
        raise ApplyAbort(f"unsupported_sql:{sql_l[:40]}")

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


async def fetch_allowlist_readonly_async(
    database_url: str, product_ids: list[int]
) -> list[LiveProduct]:
    """SELECT-only allowlist re-read via asyncpg (no FOR UPDATE, no writes)."""
    import asyncpg

    conn = await asyncpg.connect(normalize_database_url(database_url))
    try:
        sql = _percent_s_to_asyncpg(SELECT_ALLOWLIST_SQL_NO_LOCK)
        records = await conn.fetch(sql, product_ids)
        return [
            _record_to_live_product({key: record[key] for key in record.keys()})
            for record in records
        ]
    finally:
        await conn.close()


def fetch_allowlist_readonly(database_url: str, product_ids: list[int]) -> list[LiveProduct]:
    return asyncio.run(fetch_allowlist_readonly_async(database_url, product_ids))


def connect_runtime_db(database_url: str) -> AsyncpgApplyConnection:
    """Open the project-runtime PostgreSQL client used by future APPLY."""
    return AsyncpgApplyConnection(database_url)


def assert_production_apply_authorized(
    *,
    apply: bool,
    confirm_production_write: bool,
    confirm_plan_sha256: str,
    plan_csv_sha256: str,
    db_host: str,
    database_url: str = "",
) -> None:
    if not apply:
        return
    host = (db_host or "").lower()
    url_host = ""
    if database_url:
        url_host = (urlparse(database_url).hostname or "").lower()
    targets_prod = PROD_HOST_MARKER in host or PROD_HOST_MARKER in url_host
    # Explicit production apply always requires Category B + confirmation tokens,
    # even for local dry-lab hosts when --apply is requested against "production" mode.
    if not confirm_production_write:
        raise ApplyAbort("missing_confirm_production_write")
    if confirm_plan_sha256 != plan_csv_sha256:
        raise ApplyAbort(
            f"confirm_plan_sha256_mismatch:expected={plan_csv_sha256}:got={confirm_plan_sha256}"
        )
    if os.getenv(ALLOW_ENV, "").strip() != "1":
        raise ApplyAbort(f"missing_{ALLOW_ENV}")
    if os.getenv(CATEGORY_ENV, "").strip().upper() != "B":
        raise ApplyAbort(f"missing_{CATEGORY_ENV}=B")
    if targets_prod and not confirm_production_write:
        raise ApplyAbort("production_host_requires_confirm")


def apply_allowlist(
    conn: DbConnection,
    plan_rows: list[PlanRow],
    *,
    dry_run: bool = True,
    backup_dir: Path | None = None,
) -> ApplyRunResult:
    if len(plan_rows) != REVIEWED_ALLOWLIST_COUNT:
        raise ApplyAbort(f"allowlist_count_invalid:{len(plan_rows)}")

    product_ids = [row.product_id for row in plan_rows]
    cursor = conn.cursor()
    try:
        live = rows_from_db(cursor, product_ids, for_update=not dry_run)
        guard = stale_guard(plan_rows, live)
        if not guard.ok:
            conn.rollback()
            return ApplyRunResult(
                mode="dry_run" if dry_run else "apply_aborted",
                production_apply_executed=False,
                aborted=True,
                abort_reason="stale_snapshot_guard_failed",
                allowlist_count=len(plan_rows),
                expected_price_changes=REVIEWED_PRICE_CHANGES,
                expected_availability_changes=REVIEWED_AVAILABILITY_CHANGES,
                expected_active_changes=REVIEWED_ACTIVE_CHANGES,
                stale_guard=guard.as_dict(),
                dry_run_lines=[asdict(line) for line in build_dry_run_lines(plan_rows)],
                price_change_stats=price_change_stats(plan_rows),
                transaction_safeguards={
                    "single_transaction": True,
                    "abort_before_first_write": True,
                    "partial_commit_allowed": False,
                },
                implementation_ready=True,
            )

        backup_path = ""
        backup_sha = ""
        rollback_path = ""
        if backup_dir is not None:
            bpath, bsha, rpath = write_pre_apply_backup(live, output_dir=backup_dir)
            backup_path = str(bpath)
            backup_sha = bsha
            rollback_path = str(rpath)

        dry_lines = build_dry_run_lines(plan_rows)
        stats = price_change_stats(plan_rows)
        if dry_run:
            conn.rollback()
            return ApplyRunResult(
                mode="dry_run",
                production_apply_executed=False,
                aborted=False,
                allowlist_count=len(plan_rows),
                expected_price_changes=REVIEWED_PRICE_CHANGES,
                expected_availability_changes=REVIEWED_AVAILABILITY_CHANGES,
                expected_active_changes=REVIEWED_ACTIVE_CHANGES,
                stale_guard=guard.as_dict(),
                dry_run_lines=[asdict(line) for line in dry_lines],
                price_change_stats=stats,
                backup_path=backup_path,
                backup_sha256=backup_sha,
                rollback_sql_path=rollback_path,
                updated_count=0,
                transaction_safeguards={
                    "single_transaction": True,
                    "for_update_lock": False,
                    "mutable_columns": list(MUTABLE_COLUMNS),
                    "forbidden_columns": list(FORBIDDEN_MUTATION_COLUMNS),
                    "affected_count_must_equal": len(plan_rows),
                    "partial_commit_allowed": False,
                },
                implementation_ready=True,
            )

        updated = 0
        for plan in plan_rows:
            cursor.execute(
                UPDATE_SQL,
                (
                    str(plan.proposed_base_price),
                    plan.proposed_is_available,
                    plan.product_id,
                    plan.sku,
                    None
                    if plan.expected_base_price is None
                    else str(plan.expected_base_price),
                    plan.expected_is_available,
                    plan.expected_is_active,
                ),
            )
            if cursor.rowcount != 1:
                conn.rollback()
                raise ApplyAbort(
                    f"affected_row_mismatch:id={plan.product_id}:rowcount={cursor.rowcount}"
                )
            updated += 1

        if updated != len(plan_rows):
            conn.rollback()
            raise ApplyAbort(f"updated_count_mismatch:expected={len(plan_rows)}:observed={updated}")

        # Post-write verification inside the same transaction.
        verify = rows_from_db(cursor, product_ids, for_update=True)
        by_id = {row.id: row for row in verify}
        for plan in plan_rows:
            live_row = by_id.get(plan.product_id)
            if live_row is None:
                conn.rollback()
                raise ApplyAbort(f"post_write_missing:{plan.product_id}")
            if live_row.deleted_at:
                conn.rollback()
                raise ApplyAbort(f"post_write_deleted:{plan.product_id}")
            if not _decimal_equal(live_row.base_price, plan.proposed_base_price):
                conn.rollback()
                raise ApplyAbort(f"post_write_price_mismatch:{plan.sku}")
            if live_row.is_available is not plan.proposed_is_available:
                conn.rollback()
                raise ApplyAbort(f"post_write_availability_mismatch:{plan.sku}")
            if live_row.is_active is not plan.expected_is_active:
                conn.rollback()
                raise ApplyAbort(f"post_write_active_mutated:{plan.sku}")

        conn.commit()
        return ApplyRunResult(
            mode="apply_committed",
            production_apply_executed=True,
            aborted=False,
            allowlist_count=len(plan_rows),
            expected_price_changes=REVIEWED_PRICE_CHANGES,
            expected_availability_changes=REVIEWED_AVAILABILITY_CHANGES,
            expected_active_changes=REVIEWED_ACTIVE_CHANGES,
            stale_guard=guard.as_dict(),
            dry_run_lines=[asdict(line) for line in dry_lines],
            price_change_stats=stats,
            backup_path=backup_path,
            backup_sha256=backup_sha,
            rollback_sql_path=rollback_path,
            updated_count=updated,
            transaction_safeguards={
                "single_transaction": True,
                "for_update_lock": True,
                "mutable_columns": list(MUTABLE_COLUMNS),
                "forbidden_columns": list(FORBIDDEN_MUTATION_COLUMNS),
                "affected_count_must_equal": len(plan_rows),
                "post_write_verification": True,
                "partial_commit_allowed": False,
            },
            implementation_ready=True,
        )
    except Exception:
        conn.rollback()
        raise


def isolation_fingerprint(live_rows: list[LiveProduct]) -> dict[str, str]:
    """Deterministic fingerprint of allowlisted rows for before/after proofs."""
    parts = []
    for row in sorted(live_rows, key=lambda item: item.id):
        parts.append(
            f"{row.id}|{row.sku}|{row.base_price}|{row.is_active}|{row.is_available}|{row.deleted_at}"
        )
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return {"allowlist_fingerprint_sha256": digest, "count": str(len(live_rows))}


def isolation_proof_queries(allowlist_ids: list[int]) -> dict[str, str]:
    """SQL sufficient to prove only allowlisted IDs change approved columns."""
    id_list = ",".join(str(i) for i in sorted(allowlist_ids))
    return {
        "allowlist_fingerprint": (
            "SELECT id, sku, base_price, is_active, is_available, deleted_at "
            f"FROM products WHERE id IN ({id_list}) ORDER BY id"
        ),
        "non_allowlist_fingerprint": (
            "SELECT md5(string_agg(md5(ROW(id, sku, base_price, is_active, is_available, "
            "deleted_at, brand_id, category_id, name, slug)::text), ',' ORDER BY id)) "
            f"FROM products WHERE id NOT IN ({id_list})"
        ),
        "product_images_fingerprint": (
            "SELECT md5(string_agg(md5(ROW(id, product_id, image_url, is_primary, "
            "display_order)::text), ',' ORDER BY id)) FROM product_images"
        ),
        "brands_count": "SELECT COUNT(*) FROM brands",
        "categories_count": "SELECT COUNT(*) FROM categories",
        "products_count": "SELECT COUNT(*) FROM products",
        "deleted_allowlist": (
            f"SELECT id, sku FROM products WHERE id IN ({id_list}) AND deleted_at IS NOT NULL"
        ),
    }


def assert_isolation_queries_match_schema() -> None:
    """Fail closed if verification SQL drifts from the ProductImage schema contract.

    Prefers live SQLAlchemy metadata when importable; always cross-checks the
    checked-in model source so CI and offline unit runs agree.
    """
    repo_root = Path(__file__).resolve().parents[2]
    model_path = repo_root / "app" / "db" / "models" / "product.py"
    if not model_path.is_file():
        raise ApplyAbort(f"product_model_missing:{model_path}")
    model_src = model_path.read_text(encoding="utf-8")
    image_match = re.search(
        r"class ProductImage\(Base\):(.*?)(?:\nclass |\Z)",
        model_src,
        flags=re.S,
    )
    if image_match is None:
        raise ApplyAbort("product_image_class_missing_in_model_source")
    image_body = image_match.group(1)
    if "image_url" not in image_body:
        raise ApplyAbort("product_images_model_missing_image_url")
    if re.search(r"(?<![A-Za-z0-9_])url(?![A-Za-z0-9_])\s*:", image_body):
        raise ApplyAbort("product_images_model_has_bare_url_column")
    for required in (
        "__tablename__ = \"product_images\"",
        "product_id",
        "is_primary",
        "display_order",
    ):
        if required not in image_body and required not in model_src:
            # tablename lives in class body; product_id etc. too
            if required.startswith("__tablename__") and required not in image_body:
                raise ApplyAbort("product_images_tablename_mismatch")
            if not required.startswith("__tablename__") and required not in image_body:
                raise ApplyAbort(f"product_images_model_missing:{required}")

    product_match = re.search(
        r"class Product\(Base\):(.*?)(?:\nclass |\Z)",
        model_src,
        flags=re.S,
    )
    if product_match is None:
        raise ApplyAbort("product_class_missing_in_model_source")
    product_body = product_match.group(1)
    for col in (
        "base_price",
        "is_active",
        "is_available",
        "deleted_at",
        "brand_id",
        "category_id",
        "sku",
        "name",
        "slug",
    ):
        if col not in product_body:
            raise ApplyAbort(f"products_model_missing:{col}")

    queries = isolation_proof_queries([1])
    images_sql = queries["product_images_fingerprint"]
    if "image_url" not in images_sql:
        raise ApplyAbort("isolation_sql_missing_image_url")
    bare_url = re.search(r"(?<![A-Za-z0-9_])url(?![A-Za-z0-9_])", images_sql)
    if bare_url is not None:
        raise ApplyAbort("isolation_sql_uses_forbidden_url_column")

    # Optional live ORM metadata check when app deps are installed (CI).
    try:
        from app.db.models.product import Brand, Category, Product, ProductImage
    except Exception:  # noqa: BLE001
        return

    product_cols = {column.key for column in Product.__table__.columns}
    image_cols = {column.key for column in ProductImage.__table__.columns}
    brand_cols = {column.key for column in Brand.__table__.columns}
    category_cols = {column.key for column in Category.__table__.columns}
    required_product = {
        "id",
        "sku",
        "base_price",
        "is_active",
        "is_available",
        "deleted_at",
        "brand_id",
        "category_id",
        "name",
        "slug",
    }
    missing_product = required_product - product_cols
    if missing_product:
        raise ApplyAbort(f"products_schema_missing:{sorted(missing_product)}")
    required_images = {"id", "product_id", "image_url", "is_primary", "display_order"}
    missing_images = required_images - image_cols
    if missing_images:
        raise ApplyAbort(f"product_images_schema_missing:{sorted(missing_images)}")
    if "id" not in brand_cols or "id" not in category_cols:
        raise ApplyAbort("brand_or_category_schema_missing_id")


def post_apply_verification_contract() -> dict[str, Any]:
    return {
        "database": [
            "exactly_158_reviewed_products_present",
            "proposed_prices_match",
            "proposed_availability_match",
            "is_active_unchanged",
            "unrelated_products_unchanged",
            "no_product_images_mutation",
            "no_category_mutation",
            "no_brand_mutation",
            "no_create",
            "no_delete",
        ],
        "isolation_proof_queries": "catalog_target.sales_wave_apply.isolation_proof_queries",
        "storefront_api_smoke": [
            "sample_public_product_responses",
            "price_displayed_correctly",
            "product_available_for_purchase",
            "image_present",
            "checkout_price_source_agrees_with_db",
        ],
        "preferred_smoke_sku_if_present": "4602-32",
        "real_payment": False,
    }


def writer_contract_summary() -> dict[str, Any]:
    return {
        "wave": "INSIZE_SALES_WAVE_1",
        "mutable_columns": list(MUTABLE_COLUMNS),
        "forbidden_columns": list(FORBIDDEN_MUTATION_COLUMNS),
        "reviewed_allowlist_count": REVIEWED_ALLOWLIST_COUNT,
        "reviewed_price_changes": REVIEWED_PRICE_CHANGES,
        "reviewed_availability_changes": REVIEWED_AVAILABILITY_CHANGES,
        "reviewed_active_changes": REVIEWED_ACTIVE_CHANGES,
        "reviewed_snapshot_timestamp": REVIEWED_SNAPSHOT_TIMESTAMP,
        "reviewed_snapshot_sha256": REVIEWED_SNAPSHOT_SHA256,
        "reviewed_plan_csv_sha256": REVIEWED_PLAN_CSV_SHA256,
        "reviewed_plan_json_sha256": REVIEWED_PLAN_JSON_SHA256,
        "runtime_db_driver": RUNTIME_DB_DRIVER,
        "runtime_db_dependency": RUNTIME_DB_DEPENDENCY,
        "stale_snapshot_guard": StaleSnapshotGuard(writer_implemented=True).as_dict(),
        "required_live_fields": list(APPLY_REQUIRED_LIVE_FIELDS) + ["deleted_at"],
        "default_mode": "DRY_RUN",
        "production_authorization": {
            "flags": ["--apply", "--confirm-production-write", "--confirm-plan-sha256"],
            "env": [f"{ALLOW_ENV}=1", f"{CATEGORY_ENV}=B"],
        },
        "post_apply_verification": post_apply_verification_contract(),
    }
