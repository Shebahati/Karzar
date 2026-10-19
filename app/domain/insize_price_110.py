"""INSIZE +10% owner-authorized base_price APPLY (2026-10-19). Pure helpers — no I/O."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.domain.phase2c_apply import sql_literal

EXPECTED_BRAND_ID = 3
EXPECTED_BRAND_NAME = "INSIZE | اینسایز"
CHANGE_REASON = "INSIZE +10% owner-authorized price update 2026-10-19"
ROLLBACK_CHANGE_REASON = (
    "INSIZE +10% rollback restore exact pre-apply base_price 2026-10-19"
)
MULTIPLIER = Decimal("1.10")
ADVISORY_LOCK_KEY = "karzar:insize:price110:20261019"
FROZEN_MANIFEST_SHA256 = (
    "edd614107db14d9ae96e6a5d5c2b04043f95c413e6902d45fc3de7d8228feee1"
)
EXPECTED_PRICED_COHORT_ROWS = 206
EXPECTED_PREFLIGHT_BASE_SUM = Decimal("3103326000.00")
EXPECTED_POST_APPLY_BASE_SUM = Decimal("3413658600.00")
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
    "app/domain/insize_price_110.py",
    "scripts/ops/insize_price_110_apply_once.py",
)


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
    old = parse_money(raw.get("old_base_price") or raw.get("base_price"))
    if old is None or old <= 0:
        raise ValueError(f"invalid old base_price for product {raw.get('id')}")
    new = proposed_base_price(old)
    original = parse_money(raw.get("original_price"))
    impact = discount_impact_row(old_base=old, new_base=new, original_price=original)
    return {
        "product_id": int(raw["id"]),
        "sku": str(raw.get("sku") or "").strip(),
        "name": str(raw.get("name") or "").strip(),
        "slug": str(raw.get("slug") or "").strip(),
        "brand_id": int(raw.get("brand_id") or EXPECTED_BRAND_ID),
        "brand_name": str(raw.get("brand_name") or EXPECTED_BRAND_NAME).strip(),
        "category_id": raw.get("category_id"),
        "product_type_id": raw.get("product_type_id"),
        "old_base_price": f"{old:.2f}",
        "proposed_base_price": f"{new:.2f}",
        "original_price": f"{original:.2f}" if original is not None else None,
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
    logs = int(verify.get("change_log_rows_with_reason") or 0)
    distinct = int(verify.get("distinct_changed_product_ids") or 0)
    dups = int(verify.get("duplicate_mutations") or 0)
    post_sum_raw = verify.get("sum_base_price_post")
    post_sum = parse_money(str(post_sum_raw)) if post_sum_raw is not None else None
    sum_ok = True
    if expected_sum is not None and post_sum is not None:
        sum_ok = post_sum == expected_sum
    elif expected_sum is not None:
        sum_ok = False
    db_ok = (
        target == expected_rows
        and exact == expected_rows
        and formula == expected_rows
        and logs == expected_rows
        and distinct == expected_rows
        and dups == 0
        and sum_ok
    )
    return {
        "db_verification_ok": db_ok,
        "price_exact_match": exact,
        "formula_matches": formula,
        "change_log_rows_with_reason": logs,
        "distinct_changed_product_ids": distinct,
        "duplicate_mutations": dups,
        "sum_base_price_post": str(post_sum) if post_sum is not None else post_sum_raw,
        "expected_sum_ok": sum_ok,
    }


def select_public_api_verification_candidates(
    manifest: list[dict[str, Any]],
    *,
    minimum: int = MIN_PUBLIC_API_PRICE_VERIFICATIONS,
) -> list[dict[str, Any]]:
    active = [r for r in manifest if is_truthy_active(r.get("is_active"))]
    picks: list[dict[str, Any]] = []
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
    if api_base_price == expected:
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
        return "BLOCKED", "INSIZE_PRICE_110_COMMIT_FAILED"
    if db_verification_ok and api_verification_ok:
        return "COMMITTED_VERIFIED", "INSIZE_PRICE_110_COMMIT_AND_VERIFY_OK"
    return "PARTIALLY_VERIFIED", "INSIZE_PRICE_110_VERIFY_INCOMPLETE"


def build_rollback_sql(rows: list[dict[str, Any]]) -> str:
    """Atomic rollback — exact frozen pre-apply prices; requires post-APPLY price state."""
    assert_change_reason()
    if not rows:
        raise ValueError("rollback requires manifest rows")
    reason = sql_literal(ROLLBACK_CHANGE_REASON)
    values = ",\n  ".join(
        f"({int(r['product_id'])}, {sql_literal(r['sku'])}, "
        f"{sql_literal(r['old_base_price'])}::numeric, "
        f"{sql_literal(r['proposed_base_price'])}::numeric)"
        for r in sorted(rows, key=lambda r: int(r["product_id"]))
    )
    expected_rows = len(rows)
    return f"""
-- INSIZE +10% rollback — prepared recovery only (separate human authorization required)
-- Never divide by 1.10. Do not auto-run after verification failure.
BEGIN ISOLATION LEVEL SERIALIZABLE;

CREATE TEMP TABLE insize_p110_rollback_expected (
  product_id integer PRIMARY KEY,
  expected_sku text NOT NULL,
  restore_base_price numeric(12,2) NOT NULL,
  applied_base_price numeric(12,2) NOT NULL
) ON COMMIT DROP;
INSERT INTO insize_p110_rollback_expected
  (product_id, expected_sku, restore_base_price, applied_base_price)
VALUES
  {values};

DO $$
DECLARE
  expected_n integer := {expected_rows};
  guard_n integer;
  updated_n integer;
  log_n integer;
BEGIN
  SELECT COUNT(*) INTO guard_n
  FROM insize_p110_rollback_expected e
  JOIN products p ON p.id = e.product_id
  WHERE p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.sku IS NOT DISTINCT FROM e.expected_sku
    AND p.base_price IS NOT DISTINCT FROM e.applied_base_price;
  IF guard_n <> expected_n THEN
    RAISE EXCEPTION 'rollback guard failed: matching applied rows=% expected=%', guard_n, expected_n;
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
    RAISE EXCEPTION 'rollback updated rows=% expected=%', updated_n, expected_n;
  END IF;

  INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
  SELECT e.product_id, 'base_price', e.applied_base_price::text, e.restore_base_price::text,
         {reason}, NULL
  FROM insize_p110_rollback_expected e
  ORDER BY e.product_id;
  GET DIAGNOSTICS log_n = ROW_COUNT;
  IF log_n <> expected_n THEN
    RAISE EXCEPTION 'rollback change_log rows=% expected=%', log_n, expected_n;
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
    if len(rows) != expected_rows:
        raise ValueError(f"rows {len(rows)} != expected_rows {expected_rows}")
    reason = sql_literal(CHANGE_REASON)
    values = ",\n  ".join(
        f"({int(r['product_id'])}, {sql_literal(r['sku'])}, "
        f"{sql_literal(r['old_base_price'])}::numeric, {sql_literal(r['proposed_base_price'])}::numeric)"
        for r in rows
    )
    return f"""
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT pg_advisory_xact_lock(hashtext({sql_literal(ADVISORY_LOCK_KEY)}));

CREATE TEMP TABLE insize_p110_expected (
  product_id integer PRIMARY KEY,
  expected_sku text NOT NULL,
  old_base_price numeric(12,2) NOT NULL,
  new_base_price numeric(12,2) NOT NULL
) ON COMMIT DROP;
INSERT INTO insize_p110_expected (product_id, expected_sku, old_base_price, new_base_price)
VALUES
  {values};

DO $$
DECLARE
  expected_n integer := {expected_rows};
  locked_n integer;
  cohort_n integer;
  extra_n integer;
  idem_n integer;
  drift_n integer;
  updated_n integer;
  log_n integer;
  formula_bad integer;
BEGIN
  SELECT COUNT(*) INTO idem_n FROM product_change_logs WHERE reason = {reason};
  IF idem_n > 0 THEN
    RAISE EXCEPTION 'idempotency: % existing change logs with event reason', idem_n;
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

  PERFORM 1
  FROM products p
  WHERE p.deleted_at IS NULL
    AND p.brand_id = {EXPECTED_BRAND_ID}
    AND p.base_price IS NOT NULL
    AND p.base_price > 0
  FOR UPDATE OF p;

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
    AND NOT EXISTS (
      SELECT 1 FROM insize_p110_expected e WHERE e.product_id = p.id
    );
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
    RAISE EXCEPTION 'concurrent drift rows=% (sku/base_price changed since manifest)', drift_n;
  END IF;

  SELECT COUNT(*) INTO formula_bad
  FROM insize_p110_expected e
  WHERE e.new_base_price <>
    round(e.old_base_price * 1.10, 2);
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
    RAISE EXCEPTION 'updated rows=% expected=%', updated_n, expected_n;
  END IF;

  INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
  SELECT e.product_id, 'base_price', e.old_base_price::text, e.new_base_price::text,
         {reason}, NULL
  FROM insize_p110_expected e
  ORDER BY e.product_id;
  GET DIAGNOSTICS log_n = ROW_COUNT;
  IF log_n <> expected_n THEN
    RAISE EXCEPTION 'change_log rows=% expected=%', log_n, expected_n;
  END IF;
END $$;

COMMIT;
-- manifest_sha256={manifest_sha256}
"""
