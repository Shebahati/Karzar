#!/usr/bin/env bash
# Install daily DB + uploads backup cron on the VPS (03:15 / 03:30 UTC).
# Run from Karzar backend root:  sudo bash deploy/staging/scripts/install-backup-cron.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DB_SCRIPT="$ROOT_DIR/scripts/backup_db.sh"
UPLOADS_SCRIPT="$ROOT_DIR/scripts/backup_uploads.sh"
CRON_FILE=/etc/cron.d/karzar-backup

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

chmod +x "$DB_SCRIPT" "$UPLOADS_SCRIPT"
mkdir -p "$ROOT_DIR/backups"

cat > "$CRON_FILE" <<EOF
# Karzar staging backups — DB 03:15 UTC, uploads 03:30 UTC
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
15 3 * * * root cd "$ROOT_DIR" && set -a && . ./.env && set +a && BACKUP_DIR="$ROOT_DIR/backups" "$DB_SCRIPT" >> "$ROOT_DIR/backups/cron.log" 2>&1
30 3 * * * root cd "$ROOT_DIR" && set -a && . ./.env && set +a && BACKUP_DIR="$ROOT_DIR/backups" "$UPLOADS_SCRIPT" >> "$ROOT_DIR/backups/cron-uploads.log" 2>&1
EOF

chmod 644 "$CRON_FILE"

echo "Installed $CRON_FILE"
echo "Test DB:      cd $ROOT_DIR && ./scripts/backup_db.sh"
echo "Test uploads: cd $ROOT_DIR && ./scripts/backup_uploads.sh"
echo "NOTE: Copy ./backups/*.gz off-host (S3/object storage) — on-host alone is not DR."
