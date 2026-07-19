#!/usr/bin/env bash
# Install a daily Postgres backup cron on the VPS (03:15 UTC).
# Run from Karzar repo root:  sudo bash deploy/staging/scripts/install-backup-cron.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BACKUP_SCRIPT="$ROOT_DIR/scripts/backup_db.sh"
CRON_FILE=/etc/cron.d/karzar-backup

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

if [[ ! -x "$BACKUP_SCRIPT" ]]; then
  chmod +x "$BACKUP_SCRIPT"
fi

# Load DB credentials from project .env for host-side fallback path.
cat > "$CRON_FILE" <<EOF
# Karzar staging DB backup — daily 03:15 UTC
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
15 3 * * * root cd "$ROOT_DIR" && set -a && . ./.env && set +a && BACKUP_DIR="$ROOT_DIR/backups" "$BACKUP_SCRIPT" >> "$ROOT_DIR/backups/cron.log" 2>&1
EOF

chmod 644 "$CRON_FILE"
mkdir -p "$ROOT_DIR/backups"

echo "Installed $CRON_FILE"
echo "Test now: cd $ROOT_DIR && ./scripts/backup_db.sh"
