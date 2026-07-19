#!/usr/bin/env bash
# Export local/dev Postgres for staging restore.
# Run on your laptop (where the filled catalog lives), then scp the dump to the VPS.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="${OUT_DIR:-$ROOT_DIR/backups}"
mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_FILE="$OUT_DIR/karzar_catalog_${STAMP}.sql.gz"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

bash "$ROOT_DIR/scripts/backup_db.sh"
# Copy newest dump to a stable name for scp
NEWEST="$(ls -1t "$OUT_DIR"/karzar_*.sql.gz | head -1)"
cp -f "$NEWEST" "$OUT_FILE"
echo "Catalog export ready: $OUT_FILE"
echo "On VPS: scp this file, then:"
echo "  gunzip -c $OUT_FILE | docker compose exec -T db psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\""
