"""Read-only PostgreSQL access for taxonomy Phase 1B audits (SSH + lathe_postgres)."""

from __future__ import annotations

import re
import subprocess

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE)\b",
    re.I,
)

TRANSACTION_BYPASS = re.compile(
    r"\b(BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE)\b|SET\s+TRANSACTION",
    re.I,
)

EXPECTED_PG_CONTAINER = "lathe_postgres"
EXPECTED_USER = "karzar_staging"
EXPECTED_DB = "karzar_staging"
EXPECTED_PG_SYSTEM_ID = "7664189378775347234"
EXPECTED_VPS_HOSTNAME = "srv5944957438"

_PSQL_META_LINE = re.compile(
    r"^(BEGIN|COMMIT|ROLLBACK|SET|SHOW|SELECT\s+\d+|rows?\)|\(\d+\s+rows?\))$",
    re.I,
)


def _assert_permitted_sql(sql: str) -> None:
    if FORBIDDEN_SQL.search(sql):
        raise RuntimeError(f"Refusing mutation-capable SQL: {sql[:160]}")
    if TRANSACTION_BYPASS.search(sql):
        raise RuntimeError("Refusing SQL that bypasses enforced READ ONLY transaction wrapping")


def _wrap_readonly_transaction(sql: str) -> str:
    body = sql.strip().rstrip(";")
    if not body:
        raise RuntimeError("empty_sql")
    return f"BEGIN;\nSET TRANSACTION READ ONLY;\n{body};\nROLLBACK;"


def _psql_preamble_pipe() -> str:
    return "\\pset format unaligned\n\\pset tuples_only on\n\\pset fieldsep '|'\n"


def _psql_preamble_scalar() -> str:
    return "\\pset format unaligned\n\\pset tuples_only on\n"


def _filter_psql_data_lines(raw: str) -> list[str]:
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper() in {"BEGIN", "COMMIT", "ROLLBACK"}:
            continue
        if stripped.startswith("SET TRANSACTION"):
            continue
        if _PSQL_META_LINE.match(stripped):
            continue
        lines.append(stripped)
    return lines


def _docker_psql_exec(ssh_host: str, heredoc_sql: str) -> subprocess.CompletedProcess[str]:
    script = f"""set -euo pipefail
docker exec -i {EXPECTED_PG_CONTAINER} psql -U {EXPECTED_USER} -d {EXPECTED_DB} -v ON_ERROR_STOP=1 -X -q <<'EOSQL'
{heredoc_sql}
EOSQL
"""
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "bash", "-s"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )


def run_readonly_sql(ssh_host: str, sql: str) -> str:
    """Execute read-only SQL with pipe-separated, tuples-only psql output."""
    _assert_permitted_sql(sql)
    body = _wrap_readonly_transaction(sql)
    heredoc = f"{_psql_preamble_pipe()}{body}"
    proc = _docker_psql_exec(ssh_host, heredoc)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "readonly_sql_failed")
    return "\n".join(_filter_psql_data_lines(proc.stdout))


def run_readonly_scalar(ssh_host: str, select_sql: str) -> str:
    """Return exactly one scalar cell from a single SELECT."""
    _assert_permitted_sql(select_sql)
    normalized = select_sql.strip().rstrip(";")
    if not re.match(r"^SELECT\b", normalized, re.I):
        raise RuntimeError("run_readonly_scalar requires a SELECT statement")
    body = _wrap_readonly_transaction(normalized)
    heredoc = f"{_psql_preamble_scalar()}{body}"
    proc = _docker_psql_exec(ssh_host, heredoc)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "readonly_scalar_failed")
    lines = _filter_psql_data_lines(proc.stdout)
    if len(lines) != 1:
        raise RuntimeError(
            f"expected_scalar_single_line got={len(lines)} sample={lines[:3]!r}"
        )
    return lines[0]


def parse_pipe_rows(raw: str, *, min_fields: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in _filter_psql_data_lines(raw):
        parts = line.split("|")
        if len(parts) < min_fields:
            continue
        rows.append(parts)
    return rows


def read_only_transaction_proof(ssh_host: str) -> dict[str, str]:
    value = run_readonly_scalar(
        ssh_host,
        "SELECT current_setting('transaction_read_only')",
    )
    normalized = value.strip().lower()
    if normalized != "on":
        raise RuntimeError(f"BLOCKED_READ_ONLY_PROOF expected=on got={value!r}")
    return {
        "transaction_read_only": "on",
        "enforcement": "explicit_begin_read_only_rollback_psql_tuples_only",
    }


def verify_production_database_identity(
    ssh_host: str,
    *,
    expected_db: str = EXPECTED_DB,
    expected_user: str = EXPECTED_USER,
    expected_system_id: str = EXPECTED_PG_SYSTEM_ID,
) -> dict[str, str]:
    db = run_readonly_scalar(ssh_host, "SELECT current_database()")
    user = run_readonly_scalar(ssh_host, "SELECT current_user")
    sys_id = run_readonly_scalar(
        ssh_host,
        "SELECT system_identifier::text FROM pg_control_system()",
    )
    if db != expected_db or user != expected_user:
        raise RuntimeError(
            f"BLOCKED_DATABASE_IDENTITY db={db!r} user={user!r}"
        )
    if sys_id != expected_system_id:
        raise RuntimeError(
            f"BLOCKED_PG_SYSTEM_ID expected={expected_system_id} got={sys_id!r}"
        )
    proof = read_only_transaction_proof(ssh_host)
    return {
        "current_database": db,
        "current_user": user,
        "pg_system_identifier": sys_id,
        **proof,
    }
