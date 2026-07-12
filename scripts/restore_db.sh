#!/usr/bin/env bash
# Restore a gzipped SQL dump into the Karzar Postgres database.
# WARNING: overwrites existing data in the target database.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 backups/karzar_YYYYMMDD_HHMMSS.sql.gz" >&2
  exit 1
fi

DUMP_FILE="$1"
if [[ ! -f "$DUMP_FILE" ]]; then
  echo "Dump not found: $DUMP_FILE" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

read -r -p "This will overwrite the database. Continue? [y/N] " CONFIRM
if [[ "${CONFIRM,,}" != "y" ]]; then
  echo "Aborted."
  exit 1
fi

if docker compose -f "$ROOT_DIR/docker-compose.yml" ps --status running 2>/dev/null | grep -q lathe_postgres; then
  gunzip -c "$DUMP_FILE" | docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T db \
    sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
else
  : "${POSTGRES_USER:?Set POSTGRES_USER}"
  : "${POSTGRES_DB:?Set POSTGRES_DB}"
  HOST="${POSTGRES_SERVER:-127.0.0.1}"
  PORT="${POSTGRES_PORT:-5435}"
  gunzip -c "$DUMP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}" \
    psql -h "$HOST" -p "$PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"
fi

echo "Restore completed from $DUMP_FILE"
