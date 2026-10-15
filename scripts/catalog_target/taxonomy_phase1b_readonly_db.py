"""Read-only PostgreSQL access for taxonomy Phase 1B audits (SSH + lathe_postgres)."""

from __future__ import annotations

import re
import subprocess

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE)\b",
    re.I,
)

EXPECTED_PG_CONTAINER = "lathe_postgres"
EXPECTED_USER = "karzar_staging"
EXPECTED_DB = "karzar_staging"


def _escape_for_psql_c(sql: str) -> str:
    return sql.replace("\\", "\\\\").replace('"', '\\"')


def run_readonly_sql(ssh_host: str, sql: str) -> str:
    """Execute one or more read-only SQL statements inside a single READ ONLY transaction."""
    if FORBIDDEN_SQL.search(sql):
        raise RuntimeError(f"Refusing mutation-capable SQL: {sql[:160]}")
    body = sql.strip()
    if not body.upper().startswith("BEGIN"):
        body = f"BEGIN;\nSET TRANSACTION READ ONLY;\n{body}\nROLLBACK;"
    script = f"""set -euo pipefail
docker exec -i {EXPECTED_PG_CONTAINER} psql -U {EXPECTED_USER} -d {EXPECTED_DB} -v ON_ERROR_STOP=1 <<'EOSQL'
{body}
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
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "readonly_sql_failed")
    return proc.stdout.strip()


def run_readonly_scalar(ssh_host: str, select_sql: str) -> str:
    raw = run_readonly_sql(ssh_host, select_sql)
    lines = [line for line in raw.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def read_only_transaction_proof(ssh_host: str) -> dict[str, str]:
    out = run_readonly_sql(
        ssh_host,
        "SHOW transaction_read_only;\nSELECT current_setting('transaction_read_only');",
    )
    tro = "on" if "on" in out.lower() else "unknown"
    return {"transaction_read_only": tro, "enforcement": "explicit_begin_read_only_rollback"}
