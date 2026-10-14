"""INSIZE #258 final commercial reconcile — shared hash, guards, APPLY/rollback core."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from catalog_target.sales_wave_apply import (
    ApplyAbort,
    normalize_database_url,
)
from catalog_target.supplier_stock import FreshnessPolicy, file_sha256

OWNER_SOURCE_SHA256 = "8324b2c175a703ab0ff7364da4a33f82c440d592cdc10d990c133bed39ac2989"
OWNER_AUTH_APPLY = "AUTHORIZE_INSIZE_FINAL_COMMERCIAL_APPLY"
OWNER_AUTH_ROLLBACK = "AUTHORIZE_INSIZE_FINAL_COMMERCIAL_ROLLBACK"
DEFAULT_ATTESTED_SOURCE_AGE_DAYS = 7

PLACEHOLDER_ILIKE = (
    "placeholder",
    "woocommerce-placeholder",
    "no-image",
    "no_image",
    "noimage",
    "default-image",
    "default_image",
    "karzar-editorial",
    "/images/placeholders/",
)

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE)\b",
    re.I,
)

MUTABLE_COLUMNS = ("is_available", "base_price")
FORBIDDEN_MUTATION_COLUMNS = (
    "is_active",
    "manufacturer_code",
    "sku",
    "name",
    "brand_id",
    "category_id",
    "original_price",
    "slug",
    "deleted_at",
)

PLAN_CSV_NAME = "INSIZE_COMMERCIAL_RECONCILE_PLAN.csv"
ROLLBACK_CSV_NAME = "INSIZE_COMMERCIAL_ROLLBACK_MANIFEST.csv"
SOURCE_MANIFEST_NAME = "SOURCE_MANIFEST.json"
COMMERCIAL_DELTA_NAME = "COMMERCIAL_DELTA.json"


def sha256_file(path: Path) -> str:
    return file_sha256(path)


def state_hash(row: dict[str, str]) -> str:
    payload = "|".join(
        [
            str(row.get("product_id", "")),
            row.get("sku", ""),
            row.get("brand_id", ""),
            row.get("is_active", ""),
            row.get("is_available", ""),
            row.get("base_price", ""),
            row.get("deleted_at", "") or "NULL",
            row.get("image_present", ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _image_exists_sql(alias: str = "p") -> str:
    clauses = " AND ".join(
        f"pi.image_url NOT ILIKE '%{tok}%'" for tok in PLACEHOLDER_ILIKE
    )
    return f"""
    EXISTS (
      SELECT 1 FROM product_images pi
      WHERE pi.product_id = {alias}.id
        AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
        AND {clauses}
    )
    """


def parse_bool_text(raw: str) -> bool:
    text = (raw or "").strip().lower()
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    raise ApplyAbort(f"malformed_bool:{raw!r}")


def parse_price_text(raw: str) -> Decimal | None:
    s = (raw or "").strip()
    if not s or s.lower() in {"none", "null"}:
        return None
    try:
        val = Decimal(s)
    except InvalidOperation as exc:
        raise ApplyAbort(f"malformed_price:{raw!r}") from exc
    if val == 0:
        raise ApplyAbort("forbidden_zero_base_price")
    return val.quantize(Decimal("1"))


@dataclass
class PlanRow:
    product_id: int
    sku: str
    combined_action: str
    availability_action: str
    price_action: str
    expected_current_hash: str
    proposed_is_available: bool | None
    proposed_base_price: Decimal | None
    current_is_available: bool
    current_base_price: Decimal | None


@dataclass
class RollbackRow:
    product_id: int
    sku: str
    pre_is_available: bool
    pre_base_price: Decimal | None
    proposed_is_available: bool
    proposed_base_price: Decimal | None
    expected_current_hash: str


@dataclass
class StaleGuardResult:
    ok: bool
    expected_count: int
    match_count: int
    mismatches: list[dict[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApplyJournalRow:
    product_id: int
    sku: str
    action: str
    before_is_available: bool | None
    after_is_available: bool | None
    before_base_price: str
    after_base_price: str
    expected_current_hash: str
    actual_prewrite_hash: str
    success: bool
    error: str = ""


@dataclass
class ApplyResult:
    mode: str
    committed: bool
    rows_written: int
    batch_id: str
    stale_guard: StaleGuardResult
    journal_path: Path | None = None
    production_apply_executed: bool = False
    aborted_reason: str = ""
    journal: dict[str, Any] = field(default_factory=dict)


def load_source_manifest(evidence_dir: Path) -> dict[str, Any]:
    path = evidence_dir / SOURCE_MANIFEST_NAME
    if not path.is_file():
        raise ApplyAbort(f"missing_source_manifest:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def effective_source_age_days(
    manifest: dict[str, Any],
    *,
    now: datetime | None = None,
    attestation_at: datetime | None = None,
    attested_source_age_days: int | None = None,
) -> int:
    """effective_age = attested_approx_age + elapsed_since_attestation (real time)."""
    now = now or datetime.now(UTC)
    inspected_raw = manifest.get("inspected_at")
    if attestation_at is None:
        if not inspected_raw:
            raise ApplyAbort("missing_owner_attestation_timestamp")
        attestation_at = datetime.fromisoformat(str(inspected_raw).replace("Z", "+00:00"))
    if attestation_at.tzinfo is None:
        attestation_at = attestation_at.replace(tzinfo=UTC)
    if attested_source_age_days is None:
        attested_source_age_days = DEFAULT_ATTESTED_SOURCE_AGE_DAYS
    elapsed = (now - attestation_at.astimezone(UTC)).total_seconds() / 86400.0
    if elapsed < 0:
        raise ApplyAbort("attestation_timestamp_in_future")
    return int(attested_source_age_days + elapsed)


def classify_owner_freshness(
    manifest: dict[str, Any],
    *,
    now: datetime | None = None,
    attestation_at: datetime | None = None,
    attested_source_age_days: int | None = None,
    policy: FreshnessPolicy | None = None,
) -> tuple[int, str]:
    age = effective_source_age_days(
        manifest,
        now=now,
        attestation_at=attestation_at,
        attested_source_age_days=attested_source_age_days,
    )
    classification = (policy or FreshnessPolicy()).classify(age)
    return age, classification


def validate_source_sha256(path: Path, expected: str = OWNER_SOURCE_SHA256) -> None:
    if not path.is_file():
        raise ApplyAbort(f"missing_source_artifact:{path}")
    observed = sha256_file(path)
    if observed != expected:
        raise ApplyAbort(f"source_sha_mismatch:expected={expected}:got={observed}")


def load_plan_rows(plan_csv: Path) -> list[PlanRow]:
    if not plan_csv.is_file():
        raise ApplyAbort(f"missing_plan_csv:{plan_csv}")
    rows: list[PlanRow] = []
    with plan_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            if (raw.get("eligibility") or "").strip() != "APPLY_ELIGIBLE":
                continue
            prop_avail_raw = (raw.get("proposed_is_available") or "").strip().lower()
            if prop_avail_raw in {"", "none", "null"}:
                prop_avail: bool | None = None
            else:
                prop_avail = parse_bool_text(prop_avail_raw)
            prop_price = parse_price_text(raw.get("proposed_base_price") or "")
            cur_avail = parse_bool_text(raw.get("current_is_available") or "false")
            cur_price = parse_price_text(raw.get("current_base_price") or "")
            rows.append(
                PlanRow(
                    product_id=int(raw["product_id"]),
                    sku=str(raw["sku"]).strip(),
                    combined_action=str(raw.get("combined_action") or "").strip(),
                    availability_action=str(raw.get("availability_action") or "").strip(),
                    price_action=str(raw.get("price_action") or "").strip(),
                    expected_current_hash=str(raw.get("expected_current_hash") or "").strip(),
                    proposed_is_available=prop_avail,
                    proposed_base_price=prop_price,
                    current_is_available=cur_avail,
                    current_base_price=cur_price,
                )
            )
    if not rows:
        raise ApplyAbort("plan_has_no_apply_eligible_rows")
    ids = [r.product_id for r in rows]
    if len(set(ids)) != len(ids):
        raise ApplyAbort("duplicate_product_id_in_plan")
    return rows


def load_rollback_rows(path: Path) -> list[RollbackRow]:
    if not path.is_file():
        raise ApplyAbort(f"missing_rollback_manifest:{path}")
    out: list[RollbackRow] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            out.append(
                RollbackRow(
                    product_id=int(raw["product_id"]),
                    sku=str(raw["sku"]).strip(),
                    pre_is_available=parse_bool_text(raw.get("pre_is_available") or "false"),
                    pre_base_price=parse_price_text(raw.get("pre_base_price") or ""),
                    proposed_is_available=parse_bool_text(raw.get("proposed_is_available") or "false"),
                    proposed_base_price=parse_price_text(raw.get("proposed_base_price") or ""),
                    expected_current_hash=str(raw.get("expected_current_hash") or "").strip(),
                )
            )
    return out


def assert_plan_matches_evidence(plan_rows: list[PlanRow], evidence_dir: Path) -> dict[str, Any]:
    delta_path = evidence_dir / COMMERCIAL_DELTA_NAME
    if not delta_path.is_file():
        raise ApplyAbort(f"missing_commercial_delta:{delta_path}")
    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    eligible = len(plan_rows)
    expected_eligible = int(delta.get("apply_eligible_rows") or -1)
    if eligible != expected_eligible:
        raise ApplyAbort(
            f"eligible_count_mismatch:plan={eligible}:evidence={expected_eligible}"
        )
    actions = delta.get("mutation_actions") or {}
    combined = Counter()
    price = Counter()
    avail = Counter()
    for row in plan_rows:
        combined[row.combined_action] += 1
        price[row.price_action] += 1
        avail[row.availability_action] += 1
    for key, observed in {
        "combined:CLEAR_PRICE": combined.get("CLEAR_PRICE", 0),
        "combined:HOLD_CLEAR_PRICE": combined.get("HOLD_CLEAR_PRICE", 0),
        "combined:SET_AVAILABLE": combined.get("SET_AVAILABLE", 0),
        "combined:SET_AVAILABLE_AND_PRICE": combined.get("SET_AVAILABLE_AND_PRICE", 0),
        "combined:SET_AVAILABLE_CLEAR_PRICE": combined.get("SET_AVAILABLE_CLEAR_PRICE", 0),
        "combined:SET_UNAVAILABLE_AND_CLEAR_PRICE": combined.get("SET_UNAVAILABLE_AND_CLEAR_PRICE", 0),
        "combined:SET_PRICE": combined.get("SET_PRICE", 0),
        "CLEAR_PRICE": price.get("CLEAR_PRICE", 0),
        "SET_PRICE": price.get("SET_PRICE", 0),
        "SET_AVAILABLE": avail.get("SET_AVAILABLE", 0),
        "SET_UNAVAILABLE": avail.get("SET_UNAVAILABLE", 0),
    }.items():
        if int(actions.get(key, -1)) != observed:
            raise ApplyAbort(f"action_count_mismatch:{key}:plan={observed}:evidence={actions.get(key)}")
    return {
        "eligible_count": eligible,
        "combined_actions": dict(combined),
        "price_actions": dict(price),
        "availability_actions": dict(avail),
    }



def catalog_dict_from_db_row(payload: dict[str, Any]) -> dict[str, str]:
    deleted = payload.get("deleted_at")
    return {
        "product_id": str(payload["id"]),
        "sku": str(payload.get("sku") or ""),
        "brand_id": "" if payload.get("brand_id") is None else str(payload["brand_id"]),
        "is_active": str(payload.get("is_active")).lower()
        if payload.get("is_active") is not None
        else "",
        "is_available": str(payload.get("is_available")).lower()
        if payload.get("is_available") is not None
        else "",
        "base_price": "" if payload.get("base_price") is None else str(payload["base_price"]),
        "deleted_at": "" if not deleted else str(deleted),
        "image_present": str(payload.get("image_present") or "false").lower(),
    }


def stale_hash_guard(plan_rows: list[PlanRow], live_by_id: dict[int, dict[str, str]]) -> StaleGuardResult:
    mismatches: list[dict[str, str]] = []
    match_count = 0
    for plan in plan_rows:
        live = live_by_id.get(plan.product_id)
        if live is None:
            mismatches.append(
                {
                    "product_id": str(plan.product_id),
                    "sku": plan.sku,
                    "reason": "missing_live_row",
                    "expected_hash": plan.expected_current_hash,
                    "actual_hash": "",
                }
            )
            continue
        actual = state_hash(live)
        if actual == plan.expected_current_hash:
            match_count += 1
        else:
            mismatches.append(
                {
                    "product_id": str(plan.product_id),
                    "sku": plan.sku,
                    "reason": "hash_mismatch",
                    "expected_hash": plan.expected_current_hash,
                    "actual_hash": actual,
                }
            )
    ok = match_count == len(plan_rows) and len(mismatches) == 0
    return StaleGuardResult(
        ok=ok,
        expected_count=len(plan_rows),
        match_count=match_count,
        mismatches=mismatches,
    )


SELECT_HASH_ROWS_SQL = f"""
SELECT p.id, p.sku, p.brand_id, p.is_active, p.is_available, p.base_price, p.deleted_at,
       ({_image_exists_sql('p')})::text AS image_present
FROM products p
WHERE p.id = ANY(%s) AND p.deleted_at IS NULL
ORDER BY p.id
"""

SELECT_HASH_ROWS_FOR_UPDATE_SQL = SELECT_HASH_ROWS_SQL.replace(
    "ORDER BY p.id", "ORDER BY p.id\nFOR UPDATE"
)

UPDATE_COMMERCIAL_SQL = """
UPDATE products
SET base_price = %s, is_available = %s
WHERE id = %s AND sku = %s AND deleted_at IS NULL
  AND base_price IS NOT DISTINCT FROM %s
  AND is_available IS NOT DISTINCT FROM %s
"""


class DbConnection(Protocol):
    def cursor(self, *args: Any, **kwargs: Any) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


def _rows_from_cursor(cursor: Any) -> list[dict[str, Any]]:
    rows = cursor.fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
        else:
            out.append(
                {
                    "id": row[0],
                    "sku": row[1],
                    "brand_id": row[2],
                    "is_active": row[3],
                    "is_available": row[4],
                    "base_price": row[5],
                    "deleted_at": row[6],
                    "image_present": row[7],
                }
            )
    return out


def fetch_hash_rows(conn: DbConnection, product_ids: list[int], *, for_update: bool) -> dict[int, dict[str, str]]:
    sql = SELECT_HASH_ROWS_FOR_UPDATE_SQL if for_update else SELECT_HASH_ROWS_SQL
    cur = conn.cursor()
    cur.execute(sql, (product_ids,))
    payload = _rows_from_cursor(cur)
    return {
        int(item["id"]): catalog_dict_from_db_row(item)
        for item in payload
    }


async def fetch_hash_rows_readonly_async(database_url: str, product_ids: list[int]) -> dict[int, dict[str, str]]:
    import asyncpg

    conn = await asyncpg.connect(normalize_database_url(database_url))
    try:
        await conn.execute("BEGIN")
        await conn.execute("SET TRANSACTION READ ONLY")
        imaged = _image_exists_sql("p")
        sql = f"""
        SELECT p.id, p.sku, p.brand_id, p.is_active, p.is_available, p.base_price, p.deleted_at,
               ({imaged})::text AS image_present
        FROM products p
        WHERE p.id = ANY($1::int[]) AND p.deleted_at IS NULL
        ORDER BY p.id
        """
        records = await conn.fetch(sql, product_ids)
        await conn.execute("ROLLBACK")
        return {
            int(rec["id"]): catalog_dict_from_db_row({k: rec[k] for k in rec.keys()})
            for rec in records
        }
    finally:
        await conn.close()


def fetch_hash_rows_readonly(database_url: str, product_ids: list[int]) -> dict[int, dict[str, str]]:
    return asyncio.run(fetch_hash_rows_readonly_async(database_url, product_ids))


def _run_ssh_copy_csv(copy_sql: str, ssh_host: str) -> list[dict[str, str]]:
    if FORBIDDEN_SQL.search(copy_sql):
        raise RuntimeError("mutation-capable SQL refused")
    script = f"""set -euo pipefail
docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging -v ON_ERROR_STOP=1 <<'EOSQL'
BEGIN;
SET TRANSACTION READ ONLY;
{copy_sql}
ROLLBACK;
EOSQL
"""
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, script],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    header_idx = next(
        (i for i, line in enumerate(lines) if "," in line and "product_id" in line),
        None,
    )
    if header_idx is None:
        return []
    return list(csv.DictReader(lines[header_idx:]))


def fetch_hash_rows_ssh(ssh_host: str, product_ids: list[int]) -> dict[int, dict[str, str]]:
    if not product_ids:
        return {}
    id_list = ",".join(str(i) for i in sorted(product_ids))
    imaged = _image_exists_sql("p")
    copy_sql = f"""
COPY (
  SELECT
    p.id::text AS product_id,
    COALESCE(p.sku, '') AS sku,
    COALESCE(p.brand_id::text, '') AS brand_id,
    p.is_active::text AS is_active,
    p.is_available::text AS is_available,
    COALESCE(p.base_price::text, '') AS base_price,
    COALESCE(p.deleted_at::text, '') AS deleted_at,
    ({imaged})::text AS image_present
  FROM products p
  WHERE p.deleted_at IS NULL AND p.id IN ({id_list})
  ORDER BY p.id
) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
"""
    rows = _run_ssh_copy_csv(copy_sql, ssh_host)
    out: dict[int, dict[str, str]] = {}
    for row in rows:
        pid_raw = (row.get("product_id") or "").strip()
        if not pid_raw.isdigit():
            continue
        pid = int(pid_raw)
        out[pid] = row
    return out


def read_only_session_proof_ssh(ssh_host: str) -> dict[str, str]:
    from phase2c_live_readonly_census import _read_only_session_proof

    return _read_only_session_proof(ssh_host)


def proposed_values_for_row(plan: PlanRow) -> tuple[bool, Decimal | None]:
    if plan.proposed_is_available is None:
        raise ApplyAbort(f"missing_proposed_availability:{plan.product_id}")
    return plan.proposed_is_available, plan.proposed_base_price


def assert_apply_authorization_gates(
    *,
    apply: bool,
    rollback: bool,
    confirm_production_write: bool,
    confirm_source_sha256: str,
    confirm_plan_sha256: str,
    confirm_mutation_count: int,
    owner_authorization: str,
    plan_sha256: str,
    eligible_count: int,
    confirm_rollback_manifest_sha256: str = "",
    rollback_manifest_sha256: str = "",
    confirm_batch_id: str = "",
) -> None:
    if not apply and not rollback:
        return
    if apply:
        if owner_authorization != OWNER_AUTH_APPLY:
            raise ApplyAbort("owner_authorization_mismatch_apply")
        if confirm_source_sha256 != OWNER_SOURCE_SHA256:
            raise ApplyAbort("confirm_source_sha256_mismatch")
        if confirm_plan_sha256 != plan_sha256:
            raise ApplyAbort("confirm_plan_sha256_mismatch")
        if confirm_mutation_count != eligible_count:
            raise ApplyAbort(
                f"confirm_mutation_count_mismatch:expected={eligible_count}:got={confirm_mutation_count}"
            )
    if rollback:
        if owner_authorization != OWNER_AUTH_ROLLBACK:
            raise ApplyAbort("owner_authorization_mismatch_rollback")
        if confirm_rollback_manifest_sha256 != rollback_manifest_sha256:
            raise ApplyAbort("confirm_rollback_manifest_sha256_mismatch")
        if not confirm_batch_id:
            raise ApplyAbort("missing_confirm_batch_id")
    if not confirm_production_write:
        raise ApplyAbort("missing_confirm_production_write")
    if os.getenv("KARZAR_ALLOW_PRODUCTION_WRITE", "").strip() != "1":
        raise ApplyAbort("missing_KARZAR_ALLOW_PRODUCTION_WRITE")
    if os.getenv("KARZAR_INGESTION_CATEGORY", "").strip().upper() != "B":
        raise ApplyAbort("missing_KARZAR_INGESTION_CATEGORY=B")


verify_stale_guard = stale_hash_guard


@dataclass
class ApplyJournal:
    batch_id: str
    started_at: str | None
    finished_at: str
    committed: bool
    rows_written: int
    stale_guard: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def writer_contract_summary() -> dict[str, Any]:
    return {
        "mutable_columns": list(MUTABLE_COLUMNS),
        "forbidden_columns": list(FORBIDDEN_MUTATION_COLUMNS),
        "hesabfa_mutation": "NO",
        "external_api_mutation": "NO",
        "mechanism": "direct_asyncpg_sql_no_orm",
    }


def _price_db_value(price: Decimal | None) -> Any:
    return None if price is None else price


def apply_plan_rows(
    conn: DbConnection,
    plan_rows: list[PlanRow],
    *,
    dry_run: bool,
    batch_id: str,
    metadata: dict[str, Any],
    journal_dir: Path,
) -> ApplyResult:
    product_ids = [r.product_id for r in plan_rows]
    live = fetch_hash_rows(conn, product_ids, for_update=not dry_run)
    guard = stale_hash_guard(plan_rows, live)
    if not guard.ok:
        if not dry_run:
            conn.rollback()
        return ApplyResult(
            mode="apply" if not dry_run else "dry_run",
            committed=False,
            rows_written=0,
            batch_id=batch_id,
            stale_guard=guard,
            production_apply_executed=False,
            aborted_reason="BLOCKED_STALE_PLAN",
        )

    journal_rows: list[ApplyJournalRow] = []
    rows_written = 0
    if dry_run:
        for plan in plan_rows:
            live_row = live[plan.product_id]
            prop_avail, prop_price = proposed_values_for_row(plan)
            before_avail = parse_bool_text(live_row.get("is_available") or "false")
            before_price = parse_price_text(live_row.get("base_price") or "")
            journal_rows.append(
                ApplyJournalRow(
                    product_id=plan.product_id,
                    sku=plan.sku,
                    action=plan.combined_action,
                    before_is_available=before_avail,
                    after_is_available=prop_avail,
                    before_base_price="" if before_price is None else str(before_price),
                    after_base_price="" if prop_price is None else str(prop_price),
                    expected_current_hash=plan.expected_current_hash,
                    actual_prewrite_hash=state_hash(live_row),
                    success=True,
                )
            )
        journal = _build_journal(
            batch_id=batch_id,
            metadata=metadata,
            committed=False,
            rows_written=0,
            guard=guard,
            rows=journal_rows,
        )
        return ApplyResult(
            mode="dry_run",
            committed=False,
            rows_written=0,
            batch_id=batch_id,
            stale_guard=guard,
            journal=journal,
            production_apply_executed=False,
        )

    # In-transaction recheck after locks
    live = fetch_hash_rows(conn, product_ids, for_update=True)
    guard = stale_hash_guard(plan_rows, live)
    if not guard.ok:
        conn.rollback()
        return ApplyResult(
            mode="apply",
            committed=False,
            rows_written=0,
            batch_id=batch_id,
            stale_guard=guard,
            production_apply_executed=False,
            aborted_reason="BLOCKED_STALE_PLAN_IN_TX",
        )

    cur = conn.cursor()
    for plan in plan_rows:
        live_row = live[plan.product_id]
        prop_avail, prop_price = proposed_values_for_row(plan)
        before_avail = parse_bool_text(live_row.get("is_available") or "false")
        before_price = parse_price_text(live_row.get("base_price") or "")
        cur.execute(
            UPDATE_COMMERCIAL_SQL,
            (
                _price_db_value(prop_price),
                prop_avail,
                plan.product_id,
                plan.sku,
                _price_db_value(before_price),
                before_avail,
            ),
        )
        ok = getattr(cur, "rowcount", 0) == 1
        if not ok:
            conn.rollback()
            return ApplyResult(
                mode="apply",
                committed=False,
                rows_written=rows_written,
                batch_id=batch_id,
                stale_guard=guard,
                production_apply_executed=False,
                aborted_reason=f"update_rowcount_not_one:{plan.product_id}",
            )
        rows_written += 1
        journal_rows.append(
            ApplyJournalRow(
                product_id=plan.product_id,
                sku=plan.sku,
                action=plan.combined_action,
                before_is_available=before_avail,
                after_is_available=prop_avail,
                before_base_price="" if before_price is None else str(before_price),
                after_base_price="" if prop_price is None else str(prop_price),
                expected_current_hash=plan.expected_current_hash,
                actual_prewrite_hash=state_hash(live_row),
                success=True,
            )
        )
    conn.commit()
    journal = _build_journal(
        batch_id=batch_id,
        metadata=metadata,
        committed=True,
        rows_written=rows_written,
        guard=guard,
        rows=journal_rows,
    )
    path = journal_dir / f"INSIZE_COMMERCIAL_APPLY_JOURNAL_{batch_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(journal, indent=2), encoding="utf-8")
    return ApplyResult(
        mode="apply",
        committed=True,
        rows_written=rows_written,
        batch_id=batch_id,
        stale_guard=guard,
        journal_path=path,
        journal=journal,
        production_apply_executed=True,
    )


def rollback_plan_rows(
    conn: DbConnection,
    rollback_rows: list[RollbackRow],
    *,
    batch_id: str,
    metadata: dict[str, Any],
    journal_dir: Path,
) -> ApplyResult:
    product_ids = [r.product_id for r in rollback_rows]
    live = fetch_hash_rows(conn, product_ids, for_update=True)
    mismatches: list[dict[str, str]] = []
    for row in rollback_rows:
        live_row = live.get(row.product_id)
        if live_row is None:
            mismatches.append({"product_id": str(row.product_id), "reason": "missing"})
            continue
        actual = state_hash(live_row)
        if parse_bool_text(live_row.get("is_available") or "") != row.proposed_is_available:
            mismatches.append({"product_id": str(row.product_id), "reason": "availability_drift"})
        live_price = parse_price_text(live_row.get("base_price") or "")
        if live_price != row.proposed_base_price:
            mismatches.append({"product_id": str(row.product_id), "reason": "price_drift"})
        if actual != row.expected_current_hash and mismatches:
            mismatches[-1]["expected_hash"] = row.expected_current_hash
            mismatches[-1]["actual_hash"] = actual
    guard = StaleGuardResult(
        ok=not mismatches,
        expected_count=len(rollback_rows),
        match_count=len(rollback_rows) - len(mismatches),
        mismatches=mismatches,
    )
    if not guard.ok:
        conn.rollback()
        return ApplyResult(
            mode="rollback",
            committed=False,
            rows_written=0,
            batch_id=batch_id,
            stale_guard=guard,
            aborted_reason="ROLLBACK_DRIFT",
        )
    cur = conn.cursor()
    rows_written = 0
    journal_rows: list[ApplyJournalRow] = []
    for row in rollback_rows:
        live_row = live[row.product_id]
        before_avail = parse_bool_text(live_row.get("is_available") or "false")
        before_price = parse_price_text(live_row.get("base_price") or "")
        cur.execute(
            UPDATE_COMMERCIAL_SQL,
            (
                _price_db_value(row.pre_base_price),
                row.pre_is_available,
                row.product_id,
                row.sku,
                _price_db_value(before_price),
                before_avail,
            ),
        )
        if getattr(cur, "rowcount", 0) != 1:
            conn.rollback()
            return ApplyResult(
                mode="rollback",
                committed=False,
                rows_written=rows_written,
                batch_id=batch_id,
                stale_guard=guard,
                aborted_reason=f"rollback_update_failed:{row.product_id}",
            )
        rows_written += 1
        journal_rows.append(
            ApplyJournalRow(
                product_id=row.product_id,
                sku=row.sku,
                action="ROLLBACK",
                before_is_available=before_avail,
                after_is_available=row.pre_is_available,
                before_base_price="" if before_price is None else str(before_price),
                after_base_price="" if row.pre_base_price is None else str(row.pre_base_price),
                expected_current_hash=row.expected_current_hash,
                actual_prewrite_hash=state_hash(live_row),
                success=True,
            )
        )
    conn.commit()
    journal = _build_journal(
        batch_id=batch_id,
        metadata={**metadata, "rollback": True},
        committed=True,
        rows_written=rows_written,
        guard=guard,
        rows=journal_rows,
    )
    path = journal_dir / f"INSIZE_COMMERCIAL_ROLLBACK_JOURNAL_{batch_id}.json"
    path.write_text(json.dumps(journal, indent=2), encoding="utf-8")
    return ApplyResult(
        mode="rollback",
        committed=True,
        rows_written=rows_written,
        batch_id=batch_id,
        stale_guard=guard,
        journal_path=path,
        journal=journal,
        production_apply_executed=True,
    )


def _build_journal(
    *,
    batch_id: str,
    metadata: dict[str, Any],
    committed: bool,
    rows_written: int,
    guard: StaleGuardResult,
    rows: list[ApplyJournalRow],
) -> dict[str, Any]:
    finished = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "batch_id": batch_id,
        "started_at": metadata.get("started_at"),
        "finished_at": finished,
        "source_sha256": metadata.get("source_sha256"),
        "plan_sha256": metadata.get("plan_sha256"),
        "rollback_manifest_sha256": metadata.get("rollback_manifest_sha256"),
        "git_sha": metadata.get("git_sha"),
        "database_identity": metadata.get("database_identity"),
        "authorization": metadata.get("authorization"),
        "eligible_count": guard.expected_count,
        "locked_count": guard.expected_count,
        "stale_guard_match_count": guard.match_count,
        "committed": committed,
        "COMMITTED": "YES" if committed else "NO",
        "ROWS_WRITTEN": rows_written,
        "rows": [asdict(r) for r in rows],
    }


def production_preflight(
    *,
    evidence_dir: Path,
    plan_rows: list[PlanRow],
    source_xlsx: Path,
    ssh_host: str,
    database_url: str = "",
) -> dict[str, Any]:
    manifest = load_source_manifest(evidence_dir)
    age, freshness_class = classify_owner_freshness(manifest)
    if freshness_class == "STALE":
        raise ApplyAbort("BLOCKED_SOURCE_STALE")
    if source_xlsx.is_file():
        validate_source_sha256(source_xlsx)
    plan_sha = sha256_file(evidence_dir / PLAN_CSV_NAME)
    rollback_sha = sha256_file(evidence_dir / ROLLBACK_CSV_NAME)
    stats = assert_plan_matches_evidence(plan_rows, evidence_dir)
    product_ids = [r.product_id for r in plan_rows]
    db_identity: dict[str, Any]
    if database_url:
        live = fetch_hash_rows_readonly(database_url, product_ids)
        db_identity = {"database_url_host": normalize_database_url(database_url).split("@")[-1]}
        tro = "on"
    else:
        db_identity = read_only_session_proof_ssh(ssh_host)
        live = fetch_hash_rows_ssh(ssh_host, product_ids)
        tro = db_identity.get("transaction_read_only", "")
    guard = stale_hash_guard(plan_rows, live)
    return {
        "PRODUCTION_CONNECTION": "YES",
        "PRODUCTION_READ_ONLY": "YES" if str(tro).lower() == "on" else tro,
        "PRODUCTION_MUTATION": "NO",
        "DATABASE_MUTATION": "NO",
        "PRICE_APPLY": "NO",
        "AVAILABILITY_APPLY": "NO",
        "HESABFA_MUTATION": "NO",
        "DEPLOYMENT": "NO",
        "source_sha256": OWNER_SOURCE_SHA256,
        "plan_sha256": plan_sha,
        "rollback_manifest_sha256": rollback_sha,
        "effective_source_age_days": age,
        "freshness_classification": freshness_class,
        "freshness_basis": manifest.get("freshness_basis"),
        "database_identity": db_identity,
        "transaction_read_only": tro,
        "rows_checked": guard.expected_count,
        "hash_matches": guard.match_count,
        "stale_guard": guard.as_dict(),
        "plan_stats": stats,
        "STATUS": "READY" if guard.ok else "BLOCKED_STALE_PLAN",
    }
