#!/usr/bin/env bash
# Restore uploads archive into the app data volume / host data/uploads.
# WARNING: overwrites existing files under uploads/.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 backups/karzar_uploads_YYYYMMDD_HHMMSS.tar.gz" >&2
  exit 1
fi

ARCHIVE="$1"
if [[ ! -f "$ARCHIVE" ]]; then
  echo "Archive not found: $ARCHIVE" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.yml}"

read -r -p "This will overwrite uploads. Continue? [y/N] " CONFIRM
if [[ "${CONFIRM,,}" != "y" ]]; then
  echo "Aborted."
  exit 1
fi

if docker compose -f "$COMPOSE_FILE" ps --status running 2>/dev/null | grep -qE 'lathe_|karzar_|app'; then
  SERVICE="${UPLOADS_BACKUP_SERVICE:-app}"
  # Extract into /app/data (creates /app/data/uploads)
  docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
    sh -c 'rm -rf /app/data/uploads && mkdir -p /app/data && tar -C /app/data -xzf -' < "$ARCHIVE"
else
  mkdir -p "$ROOT_DIR/data"
  rm -rf "$ROOT_DIR/data/uploads"
  tar -C "$ROOT_DIR/data" -xzf "$ARCHIVE"
fi

echo "Uploads restore completed from $ARCHIVE"
