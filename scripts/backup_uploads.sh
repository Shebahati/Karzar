#!/usr/bin/env bash
# Archive product/media uploads (Docker volume karzar_uploads → /app/data/uploads).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
mkdir -p "$BACKUP_DIR"

STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_FILE="$BACKUP_DIR/karzar_uploads_${STAMP}.tar.gz"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.yml}"

if docker compose -f "$COMPOSE_FILE" ps --status running 2>/dev/null | grep -qE 'lathe_|karzar_|app'; then
  # Prefer copying from the running app container (canonical path).
  SERVICE="${UPLOADS_BACKUP_SERVICE:-app}"
  docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
    tar -C /app/data -czf - uploads > "$OUT_FILE"
elif [[ -d "$ROOT_DIR/data/uploads" ]]; then
  tar -C "$ROOT_DIR/data" -czf "$OUT_FILE" uploads
else
  echo "No running app container and no $ROOT_DIR/data/uploads — nothing to back up." >&2
  exit 1
fi

echo "Uploads backup written to $OUT_FILE"
ls -lh "$OUT_FILE"
