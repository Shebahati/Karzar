#!/usr/bin/env bash
# Non-interactive restore of a gzipped dump into the staging db container.
# Usage (on VPS, from Karzar root):
#   bash deploy/staging/scripts/restore-db-staging.sh backups/karzar_catalog_XXXX.sql.gz
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

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "Missing .env" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.staging.yml)

echo "WARNING: This overwrites database '${POSTGRES_DB}'."
echo "Restoring from $DUMP_FILE ..."

# Drop connections and recreate schema for a clean import when possible.
"${COMPOSE[@]}" exec -T db \
  sh -c 'psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1' <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "${POSTGRES_DB}";
CREATE DATABASE "${POSTGRES_DB}" OWNER "${POSTGRES_USER}";
SQL

gunzip -c "$DUMP_FILE" | "${COMPOSE[@]}" exec -T db \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

echo "Restore done. Restarting API to re-check /ready ..."
"${COMPOSE[@]}" restart app
sleep 3
curl -sf http://127.0.0.1:8000/ready && echo && echo "OK"
