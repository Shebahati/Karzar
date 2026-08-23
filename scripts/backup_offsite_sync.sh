#!/usr/bin/env bash
# Offsite backup sync (OPS-02). Copies local DB/upload backups to an external destination.
#
# Required env (set in cron / .deploy-secrets — never commit secrets):
#   BACKUP_OFFSITE_URI   e.g. s3://bucket/karzar/  or  rsync://user@host:/path/
# Optional:
#   BACKUP_LOCAL_DIR     default: <repository>/backups
#   BACKUP_RETENTION_DAYS default: 14 (local only; offsite retention is destination-side)
#
# Usage:
#   bash scripts/backup_offsite_sync.sh
#
# Prerequisites: aws CLI (for s3://) or rsync (for rsync:// / ssh paths).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_DIR="${BACKUP_LOCAL_DIR:-$ROOT_DIR/backups}"
URI="${BACKUP_OFFSITE_URI:-}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

if [[ -z "$URI" ]]; then
  echo "BACKUP_OFFSITE_URI is not set — refusing to pretend offsite backup succeeded." >&2
  echo "Configure S3/R2/rsync destination in server secrets, then re-run." >&2
  exit 1
fi

if [[ ! -d "$LOCAL_DIR" ]]; then
  echo "Local backup dir missing: $LOCAL_DIR" >&2
  exit 1
fi

echo "Syncing $LOCAL_DIR → $URI"

if [[ "$URI" == s3://* ]]; then
  aws s3 sync "$LOCAL_DIR" "$URI" --only-show-errors
elif [[ "$URI" == rsync://* ]] || [[ "$URI" == *:* ]]; then
  rsync -az --delete "$LOCAL_DIR"/ "$URI"
else
  echo "Unsupported BACKUP_OFFSITE_URI scheme: $URI" >&2
  exit 1
fi

# Local retention (offsite policy is separate)
find "$LOCAL_DIR" -type f -mtime "+${RETENTION_DAYS}" -print -delete || true

echo "Offsite sync OK."
echo "REMINDER: run a restore drill quarterly — see docs/OPERATIONS.md § Backup restore drill."
