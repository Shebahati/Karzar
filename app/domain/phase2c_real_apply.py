"""Phase 2C owner-authorized real manufacturer_code APPLY helpers (no DB I/O)."""

from __future__ import annotations

import re
from pathlib import Path

from app.domain.phase2c_apply import (
    OWNER_FROZEN_ROWS,
    OWNER_FROZEN_SHA256,
    sha256_file,
    sql_literal,
)

REAL_APPLY_ADVISORY_LOCK_KEY = "karzar:phase2c:manufacturer_code:apply"
REAL_APPLY_EXPECTED_ROWS = OWNER_FROZEN_ROWS

REAL_APPLY_LOGIC_FILES = (
    "app/domain/phase2c_real_apply.py",
    "scripts/ops/phase2c_manufacturer_identity_apply_once.py",
)


def real_apply_change_log_reason(cohort_sha256: str) -> str:
    """Owner-authorized real APPLY reason (VARCHAR(255); full cohort SHA required)."""
    reason = (
        "Phase 2C owner-authorized manufacturer identity backfill; "
        f"cohort_sha256={cohort_sha256}"
    )
    if len(reason) > 255:
        raise ValueError(f"change-log reason length {len(reason)} exceeds VARCHAR(255)")
    if cohort_sha256 not in reason:
        raise ValueError("change-log reason missing full cohort SHA256")
    return reason


def real_apply_logic_file_sha256(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in REAL_APPLY_LOGIC_FILES:
        path = repo_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"real-apply logic file missing: {rel}")
        out[rel] = sha256_file(path)
    return out


def build_recovery_target_rows(frozen_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [
        {
            "product_id": r["product_id"],
            "pre_apply_manufacturer_code": "",
            "applied_manufacturer_code": r["candidate_manufacturer_code"],
            "sku": r["sku"],
            "brand_id": r["brand_id"],
        }
        for r in frozen_rows
    ]
    rows.sort(key=lambda r: int(r["product_id"]))
    return rows


def build_real_apply_sql(
    frozen_rows: list[dict[str, str]],
    *,
    cohort_sha256: str,
    expected_rows: int = REAL_APPLY_EXPECTED_ROWS,
) -> str:
    """Build atomic SERIALIZABLE apply SQL that COMMITs only after DB-enforced gates."""
    if len(frozen_rows) != expected_rows:
        raise ValueError(f"frozen_rows {len(frozen_rows)} != expected_rows {expected_rows}")
    reason = real_apply_change_log_reason(cohort_sha256)
    expected_values = ",\n  ".join(
        f"({int(r['product_id'])}, {sql_literal(r['sku'])}, {int(r['brand_id'])}, "
        f"{sql_literal(r['candidate_manufacturer_code'])})"
        for r in frozen_rows
    )
    return f"""
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT pg_advisory_xact_lock(hashtext({sql_literal(REAL_APPLY_ADVISORY_LOCK_KEY)}));

CREATE TEMP TABLE p2c_expected (
  product_id integer PRIMARY KEY,
  expected_sku text NOT NULL,
  expected_brand_id integer NOT NULL,
  candidate_manufacturer_code text NOT NULL
) ON COMMIT DROP;
INSERT INTO p2c_expected (product_id, expected_sku, expected_brand_id, candidate_manufacturer_code)
VALUES
  {expected_values};

CREATE TEMP TABLE p2c_metrics (
  k text PRIMARY KEY,
  v bigint NOT NULL
) ON COMMIT DROP;

DO $$
DECLARE
  expected_n integer := {expected_rows};
  locked_n integer;
  null_n integer;
  sku_ok integer;
  brand_ok integer;
  deleted_n integer;
  updated_n integer;
  exact_n integer;
  log_n integer;
  protected_n integer;
  collision_n integer;
  nontarget_n integer;
  global_before integer;
  global_after integer;
BEGIN
  SELECT COUNT(*) INTO global_before
  FROM products WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL;
  IF global_before <> 0 THEN
    RAISE EXCEPTION 'pre-apply global manufacturer_code populated = % (must be 0)', global_before;
  END IF;

  -- Race-condition gate: lock every target row before mutation.
  PERFORM 1
  FROM products p
  JOIN p2c_expected e ON e.product_id = p.id
  FOR UPDATE OF p;

  CREATE TEMP TABLE p2c_locked ON COMMIT DROP AS
  SELECT p.id, p.name, p.sku, p.slug, p.brand_id, p.category_id, p.product_type_id,
         p.base_price, p.original_price, p.is_active, p.is_available, p.deleted_at,
         p.manufacturer_code
  FROM products p
  JOIN p2c_expected e ON e.product_id = p.id;

  SELECT COUNT(*) INTO locked_n FROM p2c_locked;
  IF locked_n <> expected_n THEN
    RAISE EXCEPTION 'locked targets = % (expected %)', locked_n, expected_n;
  END IF;

  SELECT COUNT(*) INTO null_n FROM p2c_locked WHERE manufacturer_code IS NULL;
  IF null_n <> expected_n THEN
    RAISE EXCEPTION 'manufacturer_code NULL among locked = % (expected %)', null_n, expected_n;
  END IF;

  SELECT COUNT(*) INTO sku_ok
  FROM p2c_locked l JOIN p2c_expected e ON e.product_id = l.id
  WHERE l.sku = e.expected_sku;
  IF sku_ok <> expected_n THEN
    RAISE EXCEPTION 'SKU exact among locked = % (expected %)', sku_ok, expected_n;
  END IF;

  SELECT COUNT(*) INTO brand_ok
  FROM p2c_locked l JOIN p2c_expected e ON e.product_id = l.id
  WHERE l.brand_id = e.expected_brand_id;
  IF brand_ok <> expected_n THEN
    RAISE EXCEPTION 'brand exact among locked = % (expected %)', brand_ok, expected_n;
  END IF;

  SELECT COUNT(*) INTO deleted_n FROM p2c_locked WHERE deleted_at IS NOT NULL;
  IF deleted_n <> 0 THEN
    RAISE EXCEPTION 'deleted locked targets = %', deleted_n;
  END IF;

  CREATE TEMP TABLE p2c_updated ON COMMIT DROP AS
  WITH u AS (
    UPDATE products p
    SET manufacturer_code = e.candidate_manufacturer_code
    FROM p2c_expected e
    WHERE p.id = e.product_id
      AND p.manufacturer_code IS NULL
      AND p.sku = e.expected_sku
      AND p.brand_id = e.expected_brand_id
      AND p.deleted_at IS NULL
    RETURNING p.id AS product_id, p.manufacturer_code AS new_value
  )
  SELECT * FROM u;

  SELECT COUNT(*) INTO updated_n FROM p2c_updated;
  IF updated_n <> expected_n THEN
    RAISE EXCEPTION 'updated rows = % (expected %)', updated_n, expected_n;
  END IF;

  SELECT COUNT(*) INTO exact_n
  FROM products p
  JOIN p2c_expected e ON e.product_id = p.id
  WHERE p.manufacturer_code IS NOT DISTINCT FROM e.candidate_manufacturer_code;
  IF exact_n <> expected_n THEN
    RAISE EXCEPTION 'exact frozen matches = % (expected %)', exact_n, expected_n;
  END IF;

  INSERT INTO product_change_logs (
    product_id, field_name, old_value, new_value, reason, actor_user_id
  )
  SELECT
    u.product_id,
    'manufacturer_code',
    NULL,
    u.new_value,
    {sql_literal(reason)},
    NULL
  FROM p2c_updated u;

  SELECT COUNT(*) INTO log_n
  FROM product_change_logs pcl
  JOIN p2c_updated u ON u.product_id = pcl.product_id
  WHERE pcl.field_name = 'manufacturer_code'
    AND pcl.old_value IS NULL
    AND pcl.new_value IS NOT DISTINCT FROM u.new_value
    AND pcl.reason = {sql_literal(reason)}
    AND pcl.actor_user_id IS NULL;
  IF log_n <> expected_n THEN
    RAISE EXCEPTION 'change logs for updated set = % (expected %)', log_n, expected_n;
  END IF;

  SELECT COUNT(*) INTO protected_n
  FROM products p
  JOIN p2c_locked b ON b.id = p.id
  WHERE p.name IS DISTINCT FROM b.name
     OR p.sku IS DISTINCT FROM b.sku
     OR p.slug IS DISTINCT FROM b.slug
     OR p.brand_id IS DISTINCT FROM b.brand_id
     OR p.category_id IS DISTINCT FROM b.category_id
     OR p.product_type_id IS DISTINCT FROM b.product_type_id
     OR p.base_price IS DISTINCT FROM b.base_price
     OR p.original_price IS DISTINCT FROM b.original_price
     OR p.is_active IS DISTINCT FROM b.is_active
     OR p.is_available IS DISTINCT FROM b.is_available
     OR p.deleted_at IS DISTINCT FROM b.deleted_at;
  IF protected_n <> 0 THEN
    RAISE EXCEPTION 'protected-field drift = %', protected_n;
  END IF;

  SELECT COUNT(*) INTO collision_n FROM (
    SELECT brand_id, manufacturer_code
    FROM products
    WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL
    GROUP BY brand_id, manufacturer_code
    HAVING COUNT(*) > 1
  ) s;
  IF collision_n <> 0 THEN
    RAISE EXCEPTION 'new unresolved brand+manufacturer_code collision groups = %', collision_n;
  END IF;

  SELECT COUNT(*) INTO nontarget_n
  FROM products
  WHERE deleted_at IS NULL
    AND manufacturer_code IS NOT NULL
    AND id NOT IN (SELECT product_id FROM p2c_expected);
  IF nontarget_n <> 0 THEN
    RAISE EXCEPTION 'non-target manufacturer_code populated = %', nontarget_n;
  END IF;

  SELECT COUNT(*) INTO global_after
  FROM products WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL;
  IF global_after <> expected_n THEN
    RAISE EXCEPTION 'global manufacturer_code populated = % (expected %)', global_after, expected_n;
  END IF;

  INSERT INTO p2c_metrics(k, v) VALUES
    ('locked_rows', locked_n),
    ('updated_rows', updated_n),
    ('exact_matches', exact_n),
    ('change_logs', log_n),
    ('protected_drift', protected_n),
    ('collision_groups', collision_n),
    ('nontarget_changes', nontarget_n);
END $$;

SELECT 'METRIC:' || k || ':' || v::text FROM p2c_metrics ORDER BY k;
SELECT 'TXID:' || txid_current()::text;
COMMIT;
SELECT 'METRIC:committed:1';
"""


def parse_real_apply_metrics(stdout: str) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for line in stdout.splitlines():
        m = re.search(r"METRIC:([a-z_]+):(\d+)", line.strip())
        if m:
            metrics[m.group(1)] = int(m.group(2))
    required = (
        "locked_rows",
        "updated_rows",
        "exact_matches",
        "change_logs",
        "protected_drift",
        "collision_groups",
        "nontarget_changes",
        "committed",
    )
    missing = [k for k in required if k not in metrics]
    if missing:
        raise RuntimeError(f"missing real-apply metrics {missing}; tail={stdout[-1200:]}")
    return {k: metrics[k] for k in required}


def assert_confirmation_sha(provided: str | None, expected: str = OWNER_FROZEN_SHA256) -> None:
    if not provided:
        raise ValueError("missing --confirm-cohort-sha; refusing mutation")
    if provided != expected:
        raise ValueError(
            f"confirm-cohort-sha mismatch: got {provided}, expected {expected}"
        )


def second_apply_blocked_reason(
    *,
    target_existing_code_count: int,
    expected_rows: int = REAL_APPLY_EXPECTED_ROWS,
) -> str | None:
    """Return block reason if a second real APPLY must fail closed before writes."""
    if target_existing_code_count > 0:
        return (
            f"target manufacturer_code already populated = {target_existing_code_count} "
            f"(expected 0 for first apply; second APPLY blocked)"
        )
    return None
