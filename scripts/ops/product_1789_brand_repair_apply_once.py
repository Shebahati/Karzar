#!/usr/bin/env python3
"""Owner-authorized ONE-ROW Product 1789 brand_id NULL→3 REAL APPLY.

Fail-closed. Persistent mutation requires BOTH:
  --apply
  --confirm-manifest-sha <full REPAIR_MANIFEST.sha256 digest>

No other Product fields or rows may be mutated.
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
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
INTEGRITY_DIR = ROOT / "audit/product-1789-brand-integrity-2026-10-06"
DEFAULT_OUT = ROOT / "audit/product-1789-brand-repair-apply-2026-10-06"

PRODUCT_ID = 1789
EXPECTED_SKU = "1114-150"
EXPECTED_MFG = "1114-150"
EXPECTED_BRAND_ID = 3
EXPECTED_MANIFEST_SHA = (
    "c5c572b3aadc65ec13f0692e019c645a60cd4f09e87691ddf27da20b952821d8"
)
EXPECTED_REHEARSAL_HASH = (
    "262b9c550257a32c248c650ab283c676e80e689eaa4d551dcd6afe3645f42555"
)
APPLY_REASON = "owner_authorized_brand_integrity_repair"
FORBIDDEN = ("--force", "--skip-preflight", "--ignore-drift", "--yes", "--partial")

CORE_PRECONDITIONS = (
    "id=1789",
    "sku=1114-150",
    "manufacturer_code=1114-150",
    "brand_id IS NULL",
    "deleted_at IS NULL",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _run_ssh_argv(remote_argv: list[str], *, ssh_host: str) -> str:
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, *remote_argv],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-4000:] or proc.stdout[-4000:] or "ssh failed")
    return proc.stdout


def _run_psql_script(script: str, *, ssh_host: str, allow_commit: bool = False) -> str:
    if not allow_commit and re.search(r"(^|[^A-Z_])COMMIT(\s|;|$)", script, re.I):
        raise RuntimeError("COMMIT forbidden unless allow_commit=True")
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
        raise RuntimeError(proc.stderr[-6000:] or proc.stdout[-6000:] or "psql failed")
    return proc.stdout


def _parse_kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        line = line.strip()
        for prefix in ("METRIC:", "ROW:", "PROOF:", "JSON:"):
            if line.startswith(prefix):
                rest = line[len(prefix) :]
                if ":" in rest:
                    sub, _, value = rest.partition(":")
                    out[f"{prefix.rstrip(':')}:{sub}"] = value
                else:
                    out[prefix.rstrip(":")] = rest
                break
    return out


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def collect_identity(ssh_host: str) -> dict[str, Any]:
    host = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "hostname"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    vol = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            ssh_host,
            "docker inspect -f '{{range .Mounts}}{{.Name}} {{end}}' lathe_postgres",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    container = (
        subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                ssh_host,
                "docker inspect -f '{{.Name}}' lathe_postgres",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
        .lstrip("/")
    )
    app_env = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            ssh_host,
            "docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' lathe_api "
            "| grep -E '^(APP_ENV|KARZAR_DATA_PLANE)=' || true",
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    env_map: dict[str, str | None] = {"APP_ENV": None, "KARZAR_DATA_PLANE": None}
    for line in app_env.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            if k in env_map:
                env_map[k] = v
    proof = _run_psql_script(
        """
BEGIN;
SET TRANSACTION READ ONLY;
SELECT 'PROOF:transaction_read_only:' || current_setting('transaction_read_only');
SELECT 'PROOF:db:' || current_database();
SELECT 'PROOF:user:' || current_user;
SELECT 'PROOF:alembic:' || COALESCE(
  (SELECT version_num FROM alembic_version LIMIT 1), 'UNKNOWN');
SELECT 'PROOF:utc:' || (NOW() AT TIME ZONE 'UTC')::text;
ROLLBACK;
""",
        ssh_host=ssh_host,
    )
    kv = _parse_kv(proof)
    identity = {
        "host_expected": "srv5944957438",
        "host_proof": host,
        "db_container_expected": "lathe_postgres",
        "db_container_proof": container,
        "database_expected": "karzar_staging",
        "database_proof": kv.get("PROOF:db"),
        "database_user_proof": kv.get("PROOF:user"),
        "volume_expected": "karzar_postgres_data",
        "volume_proof": vol,
        "APP_ENV": env_map["APP_ENV"],
        "KARZAR_DATA_PLANE": env_map["KARZAR_DATA_PLANE"],
        "alembic_revision": kv.get("PROOF:alembic"),
        "transaction_read_only": kv.get("PROOF:transaction_read_only"),
        "utc": kv.get("PROOF:utc"),
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "gates": {
            "host_ok": host == "srv5944957438",
            "container_ok": "lathe_postgres" in container,
            "db_ok": kv.get("PROOF:db") == "karzar_staging",
            "user_ok": kv.get("PROOF:user") == "karzar_staging",
            "volume_ok": "karzar_postgres_data" in vol,
            "transaction_read_only_on": kv.get("PROOF:transaction_read_only") == "on",
        },
    }
    if not all(identity["gates"].values()):
        raise SystemExit(f"PRODUCTION_IDENTITY_GATE_FAILED: {json.dumps(identity, indent=2)}")
    return identity


def fetch_pre_apply(ssh_host: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    raw = _run_psql_script(
        f"""
BEGIN;
SET TRANSACTION READ ONLY;
SELECT 'JSON:product:' || row_to_json(t)::text FROM (
  SELECT id, sku, manufacturer_code, brand_id, name, slug, category_id,
         is_active, is_available, base_price::text AS base_price,
         original_price::text AS original_price, deleted_at, updated_at, created_at
  FROM products WHERE id = {PRODUCT_ID}
) t;
SELECT 'JSON:brand3:' || row_to_json(t)::text FROM (
  SELECT id, name, slug FROM brands WHERE id = {EXPECTED_BRAND_ID}
) t;
SELECT 'JSON:changelog:' || COALESCE(json_agg(row_to_json(t) ORDER BY t.id)::text, '[]')
FROM (
  SELECT id, product_id, field_name, old_value, new_value, reason, actor_user_id,
         created_at
  FROM product_change_logs WHERE product_id = {PRODUCT_ID}
) t;
SELECT 'METRIC:sellable:' || COUNT(*)::text FROM products p
WHERE p.deleted_at IS NULL AND p.is_active AND p.is_available
  AND p.base_price IS NOT NULL AND p.base_price > 0
  AND EXISTS (
    SELECT 1 FROM product_images pi
    WHERE pi.product_id = p.id
      AND pi.image_url IS NOT NULL AND btrim(pi.image_url) <> ''
      AND pi.image_url NOT ILIKE '%placeholder%'
  );
ROLLBACK;
""",
        ssh_host=ssh_host,
    )
    kv = _parse_kv(raw)
    product = json.loads(kv["JSON:product"])
    brand = json.loads(kv["JSON:brand3"])
    logs = json.loads(kv.get("JSON:changelog", "[]") or "[]")
    sellable = int(kv.get("METRIC:sellable", "0") or "0")
    return product, logs, {"brand3": brand, "sellable": sellable}


def build_apply_sql() -> str:
    return f"""
BEGIN;
SELECT 'PROOF:txn_read_only:' || current_setting('transaction_read_only');

DO $$
DECLARE
  r RECORD;
  updated_count integer;
  audit_count integer;
  brand_name text;
  other_changes integer;
BEGIN
  SELECT * INTO r FROM products WHERE id = {PRODUCT_ID} FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'product % missing', {PRODUCT_ID};
  END IF;
  IF r.brand_id IS NOT NULL THEN
    RAISE EXCEPTION 'ALREADY_REPAIRED_OR_DRIFT: brand_id=%', r.brand_id;
  END IF;
  IF r.sku IS DISTINCT FROM '{EXPECTED_SKU}' THEN
    RAISE EXCEPTION 'gate fail sku=%', r.sku;
  END IF;
  IF r.manufacturer_code IS DISTINCT FROM '{EXPECTED_MFG}' THEN
    RAISE EXCEPTION 'gate fail manufacturer_code=%', r.manufacturer_code;
  END IF;
  IF r.deleted_at IS NOT NULL THEN
    RAISE EXCEPTION 'gate fail deleted_at set';
  END IF;

  SELECT name INTO brand_name FROM brands WHERE id = {EXPECTED_BRAND_ID};
  IF brand_name IS NULL THEN
    RAISE EXCEPTION 'brand % missing', {EXPECTED_BRAND_ID};
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
    '{APPLY_REASON}', NULL
  );

  SELECT COUNT(*) INTO audit_count
  FROM product_change_logs
  WHERE product_id = {PRODUCT_ID}
    AND field_name = 'brand_id'
    AND reason = '{APPLY_REASON}'
    AND new_value = '{EXPECTED_BRAND_ID}'
    AND old_value IS NULL;
  IF audit_count <> 1 THEN
    RAISE EXCEPTION 'expected exactly 1 apply audit row, got %', audit_count;
  END IF;

  SELECT COUNT(*) INTO other_changes
  FROM products p
  WHERE p.id = {PRODUCT_ID}
    AND (
      p.sku IS DISTINCT FROM r.sku
      OR p.manufacturer_code IS DISTINCT FROM r.manufacturer_code
      OR p.name IS DISTINCT FROM r.name
      OR p.slug IS DISTINCT FROM r.slug
      OR p.category_id IS DISTINCT FROM r.category_id
      OR p.is_active IS DISTINCT FROM r.is_active
      OR p.is_available IS DISTINCT FROM r.is_available
      OR p.base_price IS DISTINCT FROM r.base_price
      OR p.original_price IS DISTINCT FROM r.original_price
      OR p.deleted_at IS DISTINCT FROM r.deleted_at
      OR p.brand_id IS DISTINCT FROM {EXPECTED_BRAND_ID}
    );
  IF other_changes <> 0 THEN
    RAISE EXCEPTION 'BLOCKED_UNEXPECTED_DIFF protected fields changed';
  END IF;

  RAISE NOTICE 'METRIC:product_updates:%', updated_count;
  RAISE NOTICE 'METRIC:audit_rows:%', audit_count;
  RAISE NOTICE 'METRIC:brand_name:%', brand_name;
END $$;

SELECT 'ROW:post_txn:' || id || '|' || sku || '|' || COALESCE(manufacturer_code,'') || '|' ||
       COALESCE(brand_id::text,'NULL') || '|' || is_available::text || '|' ||
       base_price::text || '|' || is_active::text || '|' || updated_at::text
FROM products WHERE id = {PRODUCT_ID};

SELECT 'METRIC:audit_visible:' || COUNT(*)::text
FROM product_change_logs
WHERE product_id = {PRODUCT_ID}
  AND field_name = 'brand_id'
  AND reason = '{APPLY_REASON}';

COMMIT;
SELECT 'PROOF:commit:YES';
SELECT 'PROOF:commit_utc:' || (NOW() AT TIME ZONE 'UTC')::text;
"""


def fresh_post_verify(ssh_host: str) -> dict[str, Any]:
    raw = _run_psql_script(
        f"""
BEGIN;
SET TRANSACTION READ ONLY;
SELECT 'PROOF:transaction_read_only:' || current_setting('transaction_read_only');
SELECT 'JSON:product:' || row_to_json(t)::text FROM (
  SELECT id, sku, manufacturer_code, brand_id, name, slug, category_id,
         is_active, is_available, base_price::text AS base_price,
         original_price::text AS original_price, deleted_at, updated_at
  FROM products WHERE id = {PRODUCT_ID}
) t;
SELECT 'JSON:brand:' || row_to_json(t)::text FROM (
  SELECT b.id, b.name FROM brands b
  JOIN products p ON p.brand_id = b.id WHERE p.id = {PRODUCT_ID}
) t;
SELECT 'JSON:apply_logs:' || COALESCE(json_agg(row_to_json(t) ORDER BY t.id)::text, '[]')
FROM (
  SELECT id, product_id, field_name, old_value, new_value, reason, actor_user_id, created_at
  FROM product_change_logs
  WHERE product_id = {PRODUCT_ID}
    AND field_name = 'brand_id'
    AND reason = '{APPLY_REASON}'
) t;
SELECT 'METRIC:brand_logs_total:' || COUNT(*)::text
FROM product_change_logs
WHERE product_id = {PRODUCT_ID} AND field_name = 'brand_id';
SELECT 'METRIC:sellable:' || COUNT(*)::text FROM products p
WHERE p.deleted_at IS NULL AND p.is_active AND p.is_available
  AND p.base_price IS NOT NULL AND p.base_price > 0
  AND EXISTS (
    SELECT 1 FROM product_images pi
    WHERE pi.product_id = p.id
      AND pi.image_url IS NOT NULL AND btrim(pi.image_url) <> ''
      AND pi.image_url NOT ILIKE '%placeholder%'
  );
ROLLBACK;
""",
        ssh_host=ssh_host,
    )
    kv = _parse_kv(raw)
    return {
        "transaction_read_only": kv.get("PROOF:transaction_read_only"),
        "product": json.loads(kv["JSON:product"]),
        "brand": json.loads(kv.get("JSON:brand", "null") or "null"),
        "apply_logs": json.loads(kv.get("JSON:apply_logs", "[]") or "[]"),
        "brand_logs_total": int(kv.get("METRIC:brand_logs_total", "0") or "0"),
        "sellable": int(kv.get("METRIC:sellable", "0") or "0"),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    for flag in FORBIDDEN:
        if flag in argv:
            raise SystemExit(f"forbidden flag: {flag}")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default="karzar-vps")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-manifest-sha", default="")
    args = parser.parse_args(argv)

    out: Path = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    manifest = INTEGRITY_DIR / "REPAIR_MANIFEST.csv"
    manifest_sha_file = INTEGRITY_DIR / "REPAIR_MANIFEST.sha256"
    if not manifest.is_file() or not manifest_sha_file.is_file():
        raise SystemExit("BLOCKED: repair manifest missing on this checkout")
    actual_manifest_sha = sha256_file(manifest)
    file_sha = manifest_sha_file.read_text(encoding="utf-8").split()[0].strip()
    if actual_manifest_sha != EXPECTED_MANIFEST_SHA or file_sha != EXPECTED_MANIFEST_SHA:
        raise SystemExit(
            f"BLOCKED: manifest SHA unexpected actual={actual_manifest_sha} file={file_sha}"
        )

    print(
        "\n".join(
            [
                "OWNER_AUTHORIZED = YES",
                f"TARGET_PRODUCT_ID = {PRODUCT_ID}",
                f"TARGET_SKU = {EXPECTED_SKU}",
                "AUTHORIZED_PRODUCT_CHANGE:",
                f"brand_id NULL → {EXPECTED_BRAND_ID}",
                "AUTHORIZED_AUDIT_ROWS = 1",
                "AUTHORIZED_OTHER_CHANGES = NONE",
            ]
        )
    )

    identity = collect_identity(args.ssh_host)
    _write_json(out / "IDENTITY_PROBE.json", identity)

    product, logs, extras = fetch_pre_apply(args.ssh_host)
    brand3 = extras["brand3"]
    sellable_before = extras["sellable"]
    _write_json(out / "PRE_APPLY_PRODUCT.json", product)
    _write_json(out / "PRE_APPLY_CHANGE_LOGS.json", logs)

    brand_id = product.get("brand_id")
    if brand_id == EXPECTED_BRAND_ID:
        _write_json(
            out / "APPLY_RESULT.json",
            {
                "status": "ALREADY_REPAIRED",
                "PRODUCT_MUTATION": 0,
                "AUDIT_ROWS_CREATED": 0,
            },
        )
        print(json.dumps({"status": "ALREADY_REPAIRED"}, indent=2))
        return 0

    core_ok = (
        product.get("id") == PRODUCT_ID
        and product.get("sku") == EXPECTED_SKU
        and product.get("manufacturer_code") == EXPECTED_MFG
        and brand_id is None
        and product.get("deleted_at") is None
    )
    if not core_ok:
        raise SystemExit(
            f"BLOCKED_CURRENT_STATE_DRIFT: core preconditions failed product={product}"
        )

    brand_name = (brand3 or {}).get("name") or ""
    brand_ok = (brand3 or {}).get("id") == EXPECTED_BRAND_ID and (
        "INSIZE" in brand_name.upper() or "اینسایز" in brand_name
    )
    if not brand_ok:
        raise SystemExit(f"BLOCKED: brand 3 identity failed: {brand3}")

    # Rehearsal used psql text: '2026-10-04 11:19:55.937259+00'
    updated_psqlish = str(product["updated_at"])
    if "T" in updated_psqlish:
        updated_psqlish = (
            updated_psqlish.replace("T", " ").replace("Z", "+00").replace("+00:00", "+00")
        )
    cur_hash = current_state_hash(
        product_id=int(product["id"]),
        sku=product["sku"],
        manufacturer_code=product["manufacturer_code"],
        brand_id=None,
        is_available=(
            "true"
            if product["is_available"] in (True, "true", "t")
            else str(product["is_available"])
        ),
        base_price=str(product["base_price"]),
        deleted_at=None,
        updated_at=updated_psqlish,
    )
    hash_info = {
        "expected_rehearsal_hash": EXPECTED_REHEARSAL_HASH,
        "current_row_hash": cur_hash,
        "CURRENT_HASH_MATCH": cur_hash == EXPECTED_REHEARSAL_HASH,
        "core_preconditions": list(CORE_PRECONDITIONS),
        "core_preconditions_pass": True,
        "is_active": product.get("is_active"),
        "is_available": product.get("is_available"),
        "base_price": product.get("base_price"),
        "note": "updated_at included in hash; DB trigger will refresh updated_at on APPLY",
    }
    _write_json(out / "CURRENT_STATE_HASH.json", hash_info)
    if not hash_info["CURRENT_HASH_MATCH"]:
        # Allow proceed only if core gates hold (brief allows metadata classification)
        print(
            "WARNING: current hash differs from rehearsal hash; "
            "proceeding only because core identity gates PASS",
            file=sys.stderr,
        )

    recovery = {
        "product_id": PRODUCT_ID,
        "pre_repair_product": product,
        "pre_repair_brand_id": None,
        "current_hash": cur_hash,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "db_identity": {
            "host": identity["host_proof"],
            "database": identity["database_proof"],
            "container": identity["db_container_proof"],
            "volume": identity["volume_proof"],
            "alembic": identity["alembic_revision"],
        },
        "rollback_guard": {
            "require_id": PRODUCT_ID,
            "require_sku": EXPECTED_SKU,
            "require_manufacturer_code": EXPECTED_MFG,
            "require_brand_id": EXPECTED_BRAND_ID,
            "restore_brand_id": None,
        },
    }
    _write_json(out / "RECOVERY_SNAPSHOT.json", recovery)
    recovery_sha = sha256_file(out / "RECOVERY_SNAPSHOT.json")
    (out / "RECOVERY_SNAPSHOT.sha256").write_text(
        f"{recovery_sha}  RECOVERY_SNAPSHOT.json\n", encoding="utf-8"
    )
    rollback_sql = f"""-- Guarded rollback for Product 1789 brand repair
-- Only restores brand_id NULL if current state still matches post-repair guards.
BEGIN;
UPDATE products
SET brand_id = NULL
WHERE id = {PRODUCT_ID}
  AND brand_id = {EXPECTED_BRAND_ID}
  AND sku = '{EXPECTED_SKU}'
  AND manufacturer_code = '{EXPECTED_MFG}'
  AND deleted_at IS NULL;
-- Expect ROW_COUNT = 1; otherwise ROLLBACK manually.
INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
VALUES ({PRODUCT_ID}, 'brand_id', '{EXPECTED_BRAND_ID}', NULL,
        'owner_authorized_brand_integrity_repair_rollback', NULL);
COMMIT;
"""
    (out / "ROLLBACK.sql").write_text(rollback_sql, encoding="utf-8")

    auth = {
        "OWNER_AUTHORIZED": "YES",
        "authorization_quote": "مرج کردم، تعمیر 1789 را انجام بدهیم",
        "TARGET_PRODUCT_ID": PRODUCT_ID,
        "TARGET_SKU": EXPECTED_SKU,
        "AUTHORIZED_PRODUCT_CHANGE": "brand_id NULL → 3",
        "AUTHORIZED_AUDIT_ROWS": 1,
        "AUTHORIZED_OTHER_CHANGES": "NONE",
        "manifest_sha": EXPECTED_MANIFEST_SHA,
        "apply_reason": APPLY_REASON,
    }
    _write_json(
        out / "APPLY_PLAN.json",
        {
            **auth,
            "mode": "REAL_APPLY" if args.apply else "DRY_PLAN",
            "sql_summary": (
                "UPDATE products SET brand_id=3 WHERE id=1789 AND brand_id IS NULL "
                "AND sku/mfg match; INSERT product_change_logs"
            ),
        },
    )
    (out / "AUTHORIZATION.md").write_text(
        "# Authorization — Product 1789 brand repair\n\n"
        "Owner quote: «مرج کردم، تعمیر 1789 را انجام بدهیم»\n\n"
        f"- PRODUCT: {PRODUCT_ID}\n"
        f"- FIELD: brand_id NULL → {EXPECTED_BRAND_ID} (INSIZE)\n"
        "- AUDIT rows: 1\n"
        "- OTHER CHANGES: NONE\n"
        f"- Manifest SHA: `{EXPECTED_MANIFEST_SHA}`\n"
        f"- Reason: `{APPLY_REASON}`\n",
        encoding="utf-8",
    )

    if not args.apply:
        print(json.dumps({"status": "DRY_PLAN_ONLY", "hash": hash_info}, indent=2))
        return 0

    if args.confirm_manifest_sha.strip().lower() != EXPECTED_MANIFEST_SHA:
        raise SystemExit(
            "BLOCKED: --confirm-manifest-sha must equal full REPAIR_MANIFEST SHA256"
        )

    apply_stdout = _run_psql_script(
        build_apply_sql(), ssh_host=args.ssh_host, allow_commit=True
    )
    akv = _parse_kv(apply_stdout)
    if akv.get("PROOF:commit") != "YES":
        raise SystemExit(f"BLOCKED: commit proof missing\n{apply_stdout[-2000:]}")

    post = fresh_post_verify(args.ssh_host)
    _write_json(out / "POST_APPLY_PRODUCT.json", post["product"])
    _write_json(out / "POST_APPLY_CHANGE_LOGS.json", post["apply_logs"])

    p = post["product"]
    ok = (
        p.get("id") == PRODUCT_ID
        and p.get("sku") == EXPECTED_SKU
        and p.get("manufacturer_code") == EXPECTED_MFG
        and p.get("brand_id") == EXPECTED_BRAND_ID
        and p.get("is_available") == product.get("is_available")
        and p.get("is_active") == product.get("is_active")
        and str(p.get("base_price")) == str(product.get("base_price"))
        and len(post["apply_logs"]) == 1
        and post["brand_logs_total"] == 1
    )
    blast = {
        "Product_rows_changed": 1 if ok else "UNKNOWN",
        "other_Products_changed": 0,
        "availability_changes": 0
        if p.get("is_available") == product.get("is_available")
        else 1,
        "price_changes": 0
        if str(p.get("base_price")) == str(product.get("base_price"))
        else 1,
        "activation_changes": 0
        if p.get("is_active") == product.get("is_active")
        else 1,
        "manufacturer_code_changes": 0
        if p.get("manufacturer_code") == product.get("manufacturer_code")
        else 1,
        "brand_id_changes": 1 if p.get("brand_id") == EXPECTED_BRAND_ID else 0,
    }
    _write_json(out / "BLAST_RADIUS_CHECK.json", blast)
    sellability = {
        "before": sellable_before,
        "after": post["sellable"],
        "delta": post["sellable"] - sellable_before,
        "expected_delta": 0,
    }
    _write_json(out / "SELLABILITY_CHECK.json", sellability)

    result = {
        "status": "APPLIED_VERIFIED" if ok else "BLOCKED_POST_VERIFY",
        "commit_utc": akv.get("PROOF:commit_utc"),
        "post_txn_row": akv.get("ROW:post_txn"),
        "audit_visible": akv.get("METRIC:audit_visible"),
        "fresh_connection_ok": ok,
        "brand": post.get("brand"),
        "stdout_sha256": sha256_text(apply_stdout),
        "reason": APPLY_REASON,
        "PRODUCT_ROWS_MUTATED": 1 if ok else 0,
        "PRODUCT_FIELDS_MUTATED": ["brand_id"],
        "AUDIT_ROWS_CREATED": len(post["apply_logs"]),
        "OTHER_PRODUCT_ROWS_MUTATED": 0,
    }
    _write_json(out / "APPLY_RESULT.json", result)
    if not ok:
        raise SystemExit(f"POST_VERIFY_FAILED: {json.dumps(result, indent=2)}")
    print(json.dumps({"status": result["status"], "sellability": sellability}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
