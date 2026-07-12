#!/usr/bin/env bash
# Create a gzipped SQL dump of the Karzar Postgres database.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
mkdir -p "$BACKUP_DIR"

STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_FILE="$BACKUP_DIR/karzar_${STAMP}.sql.gz"

# Prefer running inside the db container when available.
if docker compose -f "$ROOT_DIR/docker-compose.yml" ps --status running 2>/dev/null | grep -q lathe_postgres; then
  docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T db \
    sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$OUT_FILE"
else
  : "${POSTGRES_USER:?Set POSTGRES_USER}"
  : "${POSTGRES_DB:?Set POSTGRES_DB}"
  HOST="${POSTGRES_SERVER:-127.0.0.1}"
  PORT="${POSTGRES_PORT:-5435}"
  PGPASSWORD="${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}" \
    pg_dump -h "$HOST" -p "$PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$OUT_FILE"
fi

echo "Backup written to $OUT_FILE"
