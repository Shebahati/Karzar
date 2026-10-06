"""Phase 2E — transactional Product.name rename rehearsal (frozen Phase 2D cohort)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from app.domain.product_naming import normalize_persian_text

PHASE2D_CANDIDATE_SHA256 = "25d586e371431cc371b6ce6432abba6c2da5b1f15102cac9ed187f78ef0052ff"
PHASE2D_EXPECTED_READY_ROWS = 47
HOLD_CANARY_MANUFACTURER_CODE = "2223-153"

REHEARSAL_REASON = "product_naming_phase2e_rehearsal"
ADVISORY_LOCK_KEY = "karzar:phase2e:product_name:rehearsal"

CHANGE_LOG_CONTRACT_REFERENCE = "app.crud.audit.record_product_change"
CHANGE_LOG_EQUIVALENT_FIELDS = (
    "product_id",
    "field_name",
    "old_value",
    "new_value",
    "reason",
    "actor_user_id",
)

FORBIDDEN_APPLY_FLAGS = frozenset(
    {
        "--apply",
        "--commit",
        "--real",
        "--execute-and-commit",
        "--force-commit",
        "--yes",
        "--force",
    }
)

COMMIT_RE = re.compile(r"(^|[^A-Z_])COMMIT(\s|;|$)", re.I)
METRIC_RE = re.compile(r"^METRIC:([a-z_]+):(\d+)$")
LOGROW_RE = re.compile(r"^LOGROW:(.+)$")

REHEARSAL_LOGIC_FILES = (
    "app/domain/product_naming_phase2e.py",
    "scripts/ops/product_naming_phase2e_rehearsal.py",
)

PROTECTED_PRODUCT_COLUMNS = (
    "id",
    "sku",
    "slug",
    "manufacturer_code",
    "brand_id",
    "category_id",
    "product_type_id",
    "meta_title",
    "meta_description",
    "base_price",
    "original_price",
    "is_available",
    "is_active",
    "deleted_at",
    "stock_quantity",
    "tax_percent",
)

REQUIRED_REHEARSAL_METRICS = (
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
    "rehearsal_logs_exact",
    "actual_log_row_mismatches",
    "exact_name_collisions",
    "normalized_name_collisions",
    "catalog_exact_collisions",
    "catalog_normalized_collisions",
    "non_target_name_changes",
    "non_target_protected_changes",
)

FailureInjection = Literal[
    "after_first_update",
    "mid_cohort",
    "after_all_updates",
    "during_logs",
    "after_all_logs",
    "validation_failure",
    "identity_drift_simulation",
]


def normalize_name_for_collision(name: str) -> str:
    """Phase 2D comparison normalization (Persian display text)."""
    return normalize_persian_text(name)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_real_apply_flags(argv: list[str]) -> None:
    import sys

    for a in argv:
        if a in FORBIDDEN_APPLY_FLAGS or any(
            a.startswith(f"{flag}=") for flag in FORBIDDEN_APPLY_FLAGS
        ):
            print("ERROR: Phase 2E rehearsal only — real apply flags are forbidden.", file=sys.stderr)
            raise SystemExit(2)
    if any(a.startswith("--") and "commit" in a.lower() and a not in ("--preflight-only",) for a in argv):
        for a in argv:
            if "commit" in a.lower() and a not in FORBIDDEN_APPLY_FLAGS:
                print(f"ERROR: forbidden flag {a}", file=sys.stderr)
                raise SystemExit(2)


def sql_literal(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def sql_int(value: str | None) -> str:
    v = (value or "").strip()
    if not v:
        return "NULL"
    return str(int(v))


def rehearsal_logic_file_sha256(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in REHEARSAL_LOGIC_FILES:
        path = repo_root / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        out[rel] = sha256_file(path)
    return out


def load_freeze_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_phase2d_freeze_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "READY_RENAME": PHASE2D_EXPECTED_READY_ROWS,
        "HOLD": 1303,
        "classification_reconciles": True,
        "replay_identical": True,
        "all_READY_have_owner_title_approval": True,
    }
    errors: list[str] = []
    for key, expected in required.items():
        if manifest.get(key) != expected:
            errors.append(f"{key}={manifest.get(key)} expected {expected}")
    collisions = manifest.get("collision_groups") or {}
    if collisions.get("ready_rename_affected", -1) != 0:
        errors.append(f"collision ready_rename_affected={collisions.get('ready_rename_affected')}")
    if manifest.get("SEO_impact_rows", -1) != 0:
        errors.append(f"SEO_impact_rows={manifest.get('SEO_impact_rows')}")
    written = manifest.get("written_candidate_file_sha256")
    if written != PHASE2D_CANDIDATE_SHA256:
        errors.append("written_candidate_file_sha256 mismatch")
    if errors:
        raise ValueError("phase2d_freeze_gate_failed: " + "; ".join(errors))


def load_candidate_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return rows


def validate_candidate_file(
    path: Path,
    *,
    expected_sha256: str = PHASE2D_CANDIDATE_SHA256,
    expected_rows: int = PHASE2D_EXPECTED_READY_ROWS,
) -> tuple[list[dict[str, str]], str]:
    digest = sha256_file(path)
    if digest != expected_sha256:
        raise ValueError(f"candidate SHA256 mismatch: got {digest}")
    rows = load_candidate_rows(path)
    if len(rows) != expected_rows:
        raise ValueError(f"candidate row count {len(rows)} != {expected_rows}")
    pids = [r.get("product_id", "").strip() for r in rows]
    if len(set(pids)) != len(pids):
        raise ValueError("duplicate product_id in candidate file")
    for r in rows:
        if not (r.get("proposed_name") or "").strip():
            raise ValueError(f"missing proposed_name for {r.get('product_id')}")
        if (r.get("manufacturer_code") or "").strip() == HOLD_CANARY_MANUFACTURER_CODE:
            raise ValueError("HOLD canary 2223-153 must not appear in candidate cohort")
    return rows, digest


def load_audit_ready_rows(audit_path: Path) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    with audit_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("terminal_classification") != "READY_RENAME":
                continue
            pid = int(row["product_id"])
            out[pid] = row
    return out


def build_expected_prestate_rows(
    candidates: list[dict[str, str]],
    audit_by_pid: dict[int, dict[str, str]],
) -> list[dict[str, str]]:
    prestate: list[dict[str, str]] = []
    for cand in sorted(candidates, key=lambda r: int(r["product_id"])):
        pid = int(cand["product_id"])
        audit = audit_by_pid.get(pid)
        if audit is None:
            raise ValueError(f"product_id {pid} missing READY_RENAME audit row")
        expected_old = (audit.get("current_name") or "").strip()
        proposed = (cand.get("proposed_name") or "").strip()
        if not expected_old:
            raise ValueError(f"frozen expected_old_name empty for {pid}")
        if proposed == expected_old:
            raise ValueError(f"proposed_name equals frozen old name for {pid}")
        prestate.append(
            {
                "product_id": str(pid),
                "sku": (cand.get("sku") or audit.get("sku") or "").strip(),
                "manufacturer_code": (cand.get("manufacturer_code") or "").strip(),
                "brand_id": (audit.get("brand_id") or "").strip(),
                "brand_name": (audit.get("brand_name") or "").strip(),
                "product_type_id": (audit.get("product_type_id") or "").strip(),
                "product_type_code": (cand.get("product_type_code") or "").strip(),
                "expected_old_name": expected_old,
                "proposed_name": proposed,
                "proposed_name_norm": normalize_name_for_collision(proposed),
                "meta_title_present": (audit.get("meta_title_present") or "").strip(),
                "seo_title_impact": (audit.get("seo_title_impact") or "").strip(),
            }
        )
    if len(prestate) != PHASE2D_EXPECTED_READY_ROWS:
        raise ValueError(f"prestate rows {len(prestate)} != {PHASE2D_EXPECTED_READY_ROWS}")
    return prestate


def prestate_csv_bytes(rows: list[dict[str, str]]) -> bytes:
    import io

    fields = list(rows[0].keys()) if rows else ["product_id"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue().encode("utf-8")


def reconcile_live_row(
    frozen: dict[str, str],
    live: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    pid = frozen["product_id"]
    if live.get("deleted_at"):
        errors.append(f"{pid}: deleted")
    if (live.get("name") or "").strip() != frozen["expected_old_name"]:
        errors.append(f"{pid}: name drift")
    if (live.get("sku") or "").strip() != frozen["sku"]:
        errors.append(f"{pid}: sku drift")
    mc = (live.get("manufacturer_code") or "").strip()
    if mc != frozen["manufacturer_code"]:
        errors.append(f"{pid}: manufacturer_code drift")
    if str(live.get("brand_id") or "") != frozen["brand_id"]:
        errors.append(f"{pid}: brand_id drift")
    if str(live.get("product_type_id") or "") != frozen["product_type_id"]:
        errors.append(f"{pid}: product_type_id drift")
    return errors


def collision_precheck_python(
    prestate: list[dict[str, str]],
    catalog: list[tuple[int, str]],
) -> dict[str, int]:
    """Pre-transaction collision scan using Phase 2D normalization."""
    cohort_ids = {int(r["product_id"]) for r in prestate}
    exact_names = [r["proposed_name"] for r in prestate]
    norm_names = [r["proposed_name_norm"] for r in prestate]
    cohort_exact = len(exact_names) - len(set(exact_names))
    cohort_norm = len(norm_names) - len(set(norm_names))
    catalog_exact = 0
    catalog_norm = 0
    exact_set = set(exact_names)
    norm_set = set(norm_names)
    for pid, name in catalog:
        if pid in cohort_ids:
            continue
        if name in exact_set:
            catalog_exact += 1
        if normalize_name_for_collision(name) in norm_set:
            catalog_norm += 1
    return {
        "cohort_exact_dup": cohort_exact,
        "cohort_normalized_dup": cohort_norm,
        "catalog_exact_hits": catalog_exact,
        "catalog_normalized_hits": catalog_norm,
    }


def target_fingerprint_row(live: dict[str, Any]) -> str:
    parts = []
    for col in PROTECTED_PRODUCT_COLUMNS:
        val = live.get(col)
        parts.append(f"{col}={'' if val is None else val}")
    return "|".join(parts)


def non_target_fingerprint_sql(cohort_ids: list[int]) -> str:
    id_csv = ",".join(str(i) for i in sorted(cohort_ids))
    parts = [
        "p.id::text",
        "COALESCE(p.name,'')",
        "COALESCE(p.sku,'')",
        "COALESCE(p.slug,'')",
        "COALESCE(p.manufacturer_code,'')",
        "COALESCE(p.brand_id::text,'')",
        "COALESCE(p.category_id::text,'')",
        "COALESCE(p.product_type_id::text,'')",
        "COALESCE(p.meta_title,'')",
        "COALESCE(p.meta_description,'')",
        "COALESCE(p.base_price::text,'')",
        "COALESCE(p.original_price::text,'')",
        "COALESCE(p.is_available::text,'')",
        "COALESCE(p.is_active::text,'')",
        "COALESCE(p.deleted_at::text,'')",
        "COALESCE(p.stock_quantity::text,'')",
        "COALESCE(p.tax_percent::text,'')",
    ]
    inner = " || '|' || ".join(parts)
    return (
        f"SELECT md5(COALESCE(string_agg({inner}, E'\\n' ORDER BY p.id), '')) "
        f"FROM products p WHERE p.deleted_at IS NULL AND p.id NOT IN ({id_csv});"
    )


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
        return (
            "CREATE TEMP TABLE p2e_catalog_norm (product_id int PRIMARY KEY, norm_name text);\n"
        )
    chunks: list[str] = []
    batch = 400
    for i in range(0, len(catalog_norm_rows), batch):
        part = catalog_norm_rows[i : i + batch]
        values = ",\n  ".join(f"({pid},{sql_literal(norm)})" for pid, norm in part)
        chunks.append(f"INSERT INTO p2e_catalog_norm (product_id, norm_name) VALUES\n  {values};")
    return (
        "CREATE TEMP TABLE p2e_catalog_norm (product_id int PRIMARY KEY, norm_name text);\n"
        + "\n".join(chunks)
        + "\n"
    )


def _coupled_update_sql(row: dict[str, str], reason: str) -> str:
    pid = int(row["product_id"])
    return f"""
WITH gate AS (SELECT n FROM p2e_identity_gate),
upd AS (
  UPDATE products p
  SET name = f.new_name
  FROM p2e_frozen_identity f, gate
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


def build_rehearsal_sql(
    prestate: list[dict[str, str]],
    *,
    catalog_norm_rows: list[tuple[int, str]],
    failure_injection: FailureInjection | None = None,
) -> str:
    """Single SERIALIZABLE transaction; always ends with ROLLBACK."""
    ids = sorted(int(r["product_id"]) for r in prestate)
    id_csv = ",".join(str(i) for i in ids)
    reason = REHEARSAL_REASON
    frozen_values = _frozen_identity_values(prestate)
    catalog_sql = _catalog_norm_insert_sql(catalog_norm_rows)

    updates: list[str] = []
    mid = len(prestate) // 2
    for i, row in enumerate(prestate):
        updates.append(_coupled_update_sql(row, reason))
        if failure_injection == "after_first_update" and i == 0:
            updates.append("SELECT 1/0;")
        if failure_injection == "mid_cohort" and i == mid:
            updates.append("SELECT 1/0;")
        if failure_injection == "after_all_updates" and i == len(prestate) - 1:
            updates.append("SELECT 1/0;")
        if failure_injection == "during_logs" and i == 0:
            updates.append(
                "INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason) "
                "VALUES (-1, 'name', 'x', 'y', 'inject');"
            )
    body = "\n".join(updates)

    identity_drift_block = """
SELECT 'METRIC:in_tx_name_drift:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id WHERE p.name IS DISTINCT FROM f.old_name;
SELECT 'METRIC:in_tx_sku_drift:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id WHERE p.sku IS DISTINCT FROM f.sku;
SELECT 'METRIC:in_tx_manufacturer_code_drift:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id
  WHERE COALESCE(p.manufacturer_code, '') IS DISTINCT FROM f.manufacturer_code;
SELECT 'METRIC:in_tx_brand_drift:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id WHERE p.brand_id IS DISTINCT FROM f.brand_id;
SELECT 'METRIC:in_tx_product_type_drift:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id WHERE p.product_type_id IS DISTINCT FROM f.product_type_id;
SELECT 'METRIC:in_tx_deleted_drift:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id WHERE p.deleted_at IS NOT NULL;
SELECT 'METRIC:in_tx_identity_drift:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id
  WHERE p.name IS DISTINCT FROM f.old_name
     OR p.sku IS DISTINCT FROM f.sku
     OR COALESCE(p.manufacturer_code, '') IS DISTINCT FROM f.manufacturer_code
     OR p.brand_id IS DISTINCT FROM f.brand_id
     OR p.product_type_id IS DISTINCT FROM f.product_type_id
     OR p.deleted_at IS NOT NULL;
CREATE TEMP TABLE p2e_identity_gate AS
  SELECT COUNT(*)::int AS n FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id
  WHERE p.name IS DISTINCT FROM f.old_name
     OR p.sku IS DISTINCT FROM f.sku
     OR COALESCE(p.manufacturer_code, '') IS DISTINCT FROM f.manufacturer_code
     OR p.brand_id IS DISTINCT FROM f.brand_id
     OR p.product_type_id IS DISTINCT FROM f.product_type_id
     OR p.deleted_at IS NOT NULL;
"""

    drift_sim = ""
    if failure_injection == "identity_drift_simulation" and prestate:
        first_id = int(prestate[0]["product_id"])
        drift_sim = f"UPDATE products SET sku = sku || '-drift' WHERE id = {first_id};\n"

    validation_fail = ""
    if failure_injection == "validation_failure":
        validation_fail = "SELECT 1/0;\n"

    after_logs_fail = ""
    if failure_injection == "after_all_logs":
        after_logs_fail = "SELECT 1/0;\n"

    return f"""
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT pg_advisory_xact_lock(hashtext({sql_literal(ADVISORY_LOCK_KEY)}));
CREATE TEMP TABLE p2e_frozen_identity (
  id int PRIMARY KEY,
  old_name text NOT NULL,
  sku text NOT NULL,
  manufacturer_code text NOT NULL,
  brand_id int,
  product_type_id int,
  new_name text NOT NULL,
  new_name_norm text NOT NULL
);
INSERT INTO p2e_frozen_identity (
  id, old_name, sku, manufacturer_code, brand_id, product_type_id, new_name, new_name_norm
) VALUES
  {frozen_values};
{catalog_sql}
CREATE TEMP TABLE p2e_before AS
  SELECT id, name, sku, slug, manufacturer_code, brand_id, category_id, product_type_id,
         meta_title, meta_description, base_price, original_price, is_available, is_active,
         deleted_at, stock_quantity, tax_percent
  FROM products WHERE id IN ({id_csv});
CREATE TEMP TABLE p2e_nontarget_before AS
  SELECT id, name, sku, slug, manufacturer_code, brand_id, category_id, product_type_id,
         meta_title, meta_description, base_price, original_price, is_available, is_active,
         deleted_at, stock_quantity, tax_percent
  FROM products WHERE deleted_at IS NULL AND id NOT IN ({id_csv});
SELECT id FROM products WHERE id IN ({id_csv}) ORDER BY id FOR UPDATE;
{drift_sim}
{identity_drift_block}
{body}
SELECT 'METRIC:updates_exact:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id
  WHERE p.name IS NOT DISTINCT FROM f.new_name;
SELECT 'METRIC:old_names_remaining:' || COUNT(*)::text FROM products p
  JOIN p2e_frozen_identity f ON p.id = f.id
  WHERE p.name IS NOT DISTINCT FROM f.old_name;
SELECT 'METRIC:target_protected_drift:' || COUNT(*)::text FROM products p
  JOIN p2e_before b ON p.id = b.id
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
SELECT 'METRIC:rehearsal_logs_exact:' || COUNT(*)::text FROM product_change_logs
  WHERE reason = {sql_literal(reason)} AND field_name = 'name';
SELECT 'METRIC:exact_name_collisions:' || COUNT(*)::text FROM (
  SELECT f.new_name FROM p2e_frozen_identity f
  GROUP BY f.new_name HAVING COUNT(*) > 1
) s;
SELECT 'METRIC:normalized_name_collisions:' || COUNT(*)::text FROM (
  SELECT f.new_name_norm FROM p2e_frozen_identity f
  GROUP BY f.new_name_norm HAVING COUNT(*) > 1
) s;
SELECT 'METRIC:catalog_exact_collisions:' || COUNT(*)::text FROM p2e_frozen_identity f
  WHERE EXISTS (
    SELECT 1 FROM products p
    WHERE p.deleted_at IS NULL AND p.id <> f.id AND p.name = f.new_name
  );
SELECT 'METRIC:catalog_normalized_collisions:' || COUNT(*)::text FROM p2e_frozen_identity f
  WHERE EXISTS (
    SELECT 1 FROM p2e_catalog_norm cn
    JOIN products p ON p.id = cn.product_id
    WHERE p.deleted_at IS NULL AND cn.product_id <> f.id AND cn.norm_name = f.new_name_norm
  );
SELECT 'METRIC:non_target_name_changes:' || COUNT(*)::text FROM products p
  JOIN p2e_nontarget_before b ON p.id = b.id
  WHERE p.name IS DISTINCT FROM b.name;
SELECT 'METRIC:non_target_protected_changes:' || COUNT(*)::text FROM products p
  JOIN p2e_nontarget_before b ON p.id = b.id
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
SELECT 'LOGROW:' || row_to_json(t)::text FROM (
  SELECT id, product_id, field_name, old_value, new_value, reason, actor_user_id
  FROM product_change_logs
  WHERE reason = {sql_literal(reason)} AND field_name = 'name'
  ORDER BY product_id, id
) t;
{after_logs_fail}
{validation_fail}
ROLLBACK;
"""


def parse_rehearsal_stdout(stdout: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    metrics: dict[str, int] = {}
    log_rows: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        m = METRIC_RE.match(line.strip())
        if m:
            metrics[m.group(1)] = int(m.group(2))
            continue
        lm = LOGROW_RE.match(line.strip())
        if lm:
            log_rows.append(json.loads(lm.group(1)))
    missing = [k for k in REQUIRED_REHEARSAL_METRICS if k not in metrics and k != "actual_log_row_mismatches"]
    if missing:
        raise RuntimeError(f"missing metrics {missing}: tail={stdout[-2000:]}")
    return metrics, log_rows


def parse_rehearsal_metrics(stdout: str) -> dict[str, int]:
    metrics, _ = parse_rehearsal_stdout(stdout)
    return metrics


def audit_rehearsal_logs(
    prestate: list[dict[str, str]],
    log_rows: list[dict[str, Any]],
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    expected_by_pid = {
        int(r["product_id"]): {
            "product_id": int(r["product_id"]),
            "field_name": "name",
            "old_value": r["expected_old_name"],
            "new_value": r["proposed_name"],
            "reason": REHEARSAL_REASON,
            "actor_user_id": None,
        }
        for r in prestate
    }
    cohort_ids = set(expected_by_pid)
    actual_for_cohort = [r for r in log_rows if int(r["product_id"]) in cohort_ids]
    non_target_logs = len(log_rows) - len(actual_for_cohort)
    by_pid: dict[int, list[dict[str, Any]]] = {}
    for row in actual_for_cohort:
        by_pid.setdefault(int(row["product_id"]), []).append(row)

    wrong_product = 0
    wrong_field = 0
    wrong_old = 0
    wrong_new = 0
    wrong_reason = 0
    duplicates = 0
    for pid, rows in by_pid.items():
        if len(rows) > 1:
            duplicates += len(rows) - 1
        row = rows[0]
        exp = expected_by_pid.get(pid)
        if not exp:
            wrong_product += 1
            continue
        if row.get("field_name") != "name":
            wrong_field += 1
        if (row.get("old_value") or "") != exp["old_value"]:
            wrong_old += 1
        if (row.get("new_value") or "") != exp["new_value"]:
            wrong_new += 1
        if (row.get("reason") or "") != REHEARSAL_REASON:
            wrong_reason += 1

    missing = len(cohort_ids - set(by_pid))
    extra = max(0, len(actual_for_cohort) - len(by_pid))
    mismatches = (
        missing
        + extra
        + duplicates
        + wrong_product
        + wrong_field
        + wrong_old
        + wrong_new
        + wrong_reason
        + non_target_logs
    )
    summary = {
        "actual_rows": len(log_rows),
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "wrong_product_id": wrong_product,
        "wrong_field_name": wrong_field,
        "wrong_old_value": wrong_old,
        "wrong_new_value": wrong_new,
        "wrong_reason": wrong_reason,
        "non_target_rehearsal_logs": non_target_logs,
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
                "expected_old_value": exp["old_value"] if exp else "",
                "expected_new_value": exp["new_value"] if exp else "",
                "match": (
                    "yes"
                    if exp
                    and row.get("field_name") == "name"
                    and (row.get("old_value") or "") == exp["old_value"]
                    and (row.get("new_value") or "") == exp["new_value"]
                    and (row.get("reason") or "") == REHEARSAL_REASON
                    else "no"
                ),
            }
        )
    return summary, csv_rows


def rehearsal_success_metrics(metrics: dict[str, int], expected_rows: int) -> list[str]:
    errors: list[str] = []
    checks = {
        "in_tx_identity_drift": 0,
        "in_tx_name_drift": 0,
        "in_tx_sku_drift": 0,
        "in_tx_manufacturer_code_drift": 0,
        "in_tx_brand_drift": 0,
        "in_tx_product_type_drift": 0,
        "in_tx_deleted_drift": 0,
        "updates_exact": expected_rows,
        "old_names_remaining": 0,
        "target_protected_drift": 0,
        "rehearsal_logs_exact": expected_rows,
        "actual_log_row_mismatches": 0,
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


RehearsalStatus = Literal["READY_FOR_OWNER_APPLY_AUTHORIZATION", "PARTIAL", "BLOCKED"]
