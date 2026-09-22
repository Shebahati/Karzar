#!/usr/bin/env bash
# Install daily DB + uploads + offsite backup cron on the VPS.
# Schedule (UTC):
#   03:15 DB dump
#   03:30 uploads archive
#   03:45 offsite sync (after both local jobs)
#
# Run from Karzar backend root:  sudo bash deploy/staging/scripts/install-backup-cron.sh
#
# Secrets: BACKUP_OFFSITE_URI must live in host secrets (preferred:
# /opt/karzar/.deploy-secrets), never in Git or in /etc/cron.d/karzar-backup.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DB_SCRIPT="$ROOT_DIR/scripts/backup_db.sh"
UPLOADS_SCRIPT="$ROOT_DIR/scripts/backup_uploads.sh"
OFFSITE_SCRIPT="$ROOT_DIR/scripts/backup_offsite_sync.sh"
CRON_FILE=/etc/cron.d/karzar-backup
DEPLOY_SECRETS_FILE=/opt/karzar/.deploy-secrets

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

for script in "$DB_SCRIPT" "$UPLOADS_SCRIPT" "$OFFSITE_SCRIPT"; do
  if [[ ! -r "$script" ]]; then
    echo "Missing or unreadable backup script: $script" >&2
    exit 1
  fi
done

# GitHub artifacts normalize file modes. Keep executable bits as defense in
# depth, but cron invokes the scripts through bash so a later deploy cannot
# silently break backups by restoring mode 0644.
chmod +x "$DB_SCRIPT" "$UPLOADS_SCRIPT" "$OFFSITE_SCRIPT"
mkdir -p "$ROOT_DIR/backups"

# Env load order for scheduled jobs:
#   1) repository .env (if present)
#   2) /opt/karzar/.deploy-secrets (if present; overrides)
# Missing .deploy-secrets does not fail install — offsite sync will fail closed
# at runtime until BACKUP_OFFSITE_URI is configured.
ENV_LOAD="set -a; [[ -f ./.env ]] && . ./.env; [[ -f ${DEPLOY_SECRETS_FILE} ]] && . ${DEPLOY_SECRETS_FILE}; set +a"

cat > "$CRON_FILE" <<EOF
# Karzar staging backups — DB 03:15, uploads 03:30, offsite 03:45 UTC
# Do NOT put BACKUP_OFFSITE_URI or cloud credentials in this file.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
15 3 * * * root cd "$ROOT_DIR" && ${ENV_LOAD} && BACKUP_DIR="$ROOT_DIR/backups" /bin/bash "$DB_SCRIPT" >> "$ROOT_DIR/backups/cron.log" 2>&1
30 3 * * * root cd "$ROOT_DIR" && ${ENV_LOAD} && BACKUP_DIR="$ROOT_DIR/backups" /bin/bash "$UPLOADS_SCRIPT" >> "$ROOT_DIR/backups/cron-uploads.log" 2>&1
45 3 * * * root cd "$ROOT_DIR" && ${ENV_LOAD} && BACKUP_LOCAL_DIR="$ROOT_DIR/backups" /bin/bash "$OFFSITE_SCRIPT" >> "$ROOT_DIR/backups/cron-offsite.log" 2>&1
EOF

chmod 644 "$CRON_FILE"

echo "Installed $CRON_FILE"
echo "Schedule (UTC):"
echo "  DB       03:15"
echo "  uploads  03:30"
echo "  offsite  03:45"
echo "Test DB:      cd $ROOT_DIR && bash scripts/backup_db.sh"
echo "Test uploads: cd $ROOT_DIR && bash scripts/backup_uploads.sh"
echo "Test offsite: cd $ROOT_DIR && bash scripts/backup_offsite_sync.sh"
echo "Health:       cd $ROOT_DIR && bash scripts/check_backup_health.sh"
echo "NOTE: BACKUP_OFFSITE_URI must be configured in host secrets"
echo "      (preferred: ${DEPLOY_SECRETS_FILE}; optional override after ./.env)."
echo "NOTE: Off-site DR is not active until a real sync succeeds and recovery is proven."
echo "NOTE: On-host ./backups alone is not disaster recovery."
