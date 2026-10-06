"""Phase 2F — owner-authorized real Product.name apply (frozen Phase 2D/2E cohort)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Literal

from app.domain.product_naming_phase2e import (
    HOLD_CANARY_MANUFACTURER_CODE,
    LOGROW_RE,
    METRIC_RE,
    PHASE2D_CANDIDATE_SHA256,
    PHASE2D_EXPECTED_READY_ROWS,
    normalize_name_for_collision,
    sha256_bytes,
    sha256_file,
    sql_int,
    sql_literal,
)

PHASE2E_PRESTATE_SHA256 = "88ba82d203a0e51224cbbea81eb277cd15cb5f867470fdd7c367bad4098f43e5"
PHASE2E_EXPECTED_PRESTATE = "audit/product-naming-phase2e-rehearsal/PHASE2E_EXPECTED_PRESTATE.csv"
PHASE2E_MANIFEST = "audit/product-naming-phase2e-rehearsal/PHASE2E_REHEARSAL_MANIFEST.json"

REAL_APPLY_ADVISORY_LOCK_KEY = "karzar:phase2f:product_name:apply"
REAL_APPLY_EXPECTED_ROWS = PHASE2D_EXPECTED_READY_ROWS

REAL_APPLY_LOGIC_FILES = (
    "app/domain/product_naming_phase2f.py",
    "scripts/ops/product_naming_phase2f_apply_once.py",
)

FORBIDDEN_APPLY_FLAGS = frozenset(
    {
        "--force",
        "--skip-preflight",
        "--ignore-drift",
        "--partial",
        "--reapply",
        "--yes",
        "--skip-backup",
        "--skip-collision-check",
        "--skip-audit-log",
    }
)

REQUIRED_APPLY_METRICS = (
    "in_tx_identity_drift",
    "in_tx_name_drift",
    "in_tx_sku_drift",
    "in_tx_manufacturer_code_drift",
    "in_tx_brand_drift",
    "in_tx_product_type_drift",
    "in_tx_deleted_drift",
    "updates_exact",
    "old_names_remaining",
    "target_protected_drift",
    "apply_logs_exact",
    "exact_name_collisions",
    "normalized_name_collisions",
    "catalog_exact_collisions",
    "catalog_normalized_collisions",
    "non_target_name_changes",
    "non_target_protected_changes",
)


def apply_change_log_reason(cohort_sha256: str = PHASE2D_CANDIDATE_SHA256) -> str:
    reason = (
        "Phase 2F owner-authorized Product.name apply; "
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
            raise FileNotFoundError(rel)
        out[rel] = sha256_file(path)
    return out


def assert_confirmation_sha(
    provided: str | None,
    expected: str,
    *,
    flag_name: str = "confirm-sha",
) -> None:
    if not provided:
        raise ValueError(f"missing --{flag_name}; refusing mutation")
    if provided != expected:
        raise ValueError(f"{flag_name} mismatch: got {provided}, expected {expected}")


def reject_forbidden_apply_flags(argv: list[str]) -> None:
    import sys

    for a in argv:
        if a in FORBIDDEN_APPLY_FLAGS or any(a.startswith(f"{f}=") for f in FORBIDDEN_APPLY_FLAGS):
            print(f"ERROR: forbidden flag {a}", file=sys.stderr)
            raise SystemExit(2)


def load_expected_prestate_csv(path: Path) -> list[dict[str, str]]:
    from app.domain.product_naming_phase2e import prestate_csv_bytes

    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    digest = sha256_bytes(prestate_csv_bytes(rows))
    if digest != PHASE2E_PRESTATE_SHA256:
        raise ValueError(f"prestate SHA256 mismatch: got {digest}")
    if len(rows) != REAL_APPLY_EXPECTED_ROWS:
        raise ValueError(f"prestate rows {len(rows)} != {REAL_APPLY_EXPECTED_ROWS}")
    for row in rows:
        if (row.get("manufacturer_code") or "").strip() == HOLD_CANARY_MANUFACTURER_CODE:
            raise ValueError("HOLD canary 2223-153 in prestate")
        if not (row.get("proposed_name_norm") or "").strip():
            row["proposed_name_norm"] = normalize_name_for_collision(row.get("proposed_name", ""))
    return rows


def validate_phase2e_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("status") != "READY_FOR_OWNER_APPLY_AUTHORIZATION":
        raise ValueError(f"phase2e status {manifest.get('status')}")
    metrics = manifest.get("metrics") or {}
    required_zeros = (
        "in_tx_identity_drift",
        "exact_name_collisions",
        "normalized_name_collisions",
        "catalog_exact_collisions",
        "catalog_normalized_collisions",
        "non_target_name_changes",
        "non_target_protected_changes",
    )
    for key in required_zeros:
        if metrics.get(key, -1) != 0:
            raise ValueError(f"phase2e metric {key}={metrics.get(key)}")
    if metrics.get("updates_exact") != REAL_APPLY_EXPECTED_ROWS:
        raise ValueError("phase2e updates_exact mismatch")
    if manifest.get("persistent_product_name_delta") != 0:
        raise ValueError("phase2e persistent_product_name_delta nonzero")
    if manifest.get("persistent_rehearsal_log_delta") != 0:
        raise ValueError("phase2e persistent_rehearsal_log_delta nonzero")
    log_audit = manifest.get("log_audit") or {}
    if log_audit.get("actual_log_row_mismatches", -1) != 0:
        raise ValueError("phase2e log audit mismatches")
    return manifest


def build_recovery_target_rows(prestate: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [
        {
            "product_id": r["product_id"],
            "sku": r["sku"],
            "manufacturer_code": r["manufacturer_code"],
            "brand_id": r["brand_id"],
            "product_type_id": r["product_type_id"],
            "pre_apply_name": r["expected_old_name"],
            "applied_name": r["proposed_name"],
        }
        for r in prestate
    ]
    rows.sort(key=lambda r: int(r["product_id"]))
    return rows


def second_apply_blocked_reason(prestate: list[dict[str, str]], live: dict[str, dict[str, str]]) -> str:
    already = 0
    for row in prestate:
        lv = live.get(row["product_id"], {})
        if (lv.get("name") or "").strip() == row["proposed_name"]:
            already += 1
    if already == len(prestate):
        return "ALREADY_APPLIED_BLOCKED"
    return ""


def _frozen_identity_values(prestate: list[dict[str, str]]) -> str:
    rows = []
    for r in prestate:
        pid = int(r["product_id"])
        rows.append(
            f"({pid},{sql_literal(r['expected_old_name'])},{sql_literal(r['sku'])},"
            f"{sql_literal(r['manufacturer_code'])},{sql_int(r['brand_id'])},"
            f"{sql_int(r['product_type_id'])},{sql_literal(r['proposed_name'])},"
            f"{sql_literal(r['proposed_name_norm'])})"
        )
    return ",\n  ".join(rows)


def _catalog_norm_insert_sql(catalog_norm_rows: list[tuple[int, str]]) -> str:
    if not catalog_norm_rows:
        return "CREATE TEMP TABLE p2f_catalog_norm (product_id int PRIMARY KEY, norm_name text);\n"
    chunks: list[str] = []
    batch = 400
    for i in range(0, len(catalog_norm_rows), batch):
        part = catalog_norm_rows[i : i + batch]
        values = ",\n  ".join(f"({pid},{sql_literal(norm)})" for pid, norm in part)
        chunks.append(f"INSERT INTO p2f_catalog_norm (product_id, norm_name) VALUES\n  {values};")
    return (
        "CREATE TEMP TABLE p2f_catalog_norm (product_id int PRIMARY KEY, norm_name text);\n"
        + "\n".join(chunks)
        + "\n"
    )


def _coupled_update_sql(row: dict[str, str], reason: str) -> str:
    pid = int(row["product_id"])
    return f"""
WITH gate AS (SELECT n FROM p2f_identity_gate),
upd AS (
  UPDATE products p
  SET name = f.new_name
  FROM p2f_frozen_identity f, gate
  WHERE gate.n = 0
    AND p.id = f.id
    AND p.id = {pid}
    AND p.name = f.old_name
    AND p.sku = f.sku
    AND COALESCE(p.manufacturer_code, '') = f.manufacturer_code
    AND p.brand_id IS NOT DISTINCT FROM f.brand_id
    AND p.product_type_id IS NOT DISTINCT FROM f.product_type_id
    AND p.deleted_at IS NULL
  RETURNING p.id, f.old_name, f.new_name
)
INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
SELECT id, 'name', old_name, new_name, {sql_literal(reason)}, NULL FROM upd;
"""


def build_real_apply_sql(
    prestate: list[dict[str, str]],
    *,
    catalog_norm_rows: list[tuple[int, str]],
    cohort_sha256: str = PHASE2D_CANDIDATE_SHA256,
) -> str:
    if len(prestate) != REAL_APPLY_EXPECTED_ROWS:
        raise ValueError(f"prestate rows {len(prestate)} != {REAL_APPLY_EXPECTED_ROWS}")
    ids = sorted(int(r["product_id"]) for r in prestate)
    id_csv = ",".join(str(i) for i in ids)
    reason = apply_change_log_reason(cohort_sha256)
    frozen_values = _frozen_identity_values(prestate)
    catalog_sql = _catalog_norm_insert_sql(catalog_norm_rows)
    updates = "\n".join(_coupled_update_sql(row, reason) for row in prestate)
    expected_n = REAL_APPLY_EXPECTED_ROWS

    return f"""
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '180s';
SELECT pg_advisory_xact_lock(hashtext({sql_literal(REAL_APPLY_ADVISORY_LOCK_KEY)}));
CREATE TEMP TABLE p2f_frozen_identity (
  id int PRIMARY KEY,
  old_name text NOT NULL,
  sku text NOT NULL,
  manufacturer_code text NOT NULL,
  brand_id int,
  product_type_id int,
  new_name text NOT NULL,
  new_name_norm text NOT NULL
);
INSERT INTO p2f_frozen_identity (
  id, old_name, sku, manufacturer_code, brand_id, product_type_id, new_name, new_name_norm
) VALUES
  {frozen_values};
{catalog_sql}
CREATE TEMP TABLE p2f_before AS
  SELECT id, name, sku, slug, manufacturer_code, brand_id, category_id, product_type_id,
         meta_title, meta_description, base_price, original_price, is_available, is_active,
         deleted_at, stock_quantity, tax_percent
  FROM products WHERE id IN ({id_csv});
CREATE TEMP TABLE p2f_nontarget_before AS
  SELECT id, name, sku, slug, manufacturer_code, brand_id, category_id, product_type_id,
         meta_title, meta_description, base_price, original_price, is_available, is_active,
         deleted_at, stock_quantity, tax_percent
  FROM products WHERE deleted_at IS NULL AND id NOT IN ({id_csv});
SELECT id FROM products WHERE id IN ({id_csv}) ORDER BY id FOR UPDATE;
SELECT 'METRIC:in_tx_name_drift:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id WHERE p.name IS DISTINCT FROM f.old_name;
SELECT 'METRIC:in_tx_sku_drift:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id WHERE p.sku IS DISTINCT FROM f.sku;
SELECT 'METRIC:in_tx_manufacturer_code_drift:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id
  WHERE COALESCE(p.manufacturer_code, '') IS DISTINCT FROM f.manufacturer_code;
SELECT 'METRIC:in_tx_brand_drift:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id WHERE p.brand_id IS DISTINCT FROM f.brand_id;
SELECT 'METRIC:in_tx_product_type_drift:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id WHERE p.product_type_id IS DISTINCT FROM f.product_type_id;
SELECT 'METRIC:in_tx_deleted_drift:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id WHERE p.deleted_at IS NOT NULL;
SELECT 'METRIC:in_tx_identity_drift:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id
  WHERE p.name IS DISTINCT FROM f.old_name
     OR p.sku IS DISTINCT FROM f.sku
     OR COALESCE(p.manufacturer_code, '') IS DISTINCT FROM f.manufacturer_code
     OR p.brand_id IS DISTINCT FROM f.brand_id
     OR p.product_type_id IS DISTINCT FROM f.product_type_id
     OR p.deleted_at IS NOT NULL;
CREATE TEMP TABLE p2f_identity_gate AS
  SELECT COUNT(*)::int AS n FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id
  WHERE p.name IS DISTINCT FROM f.old_name
     OR p.sku IS DISTINCT FROM f.sku
     OR COALESCE(p.manufacturer_code, '') IS DISTINCT FROM f.manufacturer_code
     OR p.brand_id IS DISTINCT FROM f.brand_id
     OR p.product_type_id IS DISTINCT FROM f.product_type_id
     OR p.deleted_at IS NOT NULL;
DO $$
BEGIN
  IF (SELECT n FROM p2f_identity_gate) > 0 THEN
    RAISE EXCEPTION 'in_tx_identity_drift nonzero';
  END IF;
END $$;
{updates}
SELECT 'METRIC:updates_exact:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id
  WHERE p.name IS NOT DISTINCT FROM f.new_name;
SELECT 'METRIC:old_names_remaining:' || COUNT(*)::text FROM products p
  JOIN p2f_frozen_identity f ON p.id = f.id
  WHERE p.name IS NOT DISTINCT FROM f.old_name;
SELECT 'METRIC:target_protected_drift:' || COUNT(*)::text FROM products p
  JOIN p2f_before b ON p.id = b.id
  WHERE p.sku IS DISTINCT FROM b.sku
     OR p.slug IS DISTINCT FROM b.slug
     OR p.manufacturer_code IS DISTINCT FROM b.manufacturer_code
     OR p.brand_id IS DISTINCT FROM b.brand_id
     OR p.category_id IS DISTINCT FROM b.category_id
     OR p.product_type_id IS DISTINCT FROM b.product_type_id
     OR p.meta_title IS DISTINCT FROM b.meta_title
     OR p.meta_description IS DISTINCT FROM b.meta_description
     OR p.base_price IS DISTINCT FROM b.base_price
     OR p.original_price IS DISTINCT FROM b.original_price
     OR p.is_available IS DISTINCT FROM b.is_available
     OR p.is_active IS DISTINCT FROM b.is_active
     OR p.deleted_at IS DISTINCT FROM b.deleted_at
     OR p.stock_quantity IS DISTINCT FROM b.stock_quantity
     OR p.tax_percent IS DISTINCT FROM b.tax_percent;
SELECT 'METRIC:apply_logs_exact:' || COUNT(*)::text FROM product_change_logs
  WHERE reason = {sql_literal(reason)} AND field_name = 'name';
SELECT 'METRIC:exact_name_collisions:' || COUNT(*)::text FROM (
  SELECT f.new_name FROM p2f_frozen_identity f
  GROUP BY f.new_name HAVING COUNT(*) > 1
) s;
SELECT 'METRIC:normalized_name_collisions:' || COUNT(*)::text FROM (
  SELECT f.new_name_norm FROM p2f_frozen_identity f
  GROUP BY f.new_name_norm HAVING COUNT(*) > 1
) s;
SELECT 'METRIC:catalog_exact_collisions:' || COUNT(*)::text FROM p2f_frozen_identity f
  WHERE EXISTS (
    SELECT 1 FROM products p
    WHERE p.deleted_at IS NULL AND p.id <> f.id AND p.name = f.new_name
  );
SELECT 'METRIC:catalog_normalized_collisions:' || COUNT(*)::text FROM p2f_frozen_identity f
  WHERE EXISTS (
    SELECT 1 FROM p2f_catalog_norm cn
    JOIN products p ON p.id = cn.product_id
    WHERE p.deleted_at IS NULL AND cn.product_id <> f.id AND cn.norm_name = f.new_name_norm
  );
SELECT 'METRIC:non_target_name_changes:' || COUNT(*)::text FROM products p
  JOIN p2f_nontarget_before b ON p.id = b.id
  WHERE p.name IS DISTINCT FROM b.name;
SELECT 'METRIC:non_target_protected_changes:' || COUNT(*)::text FROM products p
  JOIN p2f_nontarget_before b ON p.id = b.id
  WHERE p.sku IS DISTINCT FROM b.sku
     OR p.slug IS DISTINCT FROM b.slug
     OR p.manufacturer_code IS DISTINCT FROM b.manufacturer_code
     OR p.brand_id IS DISTINCT FROM b.brand_id
     OR p.category_id IS DISTINCT FROM b.category_id
     OR p.product_type_id IS DISTINCT FROM b.product_type_id
     OR p.meta_title IS DISTINCT FROM b.meta_title
     OR p.meta_description IS DISTINCT FROM b.meta_description
     OR p.base_price IS DISTINCT FROM b.base_price
     OR p.original_price IS DISTINCT FROM b.original_price
     OR p.is_available IS DISTINCT FROM b.is_available
     OR p.is_active IS DISTINCT FROM b.is_active
     OR p.deleted_at IS DISTINCT FROM b.deleted_at
     OR p.stock_quantity IS DISTINCT FROM b.stock_quantity
     OR p.tax_percent IS DISTINCT FROM b.tax_percent;
DO $$
DECLARE
  expected_n int := {expected_n};
  u int;
  o int;
  pd int;
  lg int;
  nt int;
  ntp int;
BEGIN
  SELECT COUNT(*) INTO u FROM products p JOIN p2f_frozen_identity f ON p.id=f.id
    WHERE p.name IS NOT DISTINCT FROM f.new_name;
  SELECT COUNT(*) INTO o FROM products p JOIN p2f_frozen_identity f ON p.id=f.id
    WHERE p.name IS NOT DISTINCT FROM f.old_name;
  SELECT COUNT(*) INTO pd FROM products p JOIN p2f_before b ON p.id=b.id
    WHERE p.sku IS DISTINCT FROM b.sku OR p.slug IS DISTINCT FROM b.slug
       OR p.manufacturer_code IS DISTINCT FROM b.manufacturer_code
       OR p.brand_id IS DISTINCT FROM b.brand_id OR p.category_id IS DISTINCT FROM b.category_id
       OR p.product_type_id IS DISTINCT FROM b.product_type_id
       OR p.meta_title IS DISTINCT FROM b.meta_title
       OR p.meta_description IS DISTINCT FROM b.meta_description
       OR p.base_price IS DISTINCT FROM b.base_price
       OR p.original_price IS DISTINCT FROM b.original_price
       OR p.is_available IS DISTINCT FROM b.is_available
       OR p.is_active IS DISTINCT FROM b.is_active
       OR p.deleted_at IS DISTINCT FROM b.deleted_at
       OR p.stock_quantity IS DISTINCT FROM b.stock_quantity
       OR p.tax_percent IS DISTINCT FROM b.tax_percent;
  SELECT COUNT(*) INTO lg FROM product_change_logs
    WHERE reason = {sql_literal(reason)} AND field_name = 'name';
  SELECT COUNT(*) INTO nt FROM products p JOIN p2f_nontarget_before b ON p.id=b.id
    WHERE p.name IS DISTINCT FROM b.name;
  SELECT COUNT(*) INTO ntp FROM products p JOIN p2f_nontarget_before b ON p.id=b.id
    WHERE p.sku IS DISTINCT FROM b.sku OR p.slug IS DISTINCT FROM b.slug
       OR p.manufacturer_code IS DISTINCT FROM b.manufacturer_code
       OR p.brand_id IS DISTINCT FROM b.brand_id OR p.category_id IS DISTINCT FROM b.category_id
       OR p.product_type_id IS DISTINCT FROM b.product_type_id
       OR p.meta_title IS DISTINCT FROM b.meta_title
       OR p.meta_description IS DISTINCT FROM b.meta_description
       OR p.base_price IS DISTINCT FROM b.base_price
       OR p.original_price IS DISTINCT FROM b.original_price
       OR p.is_available IS DISTINCT FROM b.is_available
       OR p.is_active IS DISTINCT FROM b.is_active
       OR p.deleted_at IS DISTINCT FROM b.deleted_at
       OR p.stock_quantity IS DISTINCT FROM b.stock_quantity
       OR p.tax_percent IS DISTINCT FROM b.tax_percent;
  IF u <> expected_n THEN RAISE EXCEPTION 'updates_exact %', u; END IF;
  IF o <> 0 THEN RAISE EXCEPTION 'old_names_remaining %', o; END IF;
  IF pd <> 0 THEN RAISE EXCEPTION 'target_protected_drift %', pd; END IF;
  IF lg <> expected_n THEN RAISE EXCEPTION 'apply_logs_exact %', lg; END IF;
  IF nt <> 0 THEN RAISE EXCEPTION 'non_target_name_changes %', nt; END IF;
  IF ntp <> 0 THEN RAISE EXCEPTION 'non_target_protected_changes %', ntp; END IF;
END $$;
SELECT 'METRIC:txid:' || txid_current()::text;
SELECT 'LOGROW:' || row_to_json(t)::text FROM (
  SELECT id, product_id, field_name, old_value, new_value, reason, actor_user_id
  FROM product_change_logs
  WHERE reason = {sql_literal(reason)} AND field_name = 'name'
  ORDER BY product_id, id
) t;
COMMIT;
"""


def parse_apply_stdout(stdout: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    metrics: dict[str, int] = {}
    log_rows: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        m = METRIC_RE.match(line.strip())
        if m:
            key, val = m.group(1), m.group(2)
            if key == "txid":
                metrics["txid"] = int(val)
            else:
                metrics[key] = int(val)
            continue
        lm = LOGROW_RE.match(line.strip())
        if lm:
            log_rows.append(json.loads(lm.group(1)))
    missing = [k for k in REQUIRED_APPLY_METRICS if k not in metrics]
    if missing:
        raise RuntimeError(f"missing apply metrics {missing}: tail={stdout[-2500:]}")
    return metrics, log_rows


def apply_success_metrics(metrics: dict[str, int], expected_rows: int) -> list[str]:
    errors: list[str] = []
    checks = {
        "in_tx_identity_drift": 0,
        "updates_exact": expected_rows,
        "old_names_remaining": 0,
        "target_protected_drift": 0,
        "apply_logs_exact": expected_rows,
        "exact_name_collisions": 0,
        "normalized_name_collisions": 0,
        "catalog_exact_collisions": 0,
        "catalog_normalized_collisions": 0,
        "non_target_name_changes": 0,
        "non_target_protected_changes": 0,
    }
    for key, expected in checks.items():
        if metrics.get(key, -1) != expected:
            errors.append(key)
    return errors


def audit_apply_logs(
    prestate: list[dict[str, str]],
    log_rows: list[dict[str, Any]],
    *,
    cohort_sha256: str = PHASE2D_CANDIDATE_SHA256,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    reason = apply_change_log_reason(cohort_sha256)
    expected_by_pid = {
        int(r["product_id"]): {
            "expected_old_name": r["expected_old_name"],
            "proposed_name": r["proposed_name"],
        }
        for r in prestate
    }
    cohort_ids = set(expected_by_pid)
    actual_for_cohort = [r for r in log_rows if int(r["product_id"]) in cohort_ids]
    non_target_logs = len(log_rows) - len(actual_for_cohort)
    by_pid: dict[int, list[dict[str, Any]]] = {}
    for row in actual_for_cohort:
        by_pid.setdefault(int(row["product_id"]), []).append(row)
    wrong_old = wrong_new = wrong_reason = wrong_field = duplicates = 0
    for pid, rows in by_pid.items():
        if len(rows) > 1:
            duplicates += len(rows) - 1
        row = rows[0]
        exp = expected_by_pid[pid]
        if row.get("field_name") != "name":
            wrong_field += 1
        if (row.get("old_value") or "") != exp["expected_old_name"]:
            wrong_old += 1
        if (row.get("new_value") or "") != exp["proposed_name"]:
            wrong_new += 1
        if (row.get("reason") or "") != reason:
            wrong_reason += 1
    missing = len(cohort_ids - set(by_pid))
    extra = max(0, len(actual_for_cohort) - len(by_pid))
    mismatches = (
        missing + extra + duplicates + wrong_field + wrong_old + wrong_new + wrong_reason + non_target_logs
    )
    summary = {
        "actual_rows": len(log_rows),
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "wrong_field_name": wrong_field,
        "wrong_old_value": wrong_old,
        "wrong_new_value": wrong_new,
        "wrong_reason": wrong_reason,
        "non_target_apply_logs": non_target_logs,
        "actual_log_row_mismatches": mismatches,
    }
    csv_rows: list[dict[str, Any]] = []
    for row in sorted(log_rows, key=lambda r: (int(r["product_id"]), int(r.get("id") or 0))):
        pid = int(row["product_id"])
        exp = expected_by_pid.get(pid)
        csv_rows.append(
            {
                "id": row.get("id"),
                "product_id": pid,
                "field_name": row.get("field_name"),
                "old_value": row.get("old_value"),
                "new_value": row.get("new_value"),
                "reason": row.get("reason"),
                "actor_user_id": row.get("actor_user_id"),
                "expected_old_value": exp["expected_old_name"] if exp else "",
                "expected_new_value": exp["proposed_name"] if exp else "",
                "match": (
                    "yes"
                    if exp
                    and row.get("field_name") == "name"
                    and (row.get("old_value") or "") == exp["expected_old_name"]
                    and (row.get("new_value") or "") == exp["proposed_name"]
                    and (row.get("reason") or "") == reason
                    else "no"
                ),
            }
        )
    return summary, csv_rows


ApplyStatus = Literal[
    "APPLIED_VERIFIED",
    "BLOCKED",
    "APPLY_FAILED_ROLLED_BACK",
    "COMMIT_STATUS_UNKNOWN",
    "BLOCKED_CRITICAL",
]
