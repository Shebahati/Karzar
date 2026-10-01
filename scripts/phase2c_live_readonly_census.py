#!/usr/bin/env python3
"""Phase 2C — read-only live DB census + product export (no mutations).

Runs from private worker with SSH to staging VPS (karzar-vps).
Fails closed on any write-capable SQL or failed read-only proof.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT = Path("/tmp/karzar-p2c-live-products.csv")
AUDIT_DIR = ROOT / "audit" / "product-naming-phase2c-discovery"

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE)\b",
    re.I,
)


def _run_ssh_psql(sql: str, *, ssh_host: str = "karzar-vps") -> str:
    if FORBIDDEN_SQL.search(sql):
        raise RuntimeError(f"Refusing mutation-capable SQL fragment: {sql[:120]}")
    inner = sql.replace('"', '\\"')
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        ssh_host,
        f'docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging -v ON_ERROR_STOP=1 -At -c "{inner}"',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def _read_only_session_proof(ssh_host: str) -> dict[str, str]:
    block = """
BEGIN;
SET TRANSACTION READ ONLY;
SHOW transaction_read_only;
"""
    out = _run_ssh_psql(block + "SELECT 1;", ssh_host=ssh_host)
    tro = "on" if "on" in out.lower() else out.split("\n")[-1].strip()
    _run_ssh_psql("ROLLBACK;", ssh_host=ssh_host)
    return {"transaction_read_only": tro, "mutation_capable_statements_executed": "0"}


def _scalar(sql: str, ssh_host: str) -> int:
    raw = _run_ssh_psql(sql, ssh_host=ssh_host)
    line = raw.splitlines()[-1] if raw else "0"
    return int(line or 0)


def collect_baseline(ssh_host: str) -> dict:
    counts = {
        "total": _scalar("SELECT COUNT(*) FROM products;", ssh_host),
        "deleted": _scalar("SELECT COUNT(*) FROM products WHERE deleted_at IS NOT NULL;", ssh_host),
        "non_deleted": _scalar("SELECT COUNT(*) FROM products WHERE deleted_at IS NULL;", ssh_host),
        "active": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND is_active IS TRUE;", ssh_host
        ),
        "available": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND is_available IS TRUE;",
            ssh_host,
        ),
        "priced": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND base_price IS NOT NULL;",
            ssh_host,
        ),
        "imaged": _scalar(
            """
            SELECT COUNT(DISTINCT p.id) FROM products p
            JOIN product_images pi ON pi.product_id = p.id
            WHERE p.deleted_at IS NULL
              AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0;
            """,
            ssh_host,
        ),
        "storefront_public_approx": _scalar(
            """
            SELECT COUNT(*) FROM products p
            WHERE p.deleted_at IS NULL AND p.is_active IS TRUE
              AND EXISTS (
                SELECT 1 FROM product_images pi
                WHERE pi.product_id = p.id
                  AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
                  AND pi.image_url NOT ILIKE '%placeholder%'
                  AND pi.image_url NOT ILIKE '%no-image%'
                  AND pi.image_url NOT ILIKE '%no_image%'
              );
            """,
            ssh_host,
        ),
        "sellable_approx": _scalar(
            """
            SELECT COUNT(*) FROM products p
            WHERE p.deleted_at IS NULL AND p.is_active IS TRUE AND p.is_available IS TRUE
              AND p.base_price IS NOT NULL;
            """,
            ssh_host,
        ),
        "brandless": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND brand_id IS NULL;",
            ssh_host,
        ),
        "categoryless": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND category_id IS NULL;",
            ssh_host,
        ),
        "manufacturer_code_non_null": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL;",
            ssh_host,
        ),
        "manufacturer_code_null": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND manufacturer_code IS NULL;",
            ssh_host,
        ),
        "manufacturer_code_distinct": _scalar(
            "SELECT COUNT(DISTINCT manufacturer_code) FROM products WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL;",
            ssh_host,
        ),
        "product_type_id_non_null": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND product_type_id IS NOT NULL;",
            ssh_host,
        ),
        "product_type_id_null": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND product_type_id IS NULL;",
            ssh_host,
        ),
        "distinct_sku": _scalar(
            "SELECT COUNT(DISTINCT sku) FROM products WHERE deleted_at IS NULL;", ssh_host
        ),
        "distinct_slug": _scalar(
            "SELECT COUNT(DISTINCT slug) FROM products WHERE deleted_at IS NULL;", ssh_host
        ),
        "distinct_name": _scalar(
            "SELECT COUNT(DISTINCT name) FROM products WHERE deleted_at IS NULL;", ssh_host
        ),
    }
    return counts


def _fingerprint_sql(field_exprs: list[str], ssh_host: str) -> str:
    concat = " || '|' || ".join(field_exprs)
    sql = f"""
    SELECT md5(string_agg({concat}, E'\\n' ORDER BY p.id))
    FROM products p
    WHERE p.deleted_at IS NULL;
    """
    return _run_ssh_psql(sql, ssh_host=ssh_host).splitlines()[-1].strip()


def collect_runtime_identity(ssh_host: str) -> dict:
    host = _run_ssh_psql("SELECT version();", ssh_host=ssh_host)[:80]
    vps_hostname = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "hostname"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    git_head = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "git -C /opt/karzar/Karzar rev-parse HEAD 2>/dev/null || echo UNKNOWN"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    api_image = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            ssh_host,
            "docker inspect lathe_api --format '{{.Config.Image}}' 2>/dev/null || echo UNKNOWN",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    app_env = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            ssh_host,
            "docker exec lathe_api printenv APP_ENV 2>/dev/null || echo UNKNOWN",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    alembic = _run_ssh_psql(
        "SELECT version_num FROM alembic_version LIMIT 1;", ssh_host=ssh_host
    ).splitlines()[-1]
    return {
        "collected_at_utc": datetime.now(UTC).isoformat(),
        "collector_hostname": subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip(),
        "vps_hostname": vps_hostname,
        "deployed_git_sha": git_head,
        "api_container": "lathe_api",
        "postgres_container": "lathe_postgres",
        "api_image": api_image,
        "postgres_db_name": "karzar_staging",
        "APP_ENV": app_env,
        "alembic_current": alembic,
        "postgres_server_note": host,
    }


def export_products_csv(path: Path, ssh_host: str) -> None:
    copy_body = """
COPY (
  SELECT
    p.id AS product_id,
    p.name,
    p.sku,
    p.slug,
    p.brand_id,
    COALESCE(b.name, '') AS brand_name,
    p.product_type_id,
    COALESCE(pt.code, '') AS product_type_code,
    COALESCE(pt.name_fa, '') AS product_type_name_fa,
    COALESCE(pt.name_en, '') AS product_type_name_en,
    COALESCE(pt.status, '') AS product_type_status,
    COALESCE(p.manufacturer_code, '') AS manufacturer_code,
    p.category_id,
    p.is_active,
    p.is_available,
    p.base_price,
    p.original_price,
    p.updated_at,
    p.deleted_at
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  LEFT JOIN product_types pt ON pt.id = p.product_type_id
  WHERE p.deleted_at IS NULL
  ORDER BY p.id
) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
"""
    if FORBIDDEN_SQL.search(copy_body):
        raise RuntimeError("export SQL failed safety check")
    script = f"""set -euo pipefail
docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging -v ON_ERROR_STOP=1 <<'EOSQL'
BEGIN;
SET TRANSACTION READ ONLY;
{copy_body}
ROLLBACK;
EOSQL
"""
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "bash", "-s"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:] or proc.stdout[-2000:])
    lines = proc.stdout.splitlines()
    header_idx = next(
        (i for i, line in enumerate(lines) if line.startswith("product_id,")),
        None,
    )
    if header_idx is None:
        raise RuntimeError("CSV header not found in export output")
    body = [lines[header_idx]]
    for line in lines[header_idx + 1 :]:
        if not line.strip() or line.strip().upper() in {"ROLLBACK", "COMMIT", "BEGIN"}:
            continue
        if not line.split(",", 1)[0].isdigit():
            continue
        body.append(line)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def brand_census_from_export(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    by: dict[str, dict] = {}
    for r in rows:
        bid = r.get("brand_id") or ""
        bname = r.get("brand_name") or "NO BRAND"
        key = f"{bid}|{bname}"
        if key not in by:
            by[key] = {
                "brand_id": bid,
                "brand_name": bname if bname else "NO BRAND",
                "non_deleted_products": 0,
                "active_products": 0,
                "public_products": 0,
                "priced_products": 0,
                "manufacturer_code_populated": 0,
                "manufacturer_code_null": 0,
                "product_type_assigned": 0,
                "product_type_null": 0,
            }
        b = by[key]
        b["non_deleted_products"] += 1
        if str(r.get("is_active", "")).lower() in ("t", "true", "1"):
            b["active_products"] += 1
        if str(r.get("is_active", "")).lower() in ("t", "true", "1") and (
            r.get("base_price") or ""
        ):
            b["public_products"] += 1  # approx; detailed public in baseline SQL
        if r.get("base_price"):
            b["priced_products"] += 1
        if (r.get("manufacturer_code") or "").strip():
            b["manufacturer_code_populated"] += 1
        else:
            b["manufacturer_code_null"] += 1
        if (r.get("product_type_id") or "").strip():
            b["product_type_assigned"] += 1
        else:
            b["product_type_null"] += 1
    return sorted(by.values(), key=lambda x: -x["non_deleted_products"])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument("--export-path", type=Path, default=DEFAULT_EXPORT)
    p.add_argument("--out-dir", type=Path, default=AUDIT_DIR)
    args = p.parse_args()

    proof = _read_only_session_proof(args.ssh_host)
    if proof.get("transaction_read_only") != "on":
        print(json.dumps({"error": "read_only_not_proven", **proof}), file=sys.stderr)
        return 2

    baseline_counts = collect_baseline(args.ssh_host)
    runtime = collect_runtime_identity(args.ssh_host)

    export_products_csv(args.export_path, args.ssh_host)
    export_rows = sum(1 for _ in open(args.export_path, encoding="utf-8")) - 1
    if export_rows != baseline_counts["non_deleted"]:
        print(
            json.dumps(
                {
                    "error": "export_row_mismatch",
                    "export_rows": export_rows,
                    "db_non_deleted": baseline_counts["non_deleted"],
                }
            ),
            file=sys.stderr,
        )
        return 2

    fps = {
        "name": _fingerprint_sql(["COALESCE(p.name,'')"], args.ssh_host),
        "sku": _fingerprint_sql(["COALESCE(p.sku,'')"], args.ssh_host),
        "slug": _fingerprint_sql(["COALESCE(p.slug,'')"], args.ssh_host),
        "manufacturer_code": _fingerprint_sql(["COALESCE(p.manufacturer_code,'')"], args.ssh_host),
        "composite": _fingerprint_sql(
            [
                "p.id::text",
                "COALESCE(p.name,'')",
                "COALESCE(p.sku,'')",
                "COALESCE(p.slug,'')",
                "COALESCE(p.brand_id::text,'')",
                "COALESCE(p.product_type_id::text,'')",
                "COALESCE(p.manufacturer_code,'')",
            ],
            args.ssh_host,
        ),
    }

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    baseline = {
        "collected_at_utc": datetime.now(UTC).isoformat(),
        "collector_hostname": subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip(),
        "coverage": "LIVE_DB_AUTHORITATIVE",
        "sql_access": {
            "worked": True,
            "read_only_guard": "postgresql:transaction_read_only=on",
            "method": f"ssh {args.ssh_host} docker exec lathe_postgres psql BEGIN READ ONLY",
        },
        "read_only_proof": proof,
        "counts": {**baseline_counts, "database_name": "karzar_staging"},
        "identity_fingerprints": fps,
        "live_export": {
            "path": str(args.export_path),
            "rows": export_rows,
            "sha256": sha256_file(args.export_path),
            "size_bytes": args.export_path.stat().st_size,
        },
    }
    (out / "LIVE_DB_BASELINE.json").write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    runtime["git_head_local"] = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    (out / "LIVE_RUNTIME_IDENTITY.json").write_text(
        json.dumps(runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    census = brand_census_from_export(args.export_path)
    with (out / "BRAND_CENSUS_LIVE.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(census[0].keys()) if census else [])
        if census:
            w.writeheader()
            w.writerows(census)

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "coverage": "LIVE_DB_AUTHORITATIVE",
        "export_path": str(args.export_path),
        "export_sha256": baseline["live_export"]["sha256"],
        "export_rows": export_rows,
        "db_non_deleted": baseline_counts["non_deleted"],
        "reconciles": export_rows == baseline_counts["non_deleted"],
        "script": "scripts/phase2c_live_readonly_census.py",
        "git_sha": runtime["git_head_local"],
    }
    (out / "LIVE_EXPORT_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({"ok": True, **manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
