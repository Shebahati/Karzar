"""Guarded Category B APPLY for AST price UPDATE + product CREATE."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Protocol

from catalog_target.ast_price_catalog_constants import (
    OWNER_AUTH_APPLY,
    OWNER_AUTH_ROLLBACK,
    PRICING_POLICY_ID,
    SOURCE_ARCHIVE_SHA256,
)
from catalog_target.ast_price_catalog_reconcile import CREATE_APPROVAL_OWNER
from catalog_target.sales_wave_apply import ApplyAbort, normalize_database_url

CREATE_APPROVAL_REQUIRED = CREATE_APPROVAL_OWNER


class DbCursor(Protocol):
    rowcount: int

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> Any: ...


class DbConnection(Protocol):
    def cursor(self, *args: Any, **kwargs: Any) -> DbCursor: ...

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
    source_checksum: str = ""
    archive_checksum: str = ""
    apply_eligible: str = ""
    approval_status: str = ""


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
    production_apply_executed: bool = False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_price_strict(raw: str, *, field_name: str) -> Decimal | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ApplyAbort(f"malformed_price:{field_name}:{raw}") from None
    if value < 0:
        raise ApplyAbort(f"negative_price:{field_name}:{raw}")
    return value


def parse_price(raw: str) -> Decimal | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def assert_unique_update_product_ids(plan_rows: list[UpdatePlanRow]) -> None:
    seen: set[int] = set()
    for row in plan_rows:
        if row.product_id in seen:
            raise ApplyAbort(f"duplicate_update_product_id:{row.product_id}")
        seen.add(row.product_id)


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
                    expected_current_price=parse_price(
                        r.get("expected_current_price") or r.get("current_price") or ""
                    ),
                    proposed_price=parse_price(r.get("proposed_price") or ""),
                )
            )
    assert_unique_update_product_ids(rows)
    return rows


def load_create_plan(
    path: Path,
    *,
    expected_manifest_sha256: str | None = None,
    require_owner_approval: bool = True,
) -> list[CreatePlanRow]:
    if expected_manifest_sha256:
        actual = sha256_file(path)
        if actual != expected_manifest_sha256:
            raise ApplyAbort(
                f"create_manifest_sha256_mismatch:expected={expected_manifest_sha256}:got={actual}"
            )
    rows: list[CreatePlanRow] = []
    seen_sku: set[str] = set()
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("apply_eligible") or "").strip().upper() != "YES":
                continue
            approval = (r.get("approval_status") or "").strip()
            if require_owner_approval and approval != CREATE_APPROVAL_REQUIRED:
                continue
            if (r.get("pricing_policy_id") or "") != PRICING_POLICY_ID:
                raise ApplyAbort(f"create_row_policy_mismatch:{r.get('sku')}")
            archive = (r.get("archive_checksum") or "").strip()
            if archive and archive != SOURCE_ARCHIVE_SHA256:
                raise ApplyAbort(f"create_row_archive_checksum_mismatch:{r.get('sku')}")
            sku = str(r["sku"]).strip()
            if sku in seen_sku:
                raise ApplyAbort(f"duplicate_create_sku_in_manifest:{sku}")
            seen_sku.add(sku)
            is_avail = str(r.get("is_available", "false")).lower() in {"1", "true", "t"}
            if is_avail:
                raise ApplyAbort(f"create_row_must_be_unavailable:{sku}")
            rows.append(
                CreatePlanRow(
                    sku=sku,
                    brand_id=int(r["brand_id"]),
                    category_id=int(r["category_id"]),
                    name=str(r["name"]),
                    base_price=parse_price_strict(r.get("base_price") or "", field_name="base_price"),
                    is_available=False,
                    is_active=str(r.get("is_active", "true")).lower() in {"1", "true", "t"},
                    source_checksum=str(r.get("source_checksum") or ""),
                    archive_checksum=archive,
                    apply_eligible="YES",
                    approval_status=approval,
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


def fetch_live_products_sql(product_ids: list[int]) -> str:
    return """
SELECT id, sku, base_price::text
FROM products
WHERE id = ANY(%s) AND deleted_at IS NULL
FOR UPDATE
"""


def apply_updates_sql(
    conn: DbConnection,
    plan_rows: list[UpdatePlanRow],
    *,
    dry_run: bool,
    product_id_allowlist: set[int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    scoped = plan_rows
    if product_id_allowlist is not None:
        scoped = [r for r in plan_rows if r.product_id in product_id_allowlist]
    if dry_run:
        return 0, []

    sql = build_update_sql()
    journal_updates: list[dict[str, Any]] = []
    written = 0
    for row in scoped:
        cur = conn.cursor()
        cur.execute(
            sql,
            (
                row.proposed_price,
                row.product_id,
                row.sku,
                row.expected_current_price,
            ),
        )
        if cur.rowcount != 1:
            conn.rollback()
            raise ApplyAbort(f"update_rowcount_mismatch:product_id={row.product_id}:rowcount={cur.rowcount}")
        written += 1
        journal_updates.append(
            {
                "product_id": row.product_id,
                "sku": row.sku,
                "before_base_price": str(row.expected_current_price or ""),
                "after_base_price": str(row.proposed_price or ""),
            }
        )
    return written, journal_updates


async def create_products_ast_batch(
    db: Any,
    plan_rows: list[CreatePlanRow],
) -> list[int]:
    """AST one-time CREATE: ProductCreate validation, flush-only, no Hesabfa."""
    from app.crud.product import check_sku_exists, create_product
    from app.schemas.product import ProductCreate
    from app.utils.category_validation import ensure_brand_exists, ensure_selectable_product_category

    created_ids: list[int] = []
    for row in plan_rows:
        if await check_sku_exists(db, row.sku):
            raise ApplyAbort(f"duplicate_sku_at_create:{row.sku}")
        await ensure_selectable_product_category(db, row.category_id, required=True)
        await ensure_brand_exists(db, row.brand_id)
        payload = ProductCreate(
            sku=row.sku,
            name=row.name,
            category_id=row.category_id,
            brand_id=row.brand_id,
            base_price=row.base_price,
            is_available=False,
            is_active=row.is_active,
        )
        product = await create_product(db, payload)
        created_ids.append(int(product.id))
    return created_ids


def apply_creates_sql(
    conn: DbConnection,
    plan_rows: list[CreatePlanRow],
    *,
    dry_run: bool,
    sku_allowlist: set[str] | None = None,
    next_product_id: Callable[[], int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Sync INSERT path for transactional tests and guarded apply without Hesabfa."""
    scoped = plan_rows
    if sku_allowlist is not None:
        scoped = [r for r in plan_rows if r.sku in sku_allowlist]
    if dry_run:
        return 0, []

    insert_sql = """
INSERT INTO products (
    sku, name, brand_id, category_id, base_price, is_available, is_active,
    stock_quantity, slug, created_at, updated_at
) VALUES (%s, %s, %s, %s, %s, false, %s, 0, %s, NOW(), NOW())
RETURNING id
"""
    journal: list[dict[str, Any]] = []
    written = 0
    pid_factory = next_product_id or (lambda: 0)
    for row in scoped:
        slug = f"ast-{row.sku.lower()}"[:255]
        cur = conn.cursor()
        cur.execute(
            insert_sql,
            (
                row.sku,
                row.name,
                row.brand_id,
                row.category_id,
                row.base_price,
                row.is_active,
                slug,
            ),
        )
        if cur.rowcount != 1:
            conn.rollback()
            raise ApplyAbort(f"create_rowcount_mismatch:sku={row.sku}")
        new_id = pid_factory()
        if hasattr(cur, "fetchone"):
            fetched = cur.fetchone()
            if fetched:
                new_id = int(fetched[0])
        written += 1
        journal.append({"product_id": new_id, "sku": row.sku, "base_price": str(row.base_price or "")})
    return written, journal


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


def post_commit_verify_updates(
    conn: DbConnection,
    journal_updates: list[dict[str, Any]],
) -> bool:
    if not journal_updates:
        return True
    ids = [int(r["product_id"]) for r in journal_updates]
    cur = conn.cursor()
    cur.execute(
        "SELECT id, sku, base_price::text FROM products WHERE id = ANY(%s) AND deleted_at IS NULL",
        (ids,),
    )
    rows = cur.fetchall() if hasattr(cur, "fetchall") else []
    live = {int(r[0]): {"sku": r[1], "base_price": r[2]} for r in rows}
    for entry in journal_updates:
        pid = int(entry["product_id"])
        row = live.get(pid)
        if row is None:
            return False
        if row["sku"] != entry["sku"]:
            return False
        if parse_price(row["base_price"]) != parse_price(str(entry["after_base_price"])):
            return False
    return True


def execute_ast_catalog_apply(
    conn: DbConnection,
    update_rows: list[UpdatePlanRow],
    create_rows: list[CreatePlanRow],
    *,
    dry_run: bool,
    batch_id: str,
    journal_dir: Path,
    metadata: dict[str, Any],
    live_by_id: dict[int, dict[str, str]] | None = None,
    create_executor: Callable[[DbConnection, list[CreatePlanRow]], tuple[int, list[dict[str, Any]]]] | None = None,
) -> ApplyResult:
    assert_unique_update_product_ids(update_rows)
    guard = verify_update_stale_guard(update_rows, live_by_id or {})
    if update_rows and not guard.ok:
        return ApplyResult(
            mode="dry_run" if dry_run else "apply",
            committed=False,
            updates_written=0,
            creates_written=0,
            batch_id=batch_id,
            stale_guard=guard,
            aborted_reason="BLOCKED_STALE_GUARD",
            production_apply_executed=False,
        )

    journal_path = journal_dir / f"AST_APPLY_{batch_id}.json"
    if dry_run:
        write_journal(
            journal_path,
            {
                "batch_id": batch_id,
                "mode": "DRY_RUN",
                "committed": False,
                "metadata": metadata,
                "updates_planned": len(update_rows),
                "creates_planned": len(create_rows),
                "stale_guard": guard.__dict__,
            },
        )
        return ApplyResult(
            mode="dry_run",
            committed=False,
            updates_written=0,
            creates_written=0,
            batch_id=batch_id,
            stale_guard=guard,
            journal_path=str(journal_path),
            production_apply_executed=False,
        )

    def _default_create(c: DbConnection, rows: list[CreatePlanRow]) -> tuple[int, list[dict[str, Any]]]:
        return apply_creates_sql(c, rows, dry_run=False)

    create_fn = create_executor or _default_create
    try:
        updates_written, update_journal = apply_updates_sql(conn, update_rows, dry_run=False)
        creates_written, create_journal = create_fn(conn, create_rows)
        journal = {
            "batch_id": batch_id,
            "mode": "APPLY",
            "committed": True,
            "metadata": metadata,
            "updates": update_journal,
            "creates": create_journal,
            "stale_guard": guard.__dict__,
        }
        write_journal(journal_path, journal)
        conn.commit()
        if not post_commit_verify_updates(conn, update_journal):
            raise ApplyAbort("POST_COMMIT_VERIFY_FAILED")
        return ApplyResult(
            mode="apply",
            committed=True,
            updates_written=updates_written,
            creates_written=creates_written,
            batch_id=batch_id,
            stale_guard=guard,
            journal_path=str(journal_path),
            production_apply_executed=True,
        )
    except ApplyAbort:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise


def load_apply_journal(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rollback_from_journal(
    conn: DbConnection,
    journal: dict[str, Any],
    *,
    dry_run: bool,
) -> int:
    if not journal.get("committed"):
        raise ApplyAbort("rollback_journal_not_committed")
    updates = journal.get("updates") or []
    creates = journal.get("creates") or []
    if dry_run:
        return 0

    rolled = 0
    update_sql = """
UPDATE products
SET base_price = %s, updated_at = NOW()
WHERE id = %s AND sku = %s AND deleted_at IS NULL
  AND base_price IS NOT DISTINCT FROM %s
"""
    for row in updates:
        cur = conn.cursor()
        cur.execute(
            update_sql,
            (
                parse_price(str(row.get("before_base_price") or "")),
                int(row["product_id"]),
                row["sku"],
                parse_price(str(row.get("after_base_price") or "")),
            ),
        )
        if cur.rowcount != 1:
            conn.rollback()
            raise ApplyAbort(f"rollback_update_rowcount_mismatch:{row.get('product_id')}")
        rolled += 1

    delete_sql = """
UPDATE products
SET deleted_at = NOW(), is_active = false, is_available = false, updated_at = NOW()
WHERE id = %s AND sku = %s AND deleted_at IS NULL
  AND NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = products.id)
"""
    for row in creates:
        cur = conn.cursor()
        cur.execute(delete_sql, (int(row["product_id"]), row["sku"]))
        if cur.rowcount != 1:
            conn.rollback()
            raise ApplyAbort(f"rollback_create_rowcount_mismatch:{row.get('product_id')}")
        rolled += 1
    conn.commit()
    return rolled


def new_batch_id() -> str:
    return datetime_now_utc_slug()


def datetime_now_utc_slug() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def build_rollback_manifest_from_updates(plan_rows: list[UpdatePlanRow]) -> list[dict[str, str]]:
    return [
        {
            "product_id": str(row.product_id),
            "sku": row.sku,
            "rollback_base_price": str(row.expected_current_price or ""),
            "applied_proposed_price": str(row.proposed_price or ""),
        }
        for row in plan_rows
    ]


def rollback_updates_sql(
    conn: DbConnection,
    journal_rows: list[dict[str, str]],
    *,
    dry_run: bool,
) -> int:
    """Legacy helper — prefer rollback_from_journal for committed APPLY journals."""
    if dry_run:
        return 0
    written = 0
    sql = """
UPDATE products
SET base_price = %s, updated_at = NOW()
WHERE id = %s AND sku = %s AND deleted_at IS NULL
"""
    for row in journal_rows:
        price = parse_price(row.get("rollback_base_price") or "")
        cur = conn.cursor()
        cur.execute(sql, (price, int(row["product_id"]), row["sku"]))
        if cur.rowcount != 1:
            conn.rollback()
            raise ApplyAbort(f"legacy_rollback_rowcount_mismatch:{row.get('product_id')}")
        written += 1
    return written


async def apply_creates_via_service(
    plan_rows: list[CreatePlanRow],
    *,
    dry_run: bool,
    sku_allowlist: set[str] | None,
    session_factory: Any,
) -> int:
    """Deprecated path — use create_products_ast_batch (no Hesabfa, batch transaction)."""
    scoped = plan_rows
    if sku_allowlist is not None:
        scoped = [r for r in plan_rows if r.sku in sku_allowlist]
    if dry_run:
        return 0
    async with session_factory() as db:
        async with db.begin():
            return len(await create_products_ast_batch(db, scoped))
