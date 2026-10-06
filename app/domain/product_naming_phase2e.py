"""Phase 2E — transactional Product.name rename rehearsal (frozen Phase 2D cohort)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

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


def target_fingerprint_row(live: dict[str, Any]) -> str:
    parts = []
    for col in PROTECTED_PRODUCT_COLUMNS:
        val = live.get(col)
        parts.append(f"{col}={'' if val is None else val}")
    return "|".join(parts)


def build_rehearsal_sql(prestate: list[dict[str, str]]) -> str:
    """Single SERIALIZABLE transaction; always ends with ROLLBACK."""
    ids = sorted(int(r["product_id"]) for r in prestate)
    id_csv = ",".join(str(i) for i in ids)
    reason = REHEARSAL_REASON
    updates: list[str] = []
    for row in prestate:
        pid = int(row["product_id"])
        old = row["expected_old_name"]
        new = row["proposed_name"]
        sku = row["sku"]
        updates.append(
            f"""
UPDATE products SET name = {sql_literal(new)}
WHERE id = {pid}
  AND name = {sql_literal(old)}
  AND sku = {sql_literal(sku)}
  AND deleted_at IS NULL;
"""
        )
        updates.append(
            f"""
INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
VALUES ({pid}, 'name', {sql_literal(old)}, {sql_literal(new)}, {sql_literal(reason)}, NULL);
"""
        )
    body = "\n".join(updates)
    proposed_values = ",\n  ".join(
        f"({int(r['product_id'])},{sql_literal(r['proposed_name'])})" for r in prestate
    )
    old_values = ",\n  ".join(
        f"({int(r['product_id'])},{sql_literal(r['expected_old_name'])})" for r in prestate
    )
    return f"""
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT pg_advisory_xact_lock(hashtext({sql_literal(ADVISORY_LOCK_KEY)}));
CREATE TEMP TABLE p2e_expected_old (id int PRIMARY KEY, old_name text);
INSERT INTO p2e_expected_old (id, old_name) VALUES
  {old_values};
CREATE TEMP TABLE p2e_expected_new (id int PRIMARY KEY, new_name text);
INSERT INTO p2e_expected_new (id, new_name) VALUES
  {proposed_values};
CREATE TEMP TABLE p2e_before AS
  SELECT id, name, sku, slug, manufacturer_code, brand_id, category_id, product_type_id,
         meta_title, meta_description, base_price, original_price, is_available, is_active,
         deleted_at, stock_quantity, tax_percent
  FROM products WHERE id IN ({id_csv});
CREATE TEMP TABLE p2e_all_names AS
  SELECT id, name FROM products WHERE deleted_at IS NULL;
SELECT id FROM products WHERE id IN ({id_csv}) ORDER BY id FOR UPDATE;
SELECT 'METRIC:drift_in_tx:' || COUNT(*)::text FROM products p
  JOIN p2e_expected_old e ON p.id = e.id
  WHERE p.name IS DISTINCT FROM e.old_name
     OR p.deleted_at IS NOT NULL;
{body}
SELECT 'METRIC:updates_exact:' || COUNT(*)::text FROM products p
  JOIN p2e_expected_new e ON p.id = e.id
  WHERE p.name IS NOT DISTINCT FROM e.new_name;
SELECT 'METRIC:old_names_remaining:' || COUNT(*)::text FROM products p
  JOIN p2e_expected_old e ON p.id = e.id
  WHERE p.name IS NOT DISTINCT FROM e.old_name;
SELECT 'METRIC:protected_drift:' || COUNT(*)::text FROM products p
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
SELECT 'METRIC:rehearsal_logs:' || COUNT(*)::text FROM product_change_logs
  WHERE reason = {sql_literal(reason)} AND field_name = 'name';
SELECT 'METRIC:exact_name_collisions:' || COUNT(*)::text FROM (
  SELECT name FROM products WHERE deleted_at IS NULL AND name IN (
    SELECT new_name FROM p2e_expected_new
  ) GROUP BY name HAVING COUNT(*) > 1
) s;
SELECT 'METRIC:non_target_name_changes:' || COUNT(*)::text FROM products p
  JOIN p2e_all_names n ON p.id = n.id
  WHERE p.id NOT IN ({id_csv}) AND p.name IS DISTINCT FROM n.name;
ROLLBACK;
"""


def parse_rehearsal_metrics(stdout: str) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for line in stdout.splitlines():
        m = re.match(r"^METRIC:([a-z_]+):(\d+)$", line.strip())
        if m:
            metrics[m.group(1)] = int(m.group(2))
    required = (
        "drift_in_tx",
        "updates_exact",
        "old_names_remaining",
        "protected_drift",
        "rehearsal_logs",
        "exact_name_collisions",
        "non_target_name_changes",
    )
    missing = [k for k in required if k not in metrics]
    if missing:
        raise RuntimeError(f"missing metrics {missing}: tail={stdout[-1200:]}")
    return metrics


def rehearsal_success_metrics(metrics: dict[str, int], expected_rows: int) -> list[str]:
    errors: list[str] = []
    if metrics["drift_in_tx"] != 0:
        errors.append("drift_in_tx")
    if metrics["updates_exact"] != expected_rows:
        errors.append("updates_exact")
    if metrics["old_names_remaining"] != 0:
        errors.append("old_names_remaining")
    if metrics["protected_drift"] != 0:
        errors.append("protected_drift")
    if metrics["rehearsal_logs"] != expected_rows:
        errors.append("rehearsal_logs")
    if metrics["exact_name_collisions"] != 0:
        errors.append("exact_name_collisions")
    if metrics["non_target_name_changes"] != 0:
        errors.append("non_target_name_changes")
    return errors


RehearsalStatus = Literal["READY_FOR_OWNER_APPLY_AUTHORIZATION", "PARTIAL", "BLOCKED"]
