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
LOCKED_PLAN_SHA256 = "ee9ebeea6219f953c91fae40716cb0cbddfa04d8f5f9de3f2b0f5a08865eb5b0"
LOCKED_ROLLBACK_MANIFEST_SHA256 = (
    "58f8497ba43c9ea74ad3b862b7c1d9de0eebb8054f460d70929a5e51a9397ca7"
)
EXPECTED_ELIGIBLE_ROWS = 711
OWNER_AUTH_APPLY = "AUTHORIZE_INSIZE_FINAL_COMMERCIAL_APPLY"
OWNER_AUTH_ROLLBACK = "AUTHORIZE_INSIZE_FINAL_COMMERCIAL_ROLLBACK"
DEFAULT_ATTESTED_SOURCE_AGE_DAYS = 7

# Live Karzar VPS catalog DB (CR-011 historic name).
EXPECTED_LIVE_VPS_HOST = "srv5944957438"
EXPECTED_PRODUCTION_DATABASE: dict[str, str] = {
    "current_database": "karzar_staging",
    "current_user": "karzar_staging",
    "postgres_container": "lathe_postgres",
    "expected_live_host": EXPECTED_LIVE_VPS_HOST,
    "pg_system_identifier": "7664189378775347234",
}

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
    price_action: str = ""
    availability_action: str = ""
    expected_post_hash: str = ""
    mutation_sql: str = ""
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


def validate_production_source_xlsx(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ApplyAbort("BLOCKED_SOURCE_XLSX_MISSING")
    observed = sha256_file(path)
    if observed != OWNER_SOURCE_SHA256:
        raise ApplyAbort("BLOCKED_SOURCE_SHA_MISMATCH")
    return {"SOURCE_FILE_PRESENT": "YES", "SOURCE_SHA_MATCH": "YES"}


def _identity_fingerprint(observed: dict[str, Any]) -> str:
    return str(observed.get("pg_system_identifier") or "").strip()


def assert_expected_production_database_identity(
    observed: dict[str, Any],
    *,
    ssh_reference: dict[str, Any] | None = None,
) -> None:
    db = str(observed.get("current_database") or "").strip()
    user = str(observed.get("current_user") or "").strip()
    fp = _identity_fingerprint(observed)
    expected = EXPECTED_PRODUCTION_DATABASE
    if db != expected["current_database"]:
        raise ApplyAbort("BLOCKED_DATABASE_IDENTITY_MISMATCH")
    if user != expected["current_user"]:
        raise ApplyAbort("BLOCKED_DATABASE_IDENTITY_MISMATCH")
    if fp != expected["pg_system_identifier"]:
        raise ApplyAbort("BLOCKED_DATABASE_IDENTITY_MISMATCH")
    host = str(observed.get("expected_live_host") or observed.get("live_host_proof") or "").strip()
    if host and host != expected["expected_live_host"]:
        raise ApplyAbort("BLOCKED_DATABASE_IDENTITY_MISMATCH")
    container = str(observed.get("postgres_container") or "").strip()
    if container and container != expected["postgres_container"]:
        raise ApplyAbort("BLOCKED_DATABASE_IDENTITY_MISMATCH")
    if ssh_reference is not None:
        if _identity_fingerprint(ssh_reference) != fp:
            raise ApplyAbort("BLOCKED_DATABASE_IDENTITY_MISMATCH")
        if str(ssh_reference.get("current_database") or "") != db:
            raise ApplyAbort("BLOCKED_DATABASE_IDENTITY_MISMATCH")


def database_identity_matches(
    observed: dict[str, Any],
    *,
    ssh_reference: dict[str, Any] | None = None,
) -> bool:
    try:
        assert_expected_production_database_identity(observed, ssh_reference=ssh_reference)
    except ApplyAbort:
        return False
    return True


async def _fetch_pg_system_identifier_async(conn: Any) -> str:
    try:
        row = await conn.fetchrow("SELECT system_identifier::text FROM pg_control_system()")
        if row and row[0]:
            return str(row[0]).strip()
    except Exception:
        pass
    return ""


def fetch_production_identity_ssh_reference(ssh_host: str = "karzar-vps") -> dict[str, str]:
    from phase2c_live_readonly_census import _run_ssh_psql

    host_proof = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "hostname"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    db = _run_ssh_psql("SELECT current_database();", ssh_host=ssh_host).splitlines()[-1].strip()
    user = _run_ssh_psql("SELECT current_user;", ssh_host=ssh_host).splitlines()[-1].strip()
    sys_id = _run_ssh_psql(
        "SELECT system_identifier::text FROM pg_control_system();",
        ssh_host=ssh_host,
    ).splitlines()[-1].strip()
    proof = read_only_session_proof_ssh(ssh_host)
    return {
        "current_database": db,
        "current_user": user,
        "pg_system_identifier": sys_id,
        "postgres_container": EXPECTED_PRODUCTION_DATABASE["postgres_container"],
        "expected_live_host": EXPECTED_LIVE_VPS_HOST,
        "live_host_proof": host_proof,
        "transaction_read_only": proof.get("transaction_read_only", ""),
    }


def resolve_production_database_identity(
    *,
    database_url: str = "",
    ssh_host: str = "karzar-vps",
) -> dict[str, Any]:
    ssh_reference = fetch_production_identity_ssh_reference(ssh_host)
    if database_url:
        url_identity = fetch_database_identity(database_url)
        url_identity["database_url_host"] = normalize_database_url(database_url).split("@")[-1]
        assert_expected_production_database_identity(url_identity, ssh_reference=ssh_reference)
        merged = {**ssh_reference, **url_identity}
        merged["pg_system_identifier"] = ssh_reference["pg_system_identifier"]
        return merged
    assert_expected_production_database_identity(ssh_reference)
    return ssh_reference


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
            price_action = str(raw.get("price_action") or "").strip()
            availability_action = str(raw.get("availability_action") or "").strip()
            if price_action == "NO_CHANGE" and availability_action == "NO_CHANGE":
                continue
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

def plan_mutates_price(plan: PlanRow) -> bool:
    return plan.price_action != "NO_CHANGE"


def plan_mutates_availability(plan: PlanRow) -> bool:
    return plan.availability_action != "NO_CHANGE"


def compute_expected_post_hash(live_row: dict[str, str], plan: PlanRow) -> str:
    prop_avail, prop_price = proposed_values_for_row(plan)
    projected = dict(live_row)
    if plan_mutates_price(plan):
        projected["base_price"] = "" if prop_price is None else str(prop_price)
    if plan_mutates_availability(plan):
        projected["is_available"] = "true" if prop_avail else "false"
    return state_hash(projected)


def build_mutation_sql(
    plan: PlanRow,
    *,
    prop_avail: bool,
    prop_price: Decimal | None,
    before_avail: bool,
    before_price: Decimal | None,
) -> tuple[str, tuple[Any, ...]]:
    sets: list[str] = []
    params: list[Any] = []
    if plan_mutates_price(plan):
        sets.append("base_price = %s")
        params.append(_price_db_value(prop_price))
    if plan_mutates_availability(plan):
        sets.append("is_available = %s")
        params.append(prop_avail)
    if not sets:
        raise ApplyAbort(f"no_mutation_actions:{plan.product_id}")
    where = ["id = %s", "sku = %s", "deleted_at IS NULL"]
    params.extend([plan.product_id, plan.sku])
    where.append("base_price IS NOT DISTINCT FROM %s")
    params.append(_price_db_value(before_price))
    where.append("is_available IS NOT DISTINCT FROM %s")
    params.append(before_avail)
    sql = f"UPDATE products SET {', '.join(sets)} WHERE {' AND '.join(where)}"
    return sql, tuple(params)


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
    return {int(item["id"]): catalog_dict_from_db_row(item) for item in payload}


async def fetch_database_identity_async(database_url: str) -> dict[str, str]:
    import asyncpg

    conn = await asyncpg.connect(normalize_database_url(database_url))
    try:
        row = await conn.fetchrow(
            """
            SELECT current_database()::text AS current_database,
                   current_user::text AS current_user,
                   COALESCE(inet_server_addr()::text, '') AS server_addr
            """
        )
        sys_id = await _fetch_pg_system_identifier_async(conn)
        return {
            "current_database": row["current_database"],
            "current_user": row["current_user"],
            "server_addr": row["server_addr"] or "",
            "pg_system_identifier": sys_id,
            "postgres_container": EXPECTED_PRODUCTION_DATABASE["postgres_container"],
            "expected_live_host": EXPECTED_LIVE_VPS_HOST,
        }
    finally:
        await conn.close()


def fetch_database_identity(database_url: str) -> dict[str, str]:
    return asyncio.run(fetch_database_identity_async(database_url))


def fetch_database_identity_ssh(ssh_host: str) -> dict[str, str]:
    return fetch_production_identity_ssh_reference(ssh_host)


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
        out[int(pid_raw)] = row
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


def _journal_path(journal_dir: Path, batch_id: str, *, rollback: bool = False) -> Path:
    prefix = "INSIZE_COMMERCIAL_ROLLBACK_JOURNAL" if rollback else "INSIZE_COMMERCIAL_APPLY_JOURNAL"
    return journal_dir / f"{prefix}_{batch_id}.json"


def write_journal_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, indent=2)
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def load_apply_journal(journal_dir: Path, batch_id: str) -> dict[str, Any]:
    path = _journal_path(journal_dir, batch_id)
    if not path.is_file():
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_apply_journal_for_rollback(
    journal: dict[str, Any],
    *,
    batch_id: str,
    source_sha256: str,
    plan_sha256: str,
    rollback_manifest_sha256: str,
    database_identity: dict[str, Any],
    expected_rows: int = EXPECTED_ELIGIBLE_ROWS,
) -> None:
    if journal.get("mode") != "APPLY":
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if journal.get("batch_id") != batch_id:
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if journal.get("COMMITTED") != "YES" or not journal.get("committed"):
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if int(journal.get("ROWS_WRITTEN") or 0) != expected_rows:
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if journal.get("source_sha256") != source_sha256:
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if journal.get("plan_sha256") != plan_sha256:
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if journal.get("rollback_manifest_sha256") != rollback_manifest_sha256:
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    stored = journal.get("database_identity") or {}
    if stored.get("current_database") != database_identity.get("current_database"):
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if stored.get("pg_system_identifier") != database_identity.get("pg_system_identifier"):
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if journal.get("POST_COMMIT_VERIFICATION") != "PASS":
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")
    if len(journal.get("rows") or []) != expected_rows:
        raise ApplyAbort("BLOCK_ROLLBACK_NO_VALID_APPLY_JOURNAL")


def verify_post_apply_hashes(
    live_by_id: dict[int, dict[str, str]],
    journal_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    mismatches: list[dict[str, str]] = []
    match_count = 0
    for row in journal_rows:
        pid = int(row["product_id"])
        live = live_by_id.get(pid)
        expected_post = str(row.get("expected_post_hash") or "")
        if live is None:
            mismatches.append({"product_id": str(pid), "reason": "missing_live_row"})
            continue
        actual = state_hash(live)
        if actual == expected_post:
            match_count += 1
        else:
            mismatches.append(
                {
                    "product_id": str(pid),
                    "reason": "post_hash_mismatch",
                    "expected_post_hash": expected_post,
                    "actual_hash": actual,
                }
            )
    ok = match_count == len(journal_rows) and not mismatches
    return {
        "ok": ok,
        "POST_COMMIT_VERIFICATION": "PASS" if ok else "FAIL",
        "POST_COMMIT_MATCH_COUNT": match_count,
        "POST_COMMIT_MISMATCH_COUNT": len(journal_rows) - match_count,
        "mismatches": mismatches,
    }


def verify_post_rollback_hashes(
    live_by_id: dict[int, dict[str, str]],
    journal_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    mismatches: list[dict[str, str]] = []
    match_count = 0
    for row in journal_rows:
        pid = int(row["product_id"])
        live = live_by_id.get(pid)
        expected_pre = str(row.get("expected_current_hash") or "")
        if live is None:
            mismatches.append({"product_id": str(pid), "reason": "missing_live_row"})
            continue
        actual = state_hash(live)
        if actual == expected_pre:
            match_count += 1
        else:
            mismatches.append(
                {
                    "product_id": str(pid),
                    "reason": "pre_hash_mismatch",
                    "expected_current_hash": expected_pre,
                    "actual_hash": actual,
                }
            )
    ok = match_count == len(journal_rows) and not mismatches
    return {
        "ok": ok,
        "POST_ROLLBACK_VERIFICATION": "PASS" if ok else "FAIL",
        "MATCH_COUNT": match_count,
        "mismatches": mismatches,
    }


def _journal_row_from_plan(
    plan: PlanRow,
    live_row: dict[str, str],
    *,
    prop_avail: bool,
    prop_price: Decimal | None,
    before_avail: bool,
    before_price: Decimal | None,
    mutation_sql: str,
) -> ApplyJournalRow:
    return ApplyJournalRow(
        product_id=plan.product_id,
        sku=plan.sku,
        action=plan.combined_action,
        price_action=plan.price_action,
        availability_action=plan.availability_action,
        before_is_available=before_avail,
        after_is_available=prop_avail,
        before_base_price="" if before_price is None else str(before_price),
        after_base_price="" if prop_price is None else str(prop_price),
        expected_current_hash=plan.expected_current_hash,
        actual_prewrite_hash=state_hash(live_row),
        expected_post_hash=compute_expected_post_hash(live_row, plan),
        mutation_sql=mutation_sql,
        success=True,
    )


def apply_plan_rows(
    conn: DbConnection,
    plan_rows: list[PlanRow],
    *,
    dry_run: bool,
    batch_id: str,
    metadata: dict[str, Any],
    journal_dir: Path,
    database_url: str = "",
    journal_writer: Any | None = None,
) -> ApplyResult:
    writer = journal_writer or write_journal_atomic
    journal_path = _journal_path(journal_dir, batch_id)
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
    planned_mutations: list[tuple[PlanRow, str, tuple[Any, ...], dict[str, str]]] = []

    for plan in plan_rows:
        live_row = live[plan.product_id]
        prop_avail, prop_price = proposed_values_for_row(plan)
        before_avail = parse_bool_text(live_row.get("is_available") or "false")
        before_price = parse_price_text(live_row.get("base_price") or "")
        sql, params = build_mutation_sql(
            plan,
            prop_avail=prop_avail,
            prop_price=prop_price,
            before_avail=before_avail,
            before_price=before_price,
        )
        journal_rows.append(
            _journal_row_from_plan(
                plan,
                live_row,
                prop_avail=prop_avail,
                prop_price=prop_price,
                before_avail=before_avail,
                before_price=before_price,
                mutation_sql=sql,
            )
        )
        if not dry_run:
            planned_mutations.append((plan, sql, params, live_row))

    if dry_run:
        journal = _build_journal(
            batch_id=batch_id,
            metadata=metadata,
            committed=False,
            rows_written=0,
            guard=guard,
            rows=journal_rows,
            mode="APPLY",
            journal_phase="DRY_RUN",
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

    pre_journal = _build_journal(
        batch_id=batch_id,
        metadata=metadata,
        committed=False,
        rows_written=0,
        guard=guard,
        rows=journal_rows,
        mode="APPLY",
        journal_phase="PRE_COMMIT",
    )
    try:
        writer(journal_path, pre_journal)
    except OSError:
        conn.rollback()
        return ApplyResult(
            mode="apply",
            committed=False,
            rows_written=0,
            batch_id=batch_id,
            stale_guard=guard,
            production_apply_executed=False,
            aborted_reason="JOURNAL_WRITE_FAILED",
        )

    cur = conn.cursor()
    rows_written = 0
    for plan, sql, params, _live_row in planned_mutations:
        cur.execute(sql, params)
        if getattr(cur, "rowcount", 0) != 1:
            conn.rollback()
            aborted = _build_journal(
                batch_id=batch_id,
                metadata=metadata,
                committed=False,
                rows_written=rows_written,
                guard=guard,
                rows=journal_rows,
                mode="APPLY",
                journal_phase="ABORTED",
            )
            writer(journal_path, aborted)
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

    commit_ack = False
    try:
        conn.commit()
        commit_ack = True
    except Exception:
        commit_ack = False

    verify_report: dict[str, Any] = {"POST_COMMIT_VERIFICATION": "SKIPPED"}
    if not commit_ack and database_url:
        live_post = fetch_hash_rows_readonly(database_url, product_ids)
        verify_report = verify_post_apply_hashes(live_post, [asdict(r) for r in journal_rows])
        ambiguous = _build_journal(
            batch_id=batch_id,
            metadata=metadata,
            committed=False,
            rows_written=rows_written,
            guard=guard,
            rows=journal_rows,
            mode="APPLY",
            journal_phase="COMMIT_OUTCOME_UNKNOWN",
            post_commit=verify_report,
        )
        ambiguous["COMMIT_OUTCOME_UNKNOWN"] = "YES"
        ambiguous["MANUAL_REVIEW_REQUIRED"] = "YES"
        if verify_report.get("ok"):
            ambiguous["COMMITTED"] = "YES"
            ambiguous["committed"] = True
            ambiguous["POST_COMMIT_VERIFICATION"] = "PASS"
            ambiguous["observed_post_apply_state_verified"] = "YES"
        writer(journal_path, ambiguous)
        return ApplyResult(
            mode="apply",
            committed=bool(verify_report.get("ok")),
            rows_written=rows_written,
            batch_id=batch_id,
            stale_guard=guard,
            journal_path=journal_path,
            journal=ambiguous,
            production_apply_executed=bool(verify_report.get("ok")),
            aborted_reason="COMMIT_OUTCOME_UNKNOWN",
        )
    if not commit_ack:
        aborted = _build_journal(
            batch_id=batch_id,
            metadata=metadata,
            committed=False,
            rows_written=rows_written,
            guard=guard,
            rows=journal_rows,
            mode="APPLY",
            journal_phase="COMMIT_OUTCOME_UNKNOWN",
        )
        aborted["COMMIT_OUTCOME_UNKNOWN"] = "YES"
        aborted["MANUAL_REVIEW_REQUIRED"] = "YES"
        writer(journal_path, aborted)
        return ApplyResult(
            mode="apply",
            committed=False,
            rows_written=rows_written,
            batch_id=batch_id,
            stale_guard=guard,
            journal_path=journal_path,
            journal=aborted,
            production_apply_executed=False,
            aborted_reason="COMMIT_OUTCOME_UNKNOWN",
        )

    if database_url:
        live_post = fetch_hash_rows_readonly(database_url, product_ids)
        verify_report = verify_post_apply_hashes(live_post, [asdict(r) for r in journal_rows])

    final_journal = _build_journal(
        batch_id=batch_id,
        metadata=metadata,
        committed=True,
        rows_written=rows_written,
        guard=guard,
        rows=journal_rows,
        mode="APPLY",
        journal_phase="FINAL",
        post_commit=verify_report,
    )
    if verify_report.get("POST_COMMIT_VERIFICATION") == "FAIL":
        final_journal["MANUAL_REVIEW_REQUIRED"] = "YES"
    writer(journal_path, final_journal)

    return ApplyResult(
        mode="apply",
        committed=True,
        rows_written=rows_written,
        batch_id=batch_id,
        stale_guard=guard,
        journal_path=journal_path,
        journal=final_journal,
        production_apply_executed=True,
        aborted_reason="" if verify_report.get("ok", True) else "POST_COMMIT_VERIFICATION_FAIL",
    )


def rollback_post_apply_drift_guard(
    apply_journal_rows: list[dict[str, Any]],
    live_by_id: dict[int, dict[str, str]],
) -> StaleGuardResult:
    mismatches: list[dict[str, str]] = []
    match_count = 0
    for row in apply_journal_rows:
        pid = int(row["product_id"])
        live_row = live_by_id.get(pid)
        if live_row is None:
            mismatches.append({"product_id": str(pid), "reason": "missing"})
            continue
        actual = state_hash(live_row)
        expected_post = str(row.get("expected_post_hash") or "")
        if actual == expected_post:
            match_count += 1
        else:
            mismatches.append(
                {
                    "product_id": str(pid),
                    "reason": "post_apply_hash_drift",
                    "expected_post_hash": expected_post,
                    "actual_hash": actual,
                }
            )
    return StaleGuardResult(
        ok=match_count == len(apply_journal_rows) and not mismatches,
        expected_count=len(apply_journal_rows),
        match_count=match_count,
        mismatches=mismatches,
    )


def rollback_plan_rows(
    conn: DbConnection,
    *,
    apply_journal: dict[str, Any],
    batch_id: str,
    metadata: dict[str, Any],
    journal_dir: Path,
    database_url: str = "",
    journal_writer: Any | None = None,
) -> ApplyResult:
    writer = journal_writer or write_journal_atomic
    journal_path = _journal_path(journal_dir, batch_id, rollback=True)
    apply_rows = list(apply_journal.get("rows") or [])
    product_ids = [int(r["product_id"]) for r in apply_rows]
    live = fetch_hash_rows(conn, product_ids, for_update=True)
    guard = rollback_post_apply_drift_guard(apply_rows, live)
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

    rollback_sql = """
UPDATE products
SET base_price = %s, is_available = %s
WHERE id = %s AND sku = %s AND deleted_at IS NULL
  AND base_price IS NOT DISTINCT FROM %s
  AND is_available IS NOT DISTINCT FROM %s
"""
    rollback_journal_rows: list[ApplyJournalRow] = []
    mutations: list[tuple[dict[str, Any], tuple[Any, ...]]] = []
    for row in apply_rows:
        pid = int(row["product_id"])
        live_row = live[pid]
        before_avail = parse_bool_text(live_row.get("is_available") or "false")
        before_price = parse_price_text(live_row.get("base_price") or "")
        raw_target_avail = row.get("before_is_available")
        if isinstance(raw_target_avail, bool):
            target_avail = raw_target_avail
        else:
            target_avail = parse_bool_text(str(raw_target_avail or "false").lower())
        target_price = parse_price_text(str(row.get("before_base_price") or ""))
        params = (
            _price_db_value(target_price),
            target_avail,
            pid,
            str(row["sku"]),
            _price_db_value(before_price),
            before_avail,
        )
        mutations.append((row, params))
        rollback_journal_rows.append(
            ApplyJournalRow(
                product_id=pid,
                sku=str(row["sku"]),
                action="ROLLBACK",
                before_is_available=before_avail,
                after_is_available=target_avail,
                before_base_price="" if before_price is None else str(before_price),
                after_base_price="" if target_price is None else str(target_price),
                expected_current_hash=str(row.get("expected_current_hash") or ""),
                actual_prewrite_hash=state_hash(live_row),
                expected_post_hash=str(row.get("expected_current_hash") or ""),
                mutation_sql=rollback_sql.strip(),
                success=True,
            )
        )

    pre_journal = _build_journal(
        batch_id=batch_id,
        metadata={**metadata, "rollback": True},
        committed=False,
        rows_written=0,
        guard=guard,
        rows=rollback_journal_rows,
        mode="ROLLBACK",
        journal_phase="PRE_COMMIT",
    )
    try:
        writer(journal_path, pre_journal)
    except OSError:
        conn.rollback()
        return ApplyResult(
            mode="rollback",
            committed=False,
            rows_written=0,
            batch_id=batch_id,
            stale_guard=guard,
            aborted_reason="JOURNAL_WRITE_FAILED",
        )

    cur = conn.cursor()
    rows_written = 0
    for _row, params in mutations:
        cur.execute(rollback_sql, params)
        if getattr(cur, "rowcount", 0) != 1:
            conn.rollback()
            return ApplyResult(
                mode="rollback",
                committed=False,
                rows_written=rows_written,
                batch_id=batch_id,
                stale_guard=guard,
                aborted_reason="ROLLBACK_DRIFT",
            )
        rows_written += 1

    commit_ack = False
    try:
        conn.commit()
        commit_ack = True
    except Exception:
        commit_ack = False

    verify_report: dict[str, Any] = {"POST_ROLLBACK_VERIFICATION": "SKIPPED"}
    if database_url:
        live_post = fetch_hash_rows_readonly(database_url, product_ids)
        verify_report = verify_post_rollback_hashes(live_post, [asdict(r) for r in rollback_journal_rows])

    if not commit_ack:
        ambiguous = _build_journal(
            batch_id=batch_id,
            metadata={**metadata, "rollback": True},
            committed=bool(verify_report.get("ok")),
            rows_written=rows_written,
            guard=guard,
            rows=rollback_journal_rows,
            mode="ROLLBACK",
            journal_phase="COMMIT_OUTCOME_UNKNOWN",
            post_commit=verify_report,
        )
        ambiguous["COMMIT_OUTCOME_UNKNOWN"] = "YES"
        ambiguous["MANUAL_REVIEW_REQUIRED"] = "YES"
        if verify_report.get("ok"):
            ambiguous["COMMITTED"] = "YES"
            ambiguous["committed"] = True
        writer(journal_path, ambiguous)
        return ApplyResult(
            mode="rollback",
            committed=bool(verify_report.get("ok")),
            rows_written=rows_written,
            batch_id=batch_id,
            stale_guard=guard,
            journal_path=journal_path,
            journal=ambiguous,
            production_apply_executed=bool(verify_report.get("ok")),
            aborted_reason="COMMIT_OUTCOME_UNKNOWN",
        )

    final_journal = _build_journal(
        batch_id=batch_id,
        metadata={**metadata, "rollback": True},
        committed=True,
        rows_written=rows_written,
        guard=guard,
        rows=rollback_journal_rows,
        mode="ROLLBACK",
        journal_phase="FINAL",
        post_commit=verify_report,
    )
    writer(journal_path, final_journal)
    return ApplyResult(
        mode="rollback",
        committed=True,
        rows_written=rows_written,
        batch_id=batch_id,
        stale_guard=guard,
        journal_path=journal_path,
        journal=final_journal,
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
    mode: str = "APPLY",
    journal_phase: str = "FINAL",
    post_commit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    finished = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload: dict[str, Any] = {
        "batch_id": batch_id,
        "mode": mode,
        "journal_phase": journal_phase,
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
    if post_commit:
        payload.update(post_commit)
    return payload


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
    source_flags = validate_production_source_xlsx(source_xlsx)
    plan_sha = sha256_file(evidence_dir / PLAN_CSV_NAME)
    rollback_sha = sha256_file(evidence_dir / ROLLBACK_CSV_NAME)
    plan_sha_match = plan_sha == LOCKED_PLAN_SHA256
    rollback_sha_match = rollback_sha == LOCKED_ROLLBACK_MANIFEST_SHA256
    stats = assert_plan_matches_evidence(plan_rows, evidence_dir)
    product_ids = [r.product_id for r in plan_rows]
    ssh_reference = fetch_production_identity_ssh_reference(ssh_host)
    if database_url:
        db_identity = fetch_database_identity(database_url)
        db_identity["database_url_host"] = normalize_database_url(database_url).split("@")[-1]
        live = fetch_hash_rows_readonly(database_url, product_ids)
        tro = "on"
        identity_match = database_identity_matches(db_identity, ssh_reference=ssh_reference)
        db_identity = {**ssh_reference, **db_identity, "pg_system_identifier": ssh_reference["pg_system_identifier"]}
    else:
        db_identity = ssh_reference
        live = fetch_hash_rows_ssh(ssh_host, product_ids)
        tro = db_identity.get("transaction_read_only", "")
        identity_match = database_identity_matches(db_identity)
    guard = stale_hash_guard(plan_rows, live)
    status = "READY"
    if not guard.ok:
        status = "BLOCKED_STALE_PLAN"
    elif not plan_sha_match or not rollback_sha_match:
        status = "BLOCKED_PLAN_ARTIFACT_MISMATCH"
    elif not identity_match:
        status = "BLOCKED_DATABASE_IDENTITY"
    return {
        "PRODUCTION_CONNECTION": "YES",
        "PRODUCTION_READ_ONLY": "YES" if str(tro).lower() == "on" else tro,
        "PRODUCTION_MUTATION": "NO",
        "DATABASE_MUTATION": "NO",
        "PRICE_APPLY": "NO",
        "AVAILABILITY_APPLY": "NO",
        "HESABFA_MUTATION": "NO",
        "DEPLOYMENT": "NO",
        **source_flags,
        "source_sha256": OWNER_SOURCE_SHA256,
        "plan_sha256": plan_sha,
        "rollback_manifest_sha256": rollback_sha,
        "PLAN_SHA_MATCH": "YES" if plan_sha_match else "NO",
        "ROLLBACK_MANIFEST_SHA_MATCH": "YES" if rollback_sha_match else "NO",
        "DATABASE_IDENTITY_MATCH": "YES" if identity_match else "NO",
        "effective_source_age_days": age,
        "freshness_classification": freshness_class,
        "freshness_basis": manifest.get("freshness_basis"),
        "database_identity": db_identity,
        "transaction_read_only": tro,
        "ROWS_CHECKED": guard.expected_count,
        "PRE_APPLY_HASH_MATCH_COUNT": guard.match_count,
        "rows_checked": guard.expected_count,
        "hash_matches": guard.match_count,
        "stale_guard": guard.as_dict(),
        "plan_stats": stats,
        "STATUS": status,
    }
