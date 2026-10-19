"""INSIZE +10% owner-authorized base_price APPLY (2026-10-19). Pure helpers — no I/O."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.domain.phase2c_apply import sql_literal

EXPECTED_BRAND_ID = 3
EXPECTED_BRAND_NAME = "INSIZE | اینسایز"
CHANGE_REASON = "INSIZE +10% owner-authorized price update 2026-10-19"
MULTIPLIER = Decimal("1.10")
ADVISORY_LOCK_KEY = "karzar:insize:price110:20261019"
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


def build_rollback_sql(rows: list[dict[str, Any]]) -> str:
    """Exact-value rollback — never infer by dividing by 1.10."""
    lines = [
        "-- INSIZE +10% rollback — restore exact pre-apply base_price values",
        f"-- change_reason: {CHANGE_REASON}",
        "BEGIN;",
    ]
    for row in sorted(rows, key=lambda r: int(r["product_id"])):
        pid = int(row["product_id"])
        old = sql_literal(row["old_base_price"])
        lines.append(
            f"UPDATE products SET base_price = {old}::numeric WHERE id = {pid} "
            f"AND brand_id = {EXPECTED_BRAND_ID} AND deleted_at IS NULL;"
        )
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


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
