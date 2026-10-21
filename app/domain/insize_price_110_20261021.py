"""INSIZE +10% owner-authorized base_price APPLY (2026-10-21). Pure helpers — no I/O."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.domain.phase2c_apply import sql_literal

EXPECTED_BRAND_ID = 3
EXPECTED_BRAND_NAME = "INSIZE | اینسایز"
CHANGE_REASON = "INSIZE +10% owner-authorized price update 2026-10-21"
ROLLBACK_CHANGE_REASON = (
    "INSIZE +10% rollback restore exact pre-apply base_price 2026-10-21"
)
MULTIPLIER = Decimal("1.10")
ADVISORY_LOCK_KEY = "karzar:insize:price110:20261021"
COMMERCIAL_EVENT_ID = "INSIZE-PRICE-110-20261021"
PREVIOUS_EVENT_CHANGE_REASON = (
    "INSIZE +10% owner-authorized price update 2026-10-19"
)
EXPECTED_PREVIOUS_EVENT_LOG_ROWS = 206
EXPECTED_PREVIOUS_EVENT_BASE_SUM = Decimal("3413658600.00")
LEGACY_FROZEN_MANIFEST_V1_SHA256 = (
    "cc1003dd41d5a87ddfb4c98724992ffad897585a46203ad780992ec46cae2d15"
)
LEGACY_FROZEN_MANIFEST_V1_CSV_REL = (
    "audit/insize-price-110-20261021/immutable-v1/"
    "INSIZE_PRICE_110_20261021_MANIFEST_20261021T132506Z.csv"
)
# Owner-frozen v2 (merchandising exceptions) — updated after manifest generation.
FROZEN_MANIFEST_SHA256 = (
    "bb2d073b8adc037ccfc50122da845d9e4869658a0467c364264fbe7f0af80540"
)
FROZEN_MANIFEST_CSV_REL = (
    "audit/insize-price-110-20261021/INSIZE_PRICE_110_20261021_MANIFEST_20261021T133454Z.csv"
)
AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS = frozenset({1944, 3639})
ORIGINAL_PRICE_CLEAR_CHANGE_REASON = (
    "INSIZE +10% owner-authorized original_price clear (1944,3639) 2026-10-21"
)
PRICE_CURRENCY_LABEL = "TOMAN"  # products.base_price is stored in Toman; never convert.
GUARDED_ROLLBACK_FILENAME_PREFIX = "INSIZE_PRICE_110_20261021_ROLLBACK_"
EXPECTED_PRICED_COHORT_ROWS = 206
EXPECTED_ORIGINAL_EXCEPTION_COUNT = len(AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS)
EXPECTED_NON_EXCEPTION_ORIGINAL_COUNT = (
    EXPECTED_PRICED_COHORT_ROWS - EXPECTED_ORIGINAL_EXCEPTION_COUNT
)
EXPECTED_TOTAL_EVENT_LOG_ROWS = (
    EXPECTED_PRICED_COHORT_ROWS + EXPECTED_ORIGINAL_EXCEPTION_COUNT
)
AUTHORIZED_EXCEPTION_IDS_SQL = ", ".join(
    str(pid) for pid in sorted(AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS)
)
EXPECTED_PREFLIGHT_BASE_SUM = Decimal("3413658600.00")
EXPECTED_POST_APPLY_BASE_SUM = Decimal("3755024460.00")
EXPECTED_VPS_HOSTNAME = "srv5944957438"
EXPECTED_POSTGRES_CONTAINER = "lathe_postgres"
EXPECTED_DATABASE = "karzar_staging"
EXPECTED_DATABASE_USER = "karzar_staging"
EXPECTED_DOCKER_VOLUME = "karzar_postgres_data"
EXPECTED_PG_SYSTEM_IDENTIFIER = "7664189378775347234"
# Live CR-011 head at 2026-10-19 owner hardening (independent psql proof).
EXPECTED_ALEMBIC_REVISION = "a3f410b5c6d7"
MIN_PUBLIC_API_PRICE_VERIFICATIONS = 5
OPERATOR_LOGIC_FILES = (
    "app/domain/insize_price_110_20261021.py",
    "scripts/ops/insize_price_110_20261021_apply_once.py",
)



def discount_percent(base: Decimal, original: Decimal | None) -> Decimal | None:
    if original is None or original <= 0 or base is None:
        return None
    if base >= original:
        return Decimal("0")
    return ((original - base) / original * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def is_authorized_original_null_exception(product_id: int) -> bool:
    return int(product_id) in AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS


def find_discount_semantics_blockers(
    manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fail-closed unless owner-authorized original_price NULL exception is declared."""
    blockers: list[dict[str, Any]] = []
    for row in manifest:
        pid = int(row["product_id"])
        proposed_original = row.get("proposed_original_price")
        if is_authorized_original_null_exception(pid):
            if proposed_original not in (None, "", "null"):
                blockers.append(
                    {
                        "product_id": pid,
                        "sku": row.get("sku"),
                        "issue": "authorized_exception_requires_null_proposed_original",
                    }
                )
            continue
        original = parse_money(
            row.get("old_original_price") or row.get("original_price")
        )
        new_base = parse_money(row.get("proposed_base_price"))
        if original is None or original <= 0 or new_base is None:
            continue
        if new_base > original:
            blockers.append(
                {
                    "product_id": pid,
                    "sku": row.get("sku"),
                    "original_price": str(original),
                    "proposed_base_price": str(new_base),
                    "issue": "proposed_base_above_original_price",
                }
            )
    return blockers


def merchandising_exception_comparison(row: dict[str, Any]) -> dict[str, Any]:
    """Owner-facing two-product style comparison (Toman, from base_price fields)."""
    old_base = parse_money(row["old_base_price"])
    new_base = parse_money(row["proposed_base_price"])
    old_orig = parse_money(row.get("old_original_price") or row.get("original_price"))
    new_orig = parse_money(row.get("proposed_original_price"))
    cur_pct = discount_percent(old_base, old_orig)
    prop_pct = discount_percent(new_base, new_orig)
    cur_display = discount_display_state(base_price=old_base or Decimal(0), original_price=old_orig)
    prop_display = discount_display_state(base_price=new_base or Decimal(0), original_price=new_orig)
    return {
        "product_id": int(row["product_id"]),
        "sku": row.get("sku"),
        "currency": PRICE_CURRENCY_LABEL,
        "current_base_price_toman": str(old_base) if old_base is not None else None,
        "current_original_price_toman": str(old_orig) if old_orig is not None else None,
        "proposed_base_price_toman": str(new_base) if new_base is not None else None,
        "proposed_original_price_toman": None if new_orig is None else str(new_orig),
        "current_discount_percent": str(cur_pct) if cur_pct is not None else None,
        "proposed_discount_percent": str(prop_pct) if prop_pct is not None else None,
        "current_storefront_display": cur_display,
        "proposed_storefront_display": prop_display,
    }


def assert_change_reason() -> None:
    if len(CHANGE_REASON) > 255:
        raise ValueError("change reason exceeds VARCHAR(255)")


def parse_money(value: str | Decimal | None) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None

def money_equal_nullable(
    left: Decimal | None,
    right: Decimal | None,
) -> bool:
    return left == right


_CSV_BOOL_TRUE = frozenset({"true", "1", "yes", "t"})
_CSV_BOOL_FALSE = frozenset({"false", "0", "no", "f"})


def parse_csv_bool(
    value: Any,
    *,
    field: str,
    product_id: int | None = None,
) -> bool:
    """Strict CSV boolean — never use Python truthiness on strings."""
    if isinstance(value, bool):
        return value
    if value is None:
        raise ValueError(f"{field}: missing boolean (product_id={product_id})")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field}: empty boolean (product_id={product_id})")
    lowered = text.lower()
    if lowered in _CSV_BOOL_TRUE:
        return True
    if lowered in _CSV_BOOL_FALSE:
        return False
    raise ValueError(
        f"{field}: malformed boolean {value!r} (product_id={product_id})"
    )


def parse_manifest_proposed_original(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    parsed = parse_money(text)
    if parsed is None:
        raise ValueError(f"unparseable proposed_original_price: {value!r}")
    return parsed


def resolve_exception_flag(row: dict[str, Any]) -> bool:
    """Validated exception flag; must agree with authorized ID whitelist."""
    pid = int(row["product_id"])
    raw = row.get("authorized_original_price_exception")
    if isinstance(raw, bool):
        flag = raw
    else:
        flag = parse_csv_bool(
            raw,
            field="authorized_original_price_exception",
            product_id=pid,
        )
    must_exception = pid in AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS
    if flag != must_exception:
        raise ValueError(
            f"authorized_original_price_exception/id mismatch product_id={pid} "
            f"flag={flag} expected={must_exception}"
        )
    return flag


def validate_owner_frozen_commercial_contract(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fail-closed merchandising + original_price whitelist (CSV-safe)."""
    errors: list[str] = []
    exception_ids: set[int] = set()
    non_exception_ids: set[int] = set()
    for row in rows:
        try:
            pid = int(row["product_id"])
            flag = resolve_exception_flag(row)
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
            continue
        old_orig = parse_money(row.get("old_original_price"))
        try:
            proposed_orig = parse_manifest_proposed_original(
                row.get("proposed_original_price")
            )
        except ValueError as exc:
            errors.append(f"product_id={row.get('product_id')}: {exc}")
            continue
        if flag:
            exception_ids.add(pid)
            if proposed_orig is not None:
                errors.append(
                    f"product_id={pid}: authorized exception requires NULL proposed_original"
                )
        else:
            non_exception_ids.add(pid)
            if not money_equal_nullable(proposed_orig, old_orig):
                errors.append(
                    f"product_id={pid}: unauthorized original_price mutation "
                    f"proposed={proposed_orig} old={old_orig}"
                )
    if exception_ids != AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS:
        errors.append(
            f"exception_product_ids={sorted(exception_ids)} "
            f"expected={sorted(AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS)}"
        )
    if len(exception_ids) != EXPECTED_ORIGINAL_EXCEPTION_COUNT:
        errors.append(
            f"exception_count={len(exception_ids)} "
            f"expected={EXPECTED_ORIGINAL_EXCEPTION_COUNT}"
        )
    if len(non_exception_ids) != EXPECTED_NON_EXCEPTION_ORIGINAL_COUNT:
        errors.append(
            f"non_exception_count={len(non_exception_ids)} "
            f"expected={EXPECTED_NON_EXCEPTION_ORIGINAL_COUNT}"
        )
    return {
        "ok": not errors,
        "errors": errors,
        "exception_product_ids": sorted(exception_ids),
        "non_exception_count": len(non_exception_ids),
    }


def normalize_manifest_from_csv_rows(
    raw_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """DictReader rows → typed manifest rows with validated exception flags."""
    contract = validate_owner_frozen_commercial_contract(raw_rows)
    if not contract["ok"]:
        detail = "; ".join(contract["errors"][:20])
        raise ValueError(f"frozen manifest commercial contract failed: {detail}")
    normalized: list[dict[str, Any]] = []
    for raw in raw_rows:
        pid = int(raw["product_id"])
        flag = resolve_exception_flag(raw)
        normalized.append(
            {
                **raw,
                "product_id": pid,
                "authorized_original_price_exception": flag,
            }
        )
    normalized.sort(key=lambda r: int(r["product_id"]))
    return normalized


def rehearsal_contract_summary() -> dict[str, int | list[int]]:
    return {
        "base_price_updates": EXPECTED_PRICED_COHORT_ROWS,
        "original_price_updates": EXPECTED_ORIGINAL_EXCEPTION_COUNT,
        "base_price_change_logs": EXPECTED_PRICED_COHORT_ROWS,
        "original_price_change_logs": EXPECTED_ORIGINAL_EXCEPTION_COUNT,
        "total_event_logs": EXPECTED_TOTAL_EVENT_LOG_ROWS,
        "exception_product_ids": sorted(AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS),
    }


def _sql_exception_literal(row: dict[str, Any]) -> str:
    flag = row.get("authorized_original_price_exception")
    if not isinstance(flag, bool):
        raise TypeError(
            "authorized_original_price_exception must be bool before SQL generation"
        )
    pid = int(row["product_id"])
    must_exception = pid in AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS
    if flag != must_exception:
        raise ValueError(f"SQL generation exception flag mismatch product_id={pid}")
    return "TRUE" if flag else "FALSE"


def _assert_rows_ready_for_sql(rows: list[dict[str, Any]], expected_rows: int) -> None:
    if len(rows) != expected_rows:
        raise ValueError(f"rows {len(rows)} != expected_rows {expected_rows}")
    contract = validate_owner_frozen_commercial_contract(rows)
    if not contract["ok"]:
        raise ValueError(
            "manifest commercial contract invalid for SQL: "
            + "; ".join(contract["errors"][:10])
        )



def proposed_base_price(current: Decimal) -> Decimal:
    if current <= 0:
        raise ValueError("current base_price must be positive")
    return (current * MULTIPLIER).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def discount_display_state(
    *,
    base_price: Decimal,
    original_price: Decimal | None,
) -> str:
    """Describe compare-at discount visibility for reporting only."""
    if original_price is None or original_price <= 0:
        return "no_compare_at"
    if base_price < original_price:
        return "discounted"
    if base_price == original_price:
        return "no_discount_equal"
    return "above_compare_at"


def discount_impact_row(
    *,
    old_base: Decimal,
    new_base: Decimal,
    original_price: Decimal | None,
) -> dict[str, Any] | None:
    before = discount_display_state(base_price=old_base, original_price=original_price)
    after = discount_display_state(base_price=new_base, original_price=original_price)
    if before == after:
        return None
    return {
        "before": before,
        "after": after,
        "original_price": str(original_price) if original_price is not None else None,
        "old_base_price": str(old_base),
        "new_base_price": str(new_base),
    }


def build_manifest_row(raw: dict[str, Any]) -> dict[str, Any]:
    pid = int(raw["id"])
    old = parse_money(raw.get("old_base_price") or raw.get("base_price"))
    if old is None or old <= 0:
        raise ValueError(f"invalid old base_price for product {raw.get('id')}")
    new = proposed_base_price(old)
    old_original = parse_money(raw.get("original_price"))
    authorized = is_authorized_original_null_exception(pid)
    if authorized:
        proposed_original = None
    else:
        proposed_original = old_original
    before = discount_display_state(base_price=old, original_price=old_original)
    after = discount_display_state(base_price=new, original_price=proposed_original)
    impact = None if before == after else {
        "before": before,
        "after": after,
        "old_original_price": str(old_original) if old_original is not None else None,
        "proposed_original_price": (
            str(proposed_original) if proposed_original is not None else None
        ),
        "old_base_price": str(old),
        "new_base_price": str(new),
    }
    return {
        "product_id": pid,
        "sku": str(raw.get("sku") or "").strip(),
        "name": str(raw.get("name") or "").strip(),
        "slug": str(raw.get("slug") or "").strip(),
        "brand_id": int(raw.get("brand_id") or EXPECTED_BRAND_ID),
        "brand_name": str(raw.get("brand_name") or EXPECTED_BRAND_NAME).strip(),
        "category_id": raw.get("category_id"),
        "product_type_id": raw.get("product_type_id"),
        "old_base_price": f"{old:.2f}",
        "proposed_base_price": f"{new:.2f}",
        "old_original_price": f"{old_original:.2f}" if old_original is not None else None,
        "proposed_original_price": (
            f"{proposed_original:.2f}" if proposed_original is not None else None
        ),
        "authorized_original_price_exception": authorized,
        "is_active": raw.get("is_active"),
        "is_available": raw.get("is_available"),
        "deleted_at": raw.get("deleted_at"),
        "discount_impact": impact,
    }


def is_truthy_active(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def manifest_product_ids(manifest: list[dict[str, Any]]) -> list[int]:
    return [int(row["product_id"]) for row in manifest]


def validate_frozen_manifest_authority(
    manifest: list[dict[str, Any]],
    *,
    csv_sha256: str,
) -> dict[str, Any]:
    """Owner-approved frozen manifest: exact SHA256 and 206 unique eligible IDs."""
    errors: list[str] = []
    sha_norm = csv_sha256.strip().lower()
    if sha_norm != FROZEN_MANIFEST_SHA256.lower():
        errors.append("frozen_manifest_sha256_mismatch")
    ids = manifest_product_ids(manifest)
    unique_ids = set(ids)
    if len(manifest) != EXPECTED_PRICED_COHORT_ROWS:
        errors.append(f"row_count_not_{EXPECTED_PRICED_COHORT_ROWS}")
    if len(unique_ids) != EXPECTED_PRICED_COHORT_ROWS:
        errors.append(f"unique_product_ids_not_{EXPECTED_PRICED_COHORT_ROWS}")
    if len(ids) != len(unique_ids):
        errors.append("duplicate_product_ids_in_manifest")
    return {
        "ok": not errors,
        "errors": errors,
        "expected_sha256": FROZEN_MANIFEST_SHA256,
        "actual_sha256": sha_norm,
        "row_count": len(manifest),
        "unique_product_ids": len(unique_ids),
    }


def evaluate_frozen_handoff_readiness(
    *,
    manifest_authority: dict[str, Any],
    cohort_membership: dict[str, Any],
    drift_report: dict[str, Any],
    idempotency: dict[str, Any],
    priced_census: int,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not manifest_authority.get("ok"):
        blockers.extend(manifest_authority.get("errors") or ["manifest_authority"])
    if priced_census != EXPECTED_PRICED_COHORT_ROWS:
        blockers.append(f"live_priced_census_{priced_census}")
    if not cohort_membership.get("ok"):
        blockers.append("cohort_membership_mismatch")
    if not drift_report.get("ok"):
        blockers.append("per_row_price_drift")
    if idempotency.get("already_present"):
        blockers.append("idempotency_logs_present")
    if idempotency.get("original_clear_already_present"):
        blockers.append("idempotency_original_clear_logs_present")
    return {
        "ok": not blockers,
        "blockers": blockers,
        "manifest_authority": manifest_authority,
        "cohort_membership": cohort_membership,
        "drift": drift_report,
        "idempotency": idempotency,
        "priced_census": priced_census,
    }


def handoff_must_not_reference_legacy_rollback(handoff_text: str) -> bool:
    """Regression guard: legacy unguarded rollback must not appear as executable .sql."""
    forbidden = "INSIZE_PRICE_110_20261021_ROLLBACK_20261019T122730Z.sql"
    for line in handoff_text.splitlines():
        stripped = line.strip()
        if forbidden in stripped and ".non-executable" not in stripped:
            return False
    return True


def cohort_id_set_diff(
    manifest_ids: set[int],
    live_ids: set[int],
) -> dict[str, list[int]]:
    return {
        "extra_in_live": sorted(live_ids - manifest_ids),
        "missing_from_live": sorted(manifest_ids - live_ids),
    }


def validate_production_identity_gates(proof: dict[str, Any]) -> list[str]:
    """Fail-closed on independently collected production proof (not collector labels)."""
    errors: list[str] = []
    gates = proof.get("gates") or {}
    required_gates = (
        "host_ok",
        "container_ok",
        "db_ok",
        "user_ok",
        "volume_ok",
        "pg_system_identifier_ok",
        "alembic_ok",
        "transaction_read_only_on",
    )
    for gate in required_gates:
        if not gates.get(gate):
            errors.append(f"identity_gate_failed:{gate}")
    data_plane = proof.get("karzar_data_plane")
    if data_plane is not None and str(data_plane).strip() and str(data_plane).strip() != "live":
        errors.append(f"karzar_data_plane={data_plane!r}")
    if proof.get("host_proof") != EXPECTED_VPS_HOSTNAME:
        errors.append(f"host_proof={proof.get('host_proof')!r}")
    if proof.get("database_proof") != EXPECTED_DATABASE:
        errors.append(f"database_proof={proof.get('database_proof')!r}")
    if proof.get("pg_system_identifier") != EXPECTED_PG_SYSTEM_IDENTIFIER:
        errors.append("pg_system_identifier_mismatch")
    return errors


def reconcile_collector_vs_proof(
    collector_identity: dict[str, Any],
    proof: dict[str, Any],
) -> list[str]:
    """Collector labels are evidence only — must match independent proof."""
    errors: list[str] = []
    if collector_identity.get("vps_hostname") != proof.get("host_proof"):
        errors.append("collector_hostname_disagrees_with_ssh_proof")
    if collector_identity.get("postgres_container") != EXPECTED_POSTGRES_CONTAINER:
        errors.append("collector_postgres_container_label_invalid")
    container_proof = str(proof.get("container_proof") or "").lstrip("/")
    if EXPECTED_POSTGRES_CONTAINER not in container_proof:
        errors.append("container_proof_mismatch")
    if collector_identity.get("postgres_db_name") != proof.get("database_proof"):
        errors.append("collector_db_name_disagrees_with_psql_proof")
    return errors


def evaluate_db_post_apply_verification(
    verify: dict[str, Any],
    *,
    expected_rows: int,
    expected_sum: Decimal | None = None,
) -> dict[str, Any]:
    target = int(verify.get("target_rows") or expected_rows)
    exact = int(verify.get("price_exact_match") or 0)
    formula = int(verify.get("formula_matches") or 0)
    base_logs = int(verify.get("base_change_log_rows") or verify.get("change_log_rows_with_reason") or 0)
    orig_logs = int(verify.get("original_change_log_rows") or 0)
    total_logs = int(verify.get("total_event_log_rows") or (base_logs + orig_logs))
    distinct = int(verify.get("distinct_changed_product_ids") or 0)
    dups = int(verify.get("duplicate_mutations") or 0)
    orig_null_ok = int(verify.get("original_null_exception_count") or 0)
    orig_unchanged_ok = int(verify.get("original_unchanged_non_exception_count") or 0)
    unexpected_orig = int(verify.get("unexpected_original_mutations") or 0)
    unexpected_orig_logs = int(verify.get("unexpected_original_change_logs") or 0)
    post_sum_raw = verify.get("sum_base_price_post")
    post_sum = parse_money(str(post_sum_raw)) if post_sum_raw is not None else None
    sum_ok = True
    if expected_sum is not None and post_sum is not None:
        sum_ok = post_sum == expected_sum
    elif expected_sum is not None:
        sum_ok = False
    original_ok = (
        orig_null_ok == EXPECTED_ORIGINAL_EXCEPTION_COUNT
        and orig_unchanged_ok == EXPECTED_NON_EXCEPTION_ORIGINAL_COUNT
        and unexpected_orig == 0
        and unexpected_orig_logs == 0
    )
    logs_ok = (
        base_logs == expected_rows
        and orig_logs == EXPECTED_ORIGINAL_EXCEPTION_COUNT
        and total_logs == EXPECTED_TOTAL_EVENT_LOG_ROWS
    )
    db_ok = (
        target == expected_rows
        and exact == expected_rows
        and formula == expected_rows
        and logs_ok
        and distinct == expected_rows
        and dups == 0
        and sum_ok
        and original_ok
    )
    return {
        "db_verification_ok": db_ok,
        "price_exact_match": exact,
        "formula_matches": formula,
        "base_change_log_rows": base_logs,
        "original_change_log_rows": orig_logs,
        "total_event_log_rows": total_logs,
        "change_log_rows_with_reason": base_logs,
        "distinct_changed_product_ids": distinct,
        "duplicate_mutations": dups,
        "original_null_exception_count": orig_null_ok,
        "original_unchanged_non_exception_count": orig_unchanged_ok,
        "unexpected_original_mutations": unexpected_orig,
        "unexpected_original_change_logs": unexpected_orig_logs,
        "original_price_verification_ok": original_ok,
        "sum_base_price_post": str(post_sum) if post_sum is not None else post_sum_raw,
        "expected_sum_ok": sum_ok,
    }


def select_public_api_verification_candidates(
    manifest: list[dict[str, Any]],
    *,
    minimum: int = MIN_PUBLIC_API_PRICE_VERIFICATIONS,
) -> list[dict[str, Any]]:
    picks: list[dict[str, Any]] = []
    for pid in sorted(AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS):
        for row in manifest:
            if int(row["product_id"]) == pid and row not in picks:
                picks.append(row)
                break
    active = [r for r in manifest if is_truthy_active(r.get("is_active"))]
    for bucket in (active, manifest):
        for row in bucket:
            if len(picks) >= minimum:
                break
            pid = int(row["product_id"])
            if any(int(p["product_id"]) == pid for p in picks):
                continue
            picks.append(row)
        if len(picks) >= minimum:
            break
    if len(picks) < minimum:
        picks = manifest[:minimum]
    return picks[: max(minimum, len(picks))]


def classify_api_sample_result(
    *,
    row: dict[str, Any],
    http_ok: bool,
    http_status: int | None,
    api_base_price: str | None,
    error: str | None = None,
) -> dict[str, Any]:
    expected = str(row["proposed_base_price"])
    active = is_truthy_active(row.get("is_active"))
    base = {
        "product_id": int(row["product_id"]),
        "slug": row.get("slug"),
        "is_active": active,
        "expected_base_price": expected,
        "http_ok": http_ok,
        "http_status": http_status,
        "api_base_price": api_base_price,
        "error": error,
    }
    if http_status == 404 and not active:
        base["verification"] = "inactive_not_public"
        base["counts_as_public_price_verified"] = False
        return base
    if not http_ok:
        base["verification"] = "http_failed"
        base["counts_as_public_price_verified"] = False
        return base
    expected_dec = parse_money(expected)
    api_dec = parse_money(api_base_price) if api_base_price is not None else None
    if expected_dec is not None and api_dec is not None and expected_dec == api_dec:
        base["verification"] = "price_match"
        base["counts_as_public_price_verified"] = True
        return base
    base["verification"] = "price_mismatch"
    base["counts_as_public_price_verified"] = False
    return base


def evaluate_api_verification(
    samples: list[dict[str, Any]],
    *,
    required_verified: int,
) -> dict[str, Any]:
    verified = [s for s in samples if s.get("counts_as_public_price_verified")]
    mismatches = [s for s in samples if s.get("verification") == "price_mismatch"]
    http_failed = [s for s in samples if s.get("verification") == "http_failed"]
    inactive = [s for s in samples if s.get("verification") == "inactive_not_public"]
    api_ok = len(verified) >= required_verified and not mismatches and not http_failed
    return {
        "api_verification_ok": api_ok,
        "required_public_price_verifications": required_verified,
        "public_price_verified_count": len(verified),
        "http_failed_count": len(http_failed),
        "price_mismatch_count": len(mismatches),
        "inactive_not_public_count": len(inactive),
        "all_http_ok": len(http_failed) == 0,
        "all_match": api_ok,
    }


def resolve_post_commit_status(
    *,
    db_committed: bool,
    db_verification_ok: bool,
    api_verification_ok: bool,
) -> tuple[str, str]:
    if not db_committed:
        return "BLOCKED", "INSIZE_PRICE_110_20261021_COMMIT_FAILED"
    if db_verification_ok and api_verification_ok:
        return "COMMITTED_VERIFIED", "INSIZE_PRICE_110_20261021_COMMIT_AND_VERIFY_OK"
    return "PARTIALLY_VERIFIED", "INSIZE_PRICE_110_20261021_VERIFY_INCOMPLETE"


def _sql_money(value: str | Decimal | None) -> str:
    if value is None or value == "":
        return "NULL"
    return f"{sql_literal(str(value))}::numeric"



def build_rollback_sql(rows: list[dict[str, Any]]) -> str:
    """Rollback base_price for full cohort; restore original_price for authorized exceptions only."""
    assert_change_reason()
    if not rows:
        raise ValueError("rollback requires manifest rows")
    expected_rows = len(rows)
    _assert_rows_ready_for_sql(rows, expected_rows)
    base_reason = sql_literal(ROLLBACK_CHANGE_REASON)
    orig_reason = sql_literal(
        "INSIZE +10% rollback restore original_price (exceptions) 2026-10-21"
    )
    values = ",\n  ".join(
        f"({int(r['product_id'])}, {sql_literal(r['sku'])}, "
        f"{_sql_money(r['old_base_price'])}, {_sql_money(r['proposed_base_price'])}, "
        f"{_sql_money(r.get('old_original_price'))}, "
        f"{_sql_exception_literal(r)})"
        for r in sorted(rows, key=lambda r: int(r["product_id"]))
    )
    exception_n = EXPECTED_ORIGINAL_EXCEPTION_COUNT
    return f"""
BEGIN ISOLATION LEVEL SERIALIZABLE;

CREATE TEMP TABLE insize_p110_rollback_expected (
  product_id integer PRIMARY KEY,
  expected_sku text NOT NULL,
  restore_base_price numeric(12,2) NOT NULL,
  applied_base_price numeric(12,2) NOT NULL,
  restore_original_price numeric(12,2),
  clear_original_exception boolean NOT NULL DEFAULT FALSE
) ON COMMIT DROP;
INSERT INTO insize_p110_rollback_expected
  (product_id, expected_sku, restore_base_price, applied_base_price, restore_original_price, clear_original_exception)
VALUES
  {values};

DO $$
DECLARE
  expected_n integer := {expected_rows};
  expected_exception_n integer := {exception_n};
  guard_n integer;
  updated_n integer;
  log_n integer;
  orig_n integer;
  orig_log_n integer;
BEGIN
  SELECT COUNT(*) INTO orig_n
  FROM insize_p110_rollback_expected
  WHERE clear_original_exception IS TRUE AND product_id NOT IN ();
  IF orig_n > 0 THEN
    RAISE EXCEPTION 'rollback exception flags outside whitelist=%', orig_n;
  END IF;

  SELECT COUNT(*) INTO guard_n
  FROM insize_p110_rollback_expected e
  JOIN products p ON p.id = e.product_id
  WHERE p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.sku IS NOT DISTINCT FROM e.expected_sku
    AND p.base_price IS NOT DISTINCT FROM e.applied_base_price;
  IF guard_n <> expected_n THEN
    RAISE EXCEPTION 'rollback guard failed: matching applied base rows=% expected=%', guard_n, expected_n;
  END IF;

  UPDATE products p
  SET base_price = e.restore_base_price,
      updated_at = NOW()
  FROM insize_p110_rollback_expected e
  WHERE p.id = e.product_id
    AND p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.sku IS NOT DISTINCT FROM e.expected_sku
    AND p.base_price IS NOT DISTINCT FROM e.applied_base_price;
  GET DIAGNOSTICS updated_n = ROW_COUNT;
  IF updated_n <> expected_n THEN
    RAISE EXCEPTION 'rollback updated base rows=% expected=%', updated_n, expected_n;
  END IF;

  UPDATE products p
  SET original_price = e.restore_original_price,
      updated_at = NOW()
  FROM insize_p110_rollback_expected e
  WHERE p.id = e.product_id
    AND e.clear_original_exception IS TRUE
    AND p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.original_price IS NULL;
  GET DIAGNOSTICS orig_n = ROW_COUNT;
  IF orig_n <> expected_exception_n THEN
    RAISE EXCEPTION 'rollback original restore rows=% expected=%', orig_n, expected_exception_n;
  END IF;

  INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
  SELECT e.product_id, 'base_price', e.applied_base_price::text, e.restore_base_price::text,
         {base_reason}, NULL
  FROM insize_p110_rollback_expected e
  ORDER BY e.product_id;
  GET DIAGNOSTICS log_n = ROW_COUNT;
  IF log_n <> expected_n THEN
    RAISE EXCEPTION 'rollback base change_log rows=% expected=%', log_n, expected_n;
  END IF;

  INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
  SELECT e.product_id, 'original_price', NULL, e.restore_original_price::text,
         {orig_reason}, NULL
  FROM insize_p110_rollback_expected e
  WHERE e.clear_original_exception IS TRUE
  ORDER BY e.product_id;
  GET DIAGNOSTICS orig_log_n = ROW_COUNT;
  IF orig_log_n <> expected_exception_n THEN
    RAISE EXCEPTION 'rollback original change_log rows=% expected=%', orig_log_n, expected_exception_n;
  END IF;
END $$;

COMMIT;
"""


def build_real_apply_sql(
    rows: list[dict[str, Any]],
    *,
    expected_rows: int,
    manifest_sha256: str,
) -> str:
    assert_change_reason()
    _assert_rows_ready_for_sql(rows, expected_rows)
    base_reason = sql_literal(CHANGE_REASON)
    orig_reason = sql_literal(ORIGINAL_PRICE_CLEAR_CHANGE_REASON)
    values = ",\n  ".join(
        f"({int(r['product_id'])}, {sql_literal(r['sku'])}, "
        f"{_sql_money(r['old_base_price'])}, {_sql_money(r['proposed_base_price'])}, "
        f"{_sql_money(r.get('old_original_price'))}, "
        f"{_sql_money(r.get('proposed_original_price'))}, "
        f"{_sql_exception_literal(r)})"
        for r in rows
    )
    exception_n = EXPECTED_ORIGINAL_EXCEPTION_COUNT
    expected_total_logs = EXPECTED_TOTAL_EVENT_LOG_ROWS
    authorized_ids_sql = AUTHORIZED_EXCEPTION_IDS_SQL
    return f"""
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT pg_advisory_xact_lock(hashtext({sql_literal(ADVISORY_LOCK_KEY)}));

CREATE TEMP TABLE insize_p110_expected (
  product_id integer PRIMARY KEY,
  expected_sku text NOT NULL,
  old_base_price numeric(12,2) NOT NULL,
  new_base_price numeric(12,2) NOT NULL,
  old_original_price numeric(12,2),
  new_original_price numeric(12,2),
  clear_original_exception boolean NOT NULL DEFAULT FALSE
) ON COMMIT DROP;
INSERT INTO insize_p110_expected (
  product_id, expected_sku, old_base_price, new_base_price,
  old_original_price, new_original_price, clear_original_exception
)
VALUES
  {values};

DO $$
DECLARE
  expected_n integer := {expected_rows};
  exception_n integer := {exception_n};
  expected_total_logs integer := {expected_total_logs};
  exception_flag_n integer;
  locked_n integer;
  cohort_n integer;
  extra_n integer;
  idem_n integer;
  idem_orig_n integer;
  drift_n integer;
  drift_orig_n integer;
  updated_n integer;
  log_n integer;
  orig_n integer;
  orig_log_n integer;
  formula_bad integer;
BEGIN
  SELECT COUNT(*) INTO idem_n FROM product_change_logs WHERE reason = {base_reason};
  IF idem_n > 0 THEN
    RAISE EXCEPTION 'idempotency: % existing base_price change logs', idem_n;
  END IF;
  SELECT COUNT(*) INTO idem_orig_n FROM product_change_logs WHERE reason = {orig_reason};
  IF idem_orig_n > 0 THEN
    RAISE EXCEPTION 'idempotency: % existing original_price change logs', idem_orig_n;
  END IF;

  SELECT COUNT(*) INTO exception_flag_n FROM insize_p110_expected WHERE clear_original_exception IS TRUE;
  IF exception_flag_n <> exception_n THEN
    RAISE EXCEPTION 'temp exception flags=% expected=%', exception_flag_n, exception_n;
  END IF;

  SELECT COUNT(*) INTO exception_flag_n FROM insize_p110_expected
    WHERE clear_original_exception IS TRUE AND product_id NOT IN ({authorized_ids_sql});
  IF exception_flag_n > 0 THEN
    RAISE EXCEPTION 'temp exception flags outside whitelist=%', exception_flag_n;
  END IF;

  SELECT COUNT(*) INTO exception_flag_n FROM insize_p110_expected
    WHERE product_id IN ({authorized_ids_sql}) AND clear_original_exception IS NOT TRUE;
  IF exception_flag_n > 0 THEN
    RAISE EXCEPTION 'authorized ids missing exception flag=%', exception_flag_n;
  END IF;

  PERFORM 1
  FROM products p
  JOIN insize_p110_expected e ON e.product_id = p.id
  WHERE p.deleted_at IS NULL AND p.brand_id = {EXPECTED_BRAND_ID}
  FOR UPDATE OF p;

  SELECT COUNT(*) INTO locked_n
  FROM products p
  JOIN insize_p110_expected e ON e.product_id = p.id
  WHERE p.deleted_at IS NULL AND p.brand_id = {EXPECTED_BRAND_ID};
  IF locked_n <> expected_n THEN
    RAISE EXCEPTION 'lock cohort mismatch: locked=% expected=%', locked_n, expected_n;
  END IF;

  SELECT COUNT(*) INTO cohort_n
  FROM products p
  WHERE p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.base_price IS NOT NULL
    AND p.base_price > 0;
  IF cohort_n <> expected_n THEN
    RAISE EXCEPTION 'cohort census mismatch: live=% expected=%', cohort_n, expected_n;
  END IF;

  SELECT COUNT(*) INTO extra_n
  FROM products p
  WHERE p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.base_price IS NOT NULL
    AND p.base_price > 0
    AND NOT EXISTS (SELECT 1 FROM insize_p110_expected e WHERE e.product_id = p.id);
  IF extra_n > 0 THEN
    RAISE EXCEPTION 'cohort extra eligible products=%', extra_n;
  END IF;

  SELECT COUNT(*) INTO drift_n
  FROM insize_p110_expected e
  JOIN products p ON p.id = e.product_id
  WHERE p.deleted_at IS NULL AND p.brand_id = {EXPECTED_BRAND_ID}
    AND (p.sku IS DISTINCT FROM e.expected_sku
         OR p.base_price IS DISTINCT FROM e.old_base_price);
  IF drift_n > 0 THEN
    RAISE EXCEPTION 'concurrent drift rows=% (sku/base_price)', drift_n;
  END IF;

  SELECT COUNT(*) INTO drift_orig_n
  FROM insize_p110_expected e
  JOIN products p ON p.id = e.product_id
  WHERE e.clear_original_exception IS TRUE
    AND p.deleted_at IS NULL AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.original_price IS DISTINCT FROM e.old_original_price;
  IF drift_orig_n > 0 THEN
    RAISE EXCEPTION 'concurrent original_price drift rows=%', drift_orig_n;
  END IF;

  SELECT COUNT(*) INTO formula_bad
  FROM insize_p110_expected e
  WHERE e.new_base_price <> round(e.old_base_price * 1.10, 2);
  IF formula_bad > 0 THEN
    RAISE EXCEPTION 'formula mismatch rows=%', formula_bad;
  END IF;

  UPDATE products p
  SET base_price = e.new_base_price,
      updated_at = NOW()
  FROM insize_p110_expected e
  WHERE p.id = e.product_id
    AND p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.base_price = e.old_base_price;
  GET DIAGNOSTICS updated_n = ROW_COUNT;
  IF updated_n <> expected_n THEN
    RAISE EXCEPTION 'updated base rows=% expected=%', updated_n, expected_n;
  END IF;

  UPDATE products p
  SET original_price = NULL,
      updated_at = NOW()
  FROM insize_p110_expected e
  WHERE p.id = e.product_id
    AND e.clear_original_exception IS TRUE
    AND p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.original_price IS NOT DISTINCT FROM e.old_original_price;
  GET DIAGNOSTICS orig_n = ROW_COUNT;
  IF orig_n <> exception_n THEN
    RAISE EXCEPTION 'cleared original_price rows=% expected=%', orig_n, exception_n;
  END IF;

  INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
  SELECT e.product_id, 'base_price', e.old_base_price::text, e.new_base_price::text,
         {base_reason}, NULL
  FROM insize_p110_expected e
  ORDER BY e.product_id;
  GET DIAGNOSTICS log_n = ROW_COUNT;
  IF log_n <> expected_n THEN
    RAISE EXCEPTION 'base change_log rows=% expected=%', log_n, expected_n;
  END IF;

  INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
  SELECT e.product_id, 'original_price', e.old_original_price::text, NULL,
         {orig_reason}, NULL
  FROM insize_p110_expected e
  WHERE e.clear_original_exception IS TRUE
  ORDER BY e.product_id;
  GET DIAGNOSTICS orig_log_n = ROW_COUNT;
  IF orig_log_n <> exception_n THEN
    RAISE EXCEPTION 'original change_log rows=% expected=%', orig_log_n, exception_n;
  END IF;

  IF log_n + orig_log_n <> {expected_total_logs} THEN
    RAISE EXCEPTION 'total event logs=% expected=%', log_n + orig_log_n, {expected_total_logs};
  END IF;

  SELECT COUNT(*) INTO orig_n
  FROM insize_p110_expected e
  JOIN products p ON p.id = e.product_id
  WHERE NOT e.clear_original_exception
    AND p.deleted_at IS NULL AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.original_price IS DISTINCT FROM e.old_original_price;
  IF orig_n > 0 THEN
    RAISE EXCEPTION 'unauthorized original_price mutations=%', orig_n;
  END IF;

  SELECT COUNT(*) INTO orig_n
  FROM insize_p110_expected e
  JOIN products p ON p.id = e.product_id
  WHERE e.clear_original_exception IS TRUE
    AND e.product_id NOT IN ({authorized_ids_sql})
    AND p.deleted_at IS NULL AND p.brand_id = {EXPECTED_BRAND_ID};
  IF orig_n > 0 THEN
    RAISE EXCEPTION 'original clear outside whitelist rows=%', orig_n;
  END IF;

  SELECT COUNT(*) INTO orig_n
  FROM insize_p110_expected e
  WHERE e.clear_original_exception IS TRUE AND e.product_id NOT IN ({authorized_ids_sql});
  IF orig_n > 0 THEN
    RAISE EXCEPTION 'exception flag set outside whitelist rows=%', orig_n;
  END IF;

  SELECT COUNT(*) INTO orig_n
  FROM insize_p110_expected e
  WHERE e.product_id IN ({authorized_ids_sql}) AND e.clear_original_exception IS NOT TRUE;
  IF orig_n > 0 THEN
    RAISE EXCEPTION 'authorized exception ids missing clear flag rows=%', orig_n;
  END IF;
END $$;

COMMIT;
-- manifest_sha256={manifest_sha256}
"""
