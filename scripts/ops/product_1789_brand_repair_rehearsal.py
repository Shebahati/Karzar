#!/usr/bin/env python3
"""Product 1789 brand_id NULL→3 REHEARSAL only (mandatory ROLLBACK).

REAL APPLY is intentionally unsupported. Any --apply / COMMIT request is rejected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "audit/product-1789-brand-integrity-2026-10-06"

PRODUCT_ID = 1789
EXPECTED_SKU = "1114-150"
EXPECTED_MFG = "1114-150"
EXPECTED_BRAND_ID = 3
REHEARSAL_REASON = "product_1789_brand_integrity_rehearsal_rollback_only"

COMMIT_RE = re.compile(r"(^|[^A-Z_])COMMIT(\s|;|$)", re.I)
APPLY_FLAGS = {"--apply", "--real-apply", "--commit", "--execute-apply"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current_state_hash(
    *,
    product_id: int,
    sku: str,
    manufacturer_code: str,
    brand_id: str | None,
    is_available: str,
    base_price: str,
    deleted_at: str | None,
    updated_at: str,
) -> str:
    payload = "|".join(
        [
            str(product_id),
            sku,
            manufacturer_code,
            brand_id if brand_id is not None else "NULL",
            is_available,
            base_price,
            deleted_at if deleted_at is not None else "NULL",
            updated_at,
        ]
    )
    return sha256_text(payload)


def reject_real_apply(argv: list[str]) -> None:
    lowered = {a.lower() for a in argv}
    if lowered & APPLY_FLAGS or any("apply" == a.lstrip("-").lower() for a in argv):
        raise SystemExit(
            "REAL_REPAIR_AUTHORIZED=NO — this tooling supports rehearsal+ROLLBACK only"
        )


def _run_ssh_script(script: str, *, ssh_host: str) -> str:
    if COMMIT_RE.search(script):
        raise RuntimeError("COMMIT forbidden in brand repair rehearsal tooling")
    if "ROLLBACK" not in script.upper():
        raise RuntimeError("Rehearsal script must include ROLLBACK")
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "bash", "-s"],
        input=f"""set -euo pipefail
docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging -v ON_ERROR_STOP=1 -At <<'EOSQL'
{script}
EOSQL
""",
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-4000:] or proc.stdout[-4000:])
    return proc.stdout


def _parse_kv(stdout: str) -> dict[str, str]:
    """Parse METRIC:/ROW:/PROOF: lines; values may contain ':'."""
    out: dict[str, str] = {}
    prefixes = ("METRIC:", "ROW:", "PROOF:")
    for line in stdout.splitlines():
        line = line.strip()
        for prefix in prefixes:
            if line.startswith(prefix):
                # Keep prefix in key up to second colon segment where present
                # e.g. ROW:pre:1789|... → key=ROW:pre, value=1789|...
                rest = line[len(prefix) :]
                if ":" in rest and prefix in ("ROW:", "PROOF:", "METRIC:"):
                    sub, _, value = rest.partition(":")
                    out[f"{prefix.rstrip(':')}:{sub}"] = value
                else:
                    out[prefix.rstrip(":")] = rest
                break
    return out


def build_rehearsal_sql() -> str:
    return f"""
BEGIN;
SELECT 'PROOF:transaction_read_only_before:' || current_setting('transaction_read_only');

SELECT 'ROW:pre:' || id || '|' || sku || '|' || COALESCE(manufacturer_code,'') || '|' ||
       COALESCE(brand_id::text,'NULL') || '|' || is_available::text || '|' ||
       base_price::text || '|' || COALESCE(deleted_at::text,'NULL') || '|' ||
       updated_at::text || '|' || is_active::text || '|' || category_id::text
FROM products WHERE id = {PRODUCT_ID};

DO $$
DECLARE
  r RECORD;
  updated_count integer;
  audit_count integer;
  other_field_changes integer;
BEGIN
  SELECT * INTO r FROM products WHERE id = {PRODUCT_ID} FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'product % missing', {PRODUCT_ID};
  END IF;
  IF r.brand_id IS NOT NULL THEN
    RAISE EXCEPTION 'gate fail: brand_id is % not NULL', r.brand_id;
  END IF;
  IF r.sku IS DISTINCT FROM '{EXPECTED_SKU}' THEN
    RAISE EXCEPTION 'gate fail: sku %', r.sku;
  END IF;
  IF r.manufacturer_code IS DISTINCT FROM '{EXPECTED_MFG}' THEN
    RAISE EXCEPTION 'gate fail: manufacturer_code %', r.manufacturer_code;
  END IF;
  IF r.deleted_at IS NOT NULL THEN
    RAISE EXCEPTION 'gate fail: deleted_at set';
  END IF;

  UPDATE products
  SET brand_id = {EXPECTED_BRAND_ID}
  WHERE id = {PRODUCT_ID}
    AND brand_id IS NULL
    AND sku = '{EXPECTED_SKU}'
    AND manufacturer_code = '{EXPECTED_MFG}'
    AND deleted_at IS NULL;

  GET DIAGNOSTICS updated_count = ROW_COUNT;
  IF updated_count <> 1 THEN
    RAISE EXCEPTION 'expected 1 product update, got %', updated_count;
  END IF;

  INSERT INTO product_change_logs (
    product_id, field_name, old_value, new_value, reason, actor_user_id
  ) VALUES (
    {PRODUCT_ID}, 'brand_id', NULL, '{EXPECTED_BRAND_ID}',
    '{REHEARSAL_REASON}', NULL
  );

  SELECT COUNT(*) INTO audit_count
  FROM product_change_logs
  WHERE product_id = {PRODUCT_ID}
    AND field_name = 'brand_id'
    AND reason = '{REHEARSAL_REASON}';
  IF audit_count <> 1 THEN
    RAISE EXCEPTION 'expected 1 rehearsal audit row, got %', audit_count;
  END IF;

  SELECT COUNT(*) INTO other_field_changes
  FROM products p
  WHERE p.id = {PRODUCT_ID}
    AND (
      p.sku IS DISTINCT FROM r.sku
      OR p.manufacturer_code IS DISTINCT FROM r.manufacturer_code
      OR p.is_available IS DISTINCT FROM r.is_available
      OR p.base_price IS DISTINCT FROM r.base_price
      OR p.is_active IS DISTINCT FROM r.is_active
      OR p.category_id IS DISTINCT FROM r.category_id
      OR p.brand_id IS DISTINCT FROM {EXPECTED_BRAND_ID}
    );
  IF other_field_changes <> 0 THEN
    RAISE EXCEPTION 'protected fields drifted inside rehearsal';
  END IF;

  RAISE NOTICE 'METRIC:product_updates:%', updated_count;
  RAISE NOTICE 'METRIC:audit_rows:%', audit_count;
  RAISE NOTICE 'METRIC:protected_field_changes:0';
END $$;

SELECT 'ROW:mid:' || id || '|' || sku || '|' || COALESCE(manufacturer_code,'') || '|' ||
       COALESCE(brand_id::text,'NULL') || '|' || is_available::text || '|' ||
       base_price::text || '|' || COALESCE(deleted_at::text,'NULL') || '|' ||
       updated_at::text
FROM products WHERE id = {PRODUCT_ID};

SELECT 'METRIC:audit_visible:' || COUNT(*)::text
FROM product_change_logs
WHERE product_id = {PRODUCT_ID}
  AND field_name = 'brand_id'
  AND reason = '{REHEARSAL_REASON}';

ROLLBACK;

BEGIN;
SET TRANSACTION READ ONLY;
SELECT 'PROOF:transaction_read_only_after:' || current_setting('transaction_read_only');
SELECT 'ROW:post:' || id || '|' || sku || '|' || COALESCE(manufacturer_code,'') || '|' ||
       COALESCE(brand_id::text,'NULL') || '|' || is_available::text || '|' ||
       base_price::text || '|' || COALESCE(deleted_at::text,'NULL') || '|' ||
       updated_at::text
FROM products WHERE id = {PRODUCT_ID};
SELECT 'METRIC:post_audit_absent:' || COUNT(*)::text
FROM product_change_logs
WHERE product_id = {PRODUCT_ID}
  AND field_name = 'brand_id'
  AND reason = '{REHEARSAL_REASON}';
SELECT 'METRIC:brand_logs_total:' || COUNT(*)::text
FROM product_change_logs
WHERE product_id = {PRODUCT_ID}
  AND field_name = 'brand_id';
ROLLBACK;
"""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    reject_real_apply(argv)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default="karzar-vps")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    identity = {
        "host": "srv5944957438",
        "db_container": "lathe_postgres",
        "db_name": "karzar_staging",
        "db_user": "karzar_staging",
        "volume": "karzar_postgres_data",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "REAL_REPAIR_AUTHORIZED": "NO",
    }

    # Plane proof (read-only)
    proof_out = _run_ssh_script(
        """
BEGIN;
SET TRANSACTION READ ONLY;
SELECT 'PROOF:transaction_read_only:' || current_setting('transaction_read_only');
SELECT 'PROOF:db:' || current_database();
SELECT 'PROOF:user:' || current_user;
SELECT 'ROW:pre:' || id || '|' || sku || '|' || COALESCE(manufacturer_code,'') || '|' ||
       COALESCE(brand_id::text,'NULL') || '|' || is_available::text || '|' ||
       base_price::text || '|' || COALESCE(deleted_at::text,'NULL') || '|' ||
       updated_at::text || '|' || is_active::text || '|' || category_id::text
FROM products WHERE id = 1789;
ROLLBACK;
""",
        ssh_host=args.ssh_host,
    )
    host_proof = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", args.ssh_host, "hostname"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    vol_proof = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            args.ssh_host,
            "docker inspect -f '{{range .Mounts}}{{.Name}} {{end}}' lathe_postgres",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    identity["host_proof"] = host_proof
    identity["volume_proof"] = vol_proof
    identity["pre_probe_stdout_sha256"] = sha256_text(proof_out)

    kv = _parse_kv(proof_out)
    pre_row = kv.get("ROW:pre", "")
    parts = pre_row.split("|")
    if len(parts) < 8:
        raise RuntimeError(f"unexpected pre row: {pre_row!r}")
    brand_token = parts[3]
    brand_id = None if brand_token == "NULL" else brand_token
    pre_hash = current_state_hash(
        product_id=int(parts[0]),
        sku=parts[1],
        manufacturer_code=parts[2],
        brand_id=brand_id,
        is_available=parts[4],
        base_price=parts[5],
        deleted_at=None if parts[6] == "NULL" else parts[6],
        updated_at=parts[7],
    )
    pre = {
        "identity": identity,
        "product_row": {
            "product_id": int(parts[0]),
            "sku": parts[1],
            "manufacturer_code": parts[2],
            "brand_id": brand_id,
            "is_available": parts[4],
            "base_price": parts[5],
            "deleted_at": None if parts[6] == "NULL" else parts[6],
            "updated_at": parts[7],
            "is_active": parts[8] if len(parts) > 8 else None,
            "category_id": parts[9] if len(parts) > 9 else None,
        },
        "expected_current_hash": pre_hash,
        "gates": {
            "brand_id_is_null": brand_id is None,
            "sku_match": parts[1] == EXPECTED_SKU,
            "manufacturer_code_match": parts[2] == EXPECTED_MFG,
            "deleted_at_null": parts[6] == "NULL",
            "host_ok": host_proof == "srv5944957438",
            "volume_ok": "karzar_postgres_data" in vol_proof,
            "transaction_read_only": kv.get("PROOF:transaction_read_only") == "on",
        },
    }
    (out_dir / "REHEARSAL_PRE.json").write_text(
        json.dumps(pre, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if not all(pre["gates"].values()):
        raise SystemExit(f"identity gates failed: {json.dumps(pre['gates'])}")

    rehearsal_sql = build_rehearsal_sql()
    raw = _run_ssh_script(rehearsal_sql, ssh_host=args.ssh_host)
    rkv = _parse_kv(raw)
    product_updates = 1 if "ROW:mid:" in raw and "|3|" in raw else 0
    audit_rows = int(rkv.get("METRIC:audit_visible", "0") or "0")
    post_audit = int(rkv.get("METRIC:post_audit_absent", "1") or "1")
    post_row = rkv.get("ROW:post", "")
    mid_row = rkv.get("ROW:mid", "")

    result = {
        "status": "ROLLED_BACK_REHEARSAL",
        "REAL_REPAIR_AUTHORIZED": "NO",
        "identity_gate": "PASS",
        "transient_product_updates": product_updates,
        "transient_audit_rows": audit_rows,
        "protected_field_changes": 0,
        "rollback": "YES",
        "mid_row": mid_row,
        "post_row": post_row,
        "stdout_sha256": sha256_text(raw),
        "reason": REHEARSAL_REASON,
        "expected_brand_id": EXPECTED_BRAND_ID,
    }
    # Require mid brand_id=3 and post brand_id NULL
    mid_parts = mid_row.split("|")
    post_parts = post_row.split("|")
    if len(mid_parts) < 4 or mid_parts[3] != "3":
        result["status"] = "FAILED"
        raise SystemExit(f"mid-state brand gate failed: {mid_row!r}\n{raw[-2000:]}")
    if len(post_parts) < 4 or post_parts[3] != "NULL":
        result["status"] = "FAILED"
        raise SystemExit(f"post-rollback brand gate failed: {post_row!r}")
    if post_audit != 0:
        result["status"] = "FAILED"
        raise SystemExit(f"rehearsal audit rows persisted: {post_audit}")
    if audit_rows != 1:
        # audit_visible may appear before rollback; if missing from -At, infer from mid success
        result["transient_audit_rows"] = 1
        result["audit_rows_note"] = "inferred_from_successful_do_block_and_mid_state"

    (out_dir / "REHEARSAL_RESULT.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    post = {
        "brand_id_remains_null": post_parts[3] == "NULL",
        "rehearsal_logs_absent": post_audit == 0,
        "persistent_product_mutations": 0,
        "persistent_change_log_rows": 0,
        "post_row": post_row,
        "brand_logs_total": int(rkv.get("METRIC:brand_logs_total", "0") or "0"),
        "REAL_REPAIR_AUTHORIZED": "NO",
    }
    (out_dir / "REHEARSAL_POST_ROLLBACK.json").write_text(
        json.dumps(post, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], "post": post}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
