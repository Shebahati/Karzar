"""Guarded INSIZE strict public-sale Safety S1 APPLY (availability-only).

Default mode is DRY RUN (zero writes). Production APPLY requires explicit
Category B authorization tokens and is never executed by this planning task.
"""

from __future__ import annotations

import csv
import hashlib
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from catalog_target.apply_contract import StaleSnapshotGuard
from catalog_target.sales_wave_apply import (
    ALLOW_ENV,
    CATEGORY_ENV,
    FORBIDDEN_MUTATION_COLUMNS as _WAVE1_FORBIDDEN,
    ApplyAbort,
    DbConnection,
    LiveProduct,
    PROD_HOST_MARKER,
    RUNTIME_DB_DEPENDENCY,
    RUNTIME_DB_DRIVER,
    assert_isolation_queries_match_schema,
    assert_production_apply_authorized,
    connect_runtime_db,
    fetch_allowlist_readonly,
    isolation_fingerprint,
    isolation_proof_queries,
    normalize_database_url,
    rows_from_db,
    sha256_file,
)

# Frozen after local reviewed plan generation (also copied under data/catalog-target/).
REVIEWED_ALLOWLIST_COUNT = 316
REVIEWED_AVAILABILITY_CHANGES = 316
REVIEWED_PRICE_CHANGES = 0
REVIEWED_ACTIVE_CHANGES = 0
REVIEWED_PLAN_CSV_RELATIVE = "data/catalog-target/insize_strict_public_sale_s1_plan.csv"
REVIEWED_PLAN_CSV_SHA256 = (
    "d67eb70a67742c985bca45b1a13c7df7e468853ba16cae2d4070e11e6018a054"
)
REVIEWED_SNAPSHOT_TIMESTAMP = "20260908T062718Z"
REVIEWED_SNAPSHOT_SHA256 = (
    "39bd234f4814a3b959f40d3be6de97c4c12b8f026e47db792ddbb22b0098fa71"
)

MUTABLE_COLUMNS = ("is_available",)
FORBIDDEN_MUTATION_COLUMNS = tuple(
    col for col in ("base_price", *_WAVE1_FORBIDDEN) if col != "is_available"
)

REQUIRED_PLAN_FIELDS = (
    "product_id",
    "site_sku",
    "current_is_available",
    "proposed_is_available",
    "current_base_price",
    "current_is_active",
    "blocker",
    "reason_for_disable",
    "mutation_scope",
    "price_mutation",
    "active_mutation",
)

UPDATE_AVAILABILITY_ONLY_SQL = """
UPDATE products
SET is_available = %s
WHERE id = %s AND sku = %s AND deleted_at IS NULL
  AND base_price IS NOT DISTINCT FROM %s
  AND is_available IS NOT DISTINCT FROM %s
  AND is_active IS NOT DISTINCT FROM %s
"""


@dataclass(frozen=True)
class StrictPlanRow:
    product_id: int
    sku: str
    expected_base_price: Decimal | None
    expected_is_available: bool
    proposed_is_available: bool
    expected_is_active: bool
    blocker: str
    reason_for_disable: str
    target_sku: str = ""
    canonical_manufacturer_sku: str = ""
    target_membership_state: str = ""
    identity_confidence: str = ""
    mutation_scope: str = "is_available_only"
    price_mutation: str = "none"
    active_mutation: str = "none"


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
    will_update_price: bool
    will_update_availability: bool
    will_update_active: bool
    unchanged_fields: list[str]
    blocker: str


@dataclass
class ApplyRunResult:
    mode: str
    production_apply_executed: bool
    aborted: bool
    abort_reason: str = ""
    allowlist_count: int = 0
    expected_availability_changes: int = REVIEWED_AVAILABILITY_CHANGES
    expected_price_changes: int = REVIEWED_PRICE_CHANGES
    expected_active_changes: int = REVIEWED_ACTIVE_CHANGES
    stale_guard: dict[str, Any] = field(default_factory=dict)
    dry_run_lines: list[dict[str, Any]] = field(default_factory=list)
    backup_path: str = ""
    backup_sha256: str = ""
    rollback_sql_path: str = ""
    updated_count: int = 0
    transaction_safeguards: dict[str, Any] = field(default_factory=dict)
    implementation_ready: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_plan_csv_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    return root / REVIEWED_PLAN_CSV_RELATIVE


def _parse_bool(raw: str | None, *, field_name: str) -> bool:
    text = str(raw or "").strip().lower()
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    raise ApplyAbort(f"malformed_bool:{field_name}:{raw!r}")


def _parse_price(raw: str | None) -> Decimal | None:
    text = str(raw or "").strip()
    if text == "":
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ApplyAbort(f"malformed_price:{raw!r}") from exc


def _decimal_equal(left: Decimal | None, right: Decimal | None) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return left == right


def load_and_validate_plan(
    path: Path,
    *,
    expected_csv_sha256: str = REVIEWED_PLAN_CSV_SHA256,
    expected_count: int = REVIEWED_ALLOWLIST_COUNT,
    require_checksum: bool = True,
) -> list[StrictPlanRow]:
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

    if len(raw_rows) != expected_count:
        raise ApplyAbort(
            f"plan_count_mismatch:expected={expected_count}:observed={len(raw_rows)}"
        )

    rows: list[StrictPlanRow] = []
    seen_ids: set[int] = set()
    seen_skus: set[str] = set()
    for raw in raw_rows:
        for field_name in REQUIRED_PLAN_FIELDS:
            if field_name == "current_base_price":
                continue
            if str(raw.get(field_name) or "").strip() == "":
                raise ApplyAbort(f"plan_empty_required_field:{field_name}")

        product_id = int(str(raw["product_id"]).strip())
        sku = str(raw["site_sku"]).strip()
        if product_id in seen_ids:
            raise ApplyAbort(f"duplicate_product_id:{product_id}")
        if sku.upper() in seen_skus:
            raise ApplyAbort(f"duplicate_sku:{sku}")
        seen_ids.add(product_id)
        seen_skus.add(sku.upper())

        if str(raw["mutation_scope"]).strip() != "is_available_only":
            raise ApplyAbort(f"mutation_scope_forbidden:{sku}:{raw['mutation_scope']}")
        if str(raw["price_mutation"]).strip() != "none":
            raise ApplyAbort(f"price_mutation_forbidden:{sku}")
        if str(raw["active_mutation"]).strip() != "none":
            raise ApplyAbort(f"active_mutation_forbidden:{sku}")

        expected_available = _parse_bool(
            raw["current_is_available"], field_name="current_is_available"
        )
        proposed_available = _parse_bool(
            raw["proposed_is_available"], field_name="proposed_is_available"
        )
        if expected_available is not True:
            raise ApplyAbort(f"expected_available_must_be_true:{sku}")
        if proposed_available is not False:
            raise ApplyAbort(f"proposed_available_must_be_false:{sku}")

        rows.append(
            StrictPlanRow(
                product_id=product_id,
                sku=sku,
                expected_base_price=_parse_price(raw.get("current_base_price")),
                expected_is_available=True,
                proposed_is_available=False,
                expected_is_active=_parse_bool(
                    raw["current_is_active"], field_name="current_is_active"
                ),
                blocker=str(raw["blocker"]).strip(),
                reason_for_disable=str(raw["reason_for_disable"]).strip(),
                target_sku=str(raw.get("target_sku") or "").strip(),
                canonical_manufacturer_sku=str(
                    raw.get("canonical_manufacturer_sku") or ""
                ).strip(),
                target_membership_state=str(
                    raw.get("target_membership_state") or ""
                ).strip(),
                identity_confidence=str(raw.get("identity_confidence") or "").strip(),
            )
        )

    if len(rows) != expected_count:
        raise ApplyAbort(f"parsed_count_mismatch:{len(rows)}")
    return rows


def compare_live_to_plan(plan: StrictPlanRow, live: LiveProduct) -> list[DriftItem]:
    drifts: list[DriftItem] = []
    if live.deleted_at:
        drifts.append(
            DriftItem(
                plan.product_id,
                plan.sku,
                "deleted_at",
                "",
                str(live.deleted_at),
                "deleted_current",
            )
        )
    if live.id != plan.product_id:
        drifts.append(
            DriftItem(
                plan.product_id,
                plan.sku,
                "id",
                str(plan.product_id),
                str(live.id),
                "id_mismatch",
            )
        )
    if live.sku.strip().upper() != plan.sku.strip().upper():
        drifts.append(
            DriftItem(
                plan.product_id,
                plan.sku,
                "sku",
                plan.sku,
                live.sku,
                "sku_mismatch",
            )
        )
    if not _decimal_equal(live.base_price, plan.expected_base_price):
        drifts.append(
            DriftItem(
                plan.product_id,
                plan.sku,
                "base_price",
                str(plan.expected_base_price),
                "" if live.base_price is None else str(live.base_price),
                "stale_price",
            )
        )
    if live.is_available is not plan.expected_is_available:
        drifts.append(
            DriftItem(
                plan.product_id,
                plan.sku,
                "is_available",
                str(plan.expected_is_available).lower(),
                "" if live.is_available is None else str(live.is_available).lower(),
                "stale_availability",
            )
        )
    if live.is_active is not plan.expected_is_active:
        drifts.append(
            DriftItem(
                plan.product_id,
                plan.sku,
                "is_active",
                str(plan.expected_is_active).lower(),
                "" if live.is_active is None else str(live.is_active).lower(),
                "stale_active",
            )
        )
    return drifts


def stale_guard(
    plan_rows: list[StrictPlanRow], live_rows: list[LiveProduct]
) -> StaleGuardResult:
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


def build_dry_run_lines(plan_rows: list[StrictPlanRow]) -> list[DryRunLine]:
    lines: list[DryRunLine] = []
    for row in plan_rows:
        unchanged = list(FORBIDDEN_MUTATION_COLUMNS)
        lines.append(
            DryRunLine(
                product_id=row.product_id,
                sku=row.sku,
                current_base_price=""
                if row.expected_base_price is None
                else str(row.expected_base_price),
                proposed_base_price=""
                if row.expected_base_price is None
                else str(row.expected_base_price),
                current_is_available="true",
                proposed_is_available="false",
                current_is_active=str(row.expected_is_active).lower(),
                proposed_is_active=str(row.expected_is_active).lower(),
                will_update_price=False,
                will_update_availability=True,
                will_update_active=False,
                unchanged_fields=unchanged,
                blocker=row.blocker,
            )
        )
    return lines


def write_pre_apply_backup(
    live_rows: list[LiveProduct],
    *,
    output_dir: Path,
    stamp: str | None = None,
) -> tuple[Path, str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = output_dir / f"insize_strict_public_sale_s1_pre_apply_{stamp}.csv"
    rollback_path = output_dir / f"insize_strict_public_sale_s1_rollback_{stamp}.sql"
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
        "-- Rollback for INSIZE strict public-sale Safety S1.",
        "-- Restores ONLY writer-mutable column: is_available.",
        "-- base_price / is_active / identity / media are intentionally untouched.",
        "BEGIN;",
    ]
    for row in sorted(live_rows, key=lambda item: item.id):
        available = (
            "NULL" if row.is_available is None else ("TRUE" if row.is_available else "FALSE")
        )
        sku = row.sku.replace("'", "''")
        lines.append(
            "UPDATE products SET "
            f"is_available = {available} "
            f"WHERE id = {row.id} AND sku = '{sku}';"
        )
    lines.append(f"-- expected_row_count={len(live_rows)}")
    lines.append("COMMIT;")
    rollback_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return backup_path, sha256_file(backup_path), rollback_path


def apply_allowlist(
    conn: DbConnection,
    plan_rows: list[StrictPlanRow],
    *,
    dry_run: bool = True,
    backup_dir: Path | None = None,
    expected_count: int = REVIEWED_ALLOWLIST_COUNT,
) -> ApplyRunResult:
    if len(plan_rows) != expected_count:
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
                stale_guard=guard.as_dict(),
                dry_run_lines=[asdict(line) for line in build_dry_run_lines(plan_rows)],
                transaction_safeguards={
                    "single_transaction": True,
                    "abort_before_first_write": True,
                    "partial_commit_allowed": False,
                    "mutable_columns": list(MUTABLE_COLUMNS),
                },
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
        if dry_run:
            conn.rollback()
            return ApplyRunResult(
                mode="dry_run",
                production_apply_executed=False,
                aborted=False,
                allowlist_count=len(plan_rows),
                stale_guard=guard.as_dict(),
                dry_run_lines=[asdict(line) for line in dry_lines],
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
            )

        updated = 0
        for plan in plan_rows:
            cursor.execute(
                UPDATE_AVAILABILITY_ONLY_SQL,
                (
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
            raise ApplyAbort(
                f"updated_count_mismatch:expected={len(plan_rows)}:observed={updated}"
            )

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
            if not _decimal_equal(live_row.base_price, plan.expected_base_price):
                conn.rollback()
                raise ApplyAbort(f"post_write_price_mutated:{plan.sku}")
            if live_row.is_available is not False:
                conn.rollback()
                raise ApplyAbort(f"post_write_availability_mismatch:{plan.sku}")
            if live_row.is_active is not plan.expected_is_active:
                conn.rollback()
                raise ApplyAbort(f"post_write_active_mutated:{plan.sku}")
            if live_row.sku.strip().upper() != plan.sku.strip().upper():
                conn.rollback()
                raise ApplyAbort(f"post_write_sku_mutated:{plan.sku}")

        conn.commit()
        return ApplyRunResult(
            mode="apply_committed",
            production_apply_executed=True,
            aborted=False,
            allowlist_count=len(plan_rows),
            stale_guard=guard.as_dict(),
            dry_run_lines=[asdict(line) for line in dry_lines],
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
        )
    except Exception:
        conn.rollback()
        raise


def writer_contract_summary() -> dict[str, Any]:
    return {
        "wave": "STRICT_PUBLIC_SALE_SAFETY_S1",
        "default_mode": "DRY_RUN",
        "runtime_db_driver": RUNTIME_DB_DRIVER,
        "runtime_db_dependency": RUNTIME_DB_DEPENDENCY,
        "mutable_columns": list(MUTABLE_COLUMNS),
        "forbidden_columns": list(FORBIDDEN_MUTATION_COLUMNS),
        "reviewed_allowlist_count": REVIEWED_ALLOWLIST_COUNT,
        "reviewed_plan_csv": REVIEWED_PLAN_CSV_RELATIVE,
        "reviewed_plan_csv_sha256": REVIEWED_PLAN_CSV_SHA256,
        "reviewed_snapshot_timestamp": REVIEWED_SNAPSHOT_TIMESTAMP,
        "reviewed_snapshot_sha256": REVIEWED_SNAPSHOT_SHA256,
        "stale_snapshot_guard": StaleSnapshotGuard(
            writer_implemented=True,
            notes=(
                "Re-SELECT targeted production rows immediately before mutation.",
                "Compare id, sku, base_price, is_active, is_available to the reviewed plan.",
                "Abort entire APPLY on any drift; no partial commit.",
                "Only is_available may change (true→false).",
            ),
        ).as_dict(),
        "authorization": {
            "apply_flag": "--apply",
            "confirm_production_write": "--confirm-production-write",
            "confirm_plan_sha256": "--confirm-plan-sha256",
            "env": [ALLOW_ENV, f"{CATEGORY_ENV}=B"],
            "production_host_marker": PROD_HOST_MARKER,
        },
        "isolation_proof_queries": "catalog_target.public_sale_safety_apply.isolation_proof_queries",
        "PRODUCTION_MUTATION_DEFAULT": "ZERO",
    }


def post_apply_verification_contract() -> dict[str, Any]:
    return {
        "expected_remaining_available_on_keep_allowlist_only": True,
        "AVAILABLE_TRUE_NOT_ON_PUBLIC_SALE_ALLOWLIST": 0,
        "assert_isolation_queries_match_schema": True,
        "fingerprint_helpers": [
            "isolation_fingerprint",
            "isolation_proof_queries",
        ],
    }


# Re-export helpers tests/CLI may need.
__all__ = [
    "REVIEWED_ALLOWLIST_COUNT",
    "REVIEWED_PLAN_CSV_SHA256",
    "REVIEWED_PLAN_CSV_RELATIVE",
    "ApplyAbort",
    "StrictPlanRow",
    "LiveProduct",
    "apply_allowlist",
    "assert_isolation_queries_match_schema",
    "assert_production_apply_authorized",
    "build_dry_run_lines",
    "connect_runtime_db",
    "default_plan_csv_path",
    "fetch_allowlist_readonly",
    "isolation_fingerprint",
    "isolation_proof_queries",
    "load_and_validate_plan",
    "normalize_database_url",
    "post_apply_verification_contract",
    "sha256_file",
    "stale_guard",
    "write_pre_apply_backup",
    "writer_contract_summary",
]
