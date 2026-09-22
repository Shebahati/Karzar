#!/usr/bin/env bash
# Read-only backup health checker for local + offsite evidence.
#
# Checks (default max age 24h, override with BACKUP_MAX_AGE_HOURS):
#   - recent DB dump:    backups/karzar_YYYYMMDD_HHMMSS.sql.gz
#   - recent uploads:    backups/karzar_uploads_YYYYMMDD_HHMMSS.tar.gz
#   - offsite-last-success.txt exists and is fresh
#   - offsite-last-failure.txt is not newer than success
#
# Exit 0 = healthy, non-zero = unhealthy.
# No network mutation. Suitable for an external uptime/cron monitor later.
#
# EXTERNAL_ALERTING = NOT IMPLEMENTED in-repo (no Telegram/Slack/email provider).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_DIR="${BACKUP_LOCAL_DIR:-$ROOT_DIR/backups}"
MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-24}"
SUCCESS_MARKER="${LOCAL_DIR}/offsite-last-success.txt"
FAILURE_MARKER="${LOCAL_DIR}/offsite-last-failure.txt"

fail() {
  echo "BACKUP_HEALTH_UNHEALTHY: $*" >&2
  exit 1
}

if [[ ! -d "$LOCAL_DIR" ]]; then
  fail "backup dir missing: $LOCAL_DIR"
fi

# BusyBox/GNU compatible: find files newer than MAX_AGE_HOURS.
max_age_minutes=$((MAX_AGE_HOURS * 60))
if [[ "$max_age_minutes" -lt 1 ]]; then
  fail "BACKUP_MAX_AGE_HOURS must be >= 1"
fi

db_count="$(find "$LOCAL_DIR" -maxdepth 1 -type f -name 'karzar_*.sql.gz' ! -name 'karzar_uploads_*' -mmin "-${max_age_minutes}" | wc -l | tr -d ' ')"
uploads_count="$(find "$LOCAL_DIR" -maxdepth 1 -type f -name 'karzar_uploads_*.tar.gz' -mmin "-${max_age_minutes}" | wc -l | tr -d ' ')"

if [[ "$db_count" -lt 1 ]]; then
  fail "no recent DB backup (karzar_*.sql.gz) within ${MAX_AGE_HOURS}h under ${LOCAL_DIR}"
fi
if [[ "$uploads_count" -lt 1 ]]; then
  fail "no recent uploads backup (karzar_uploads_*.tar.gz) within ${MAX_AGE_HOURS}h under ${LOCAL_DIR}"
fi

if [[ ! -f "$SUCCESS_MARKER" ]]; then
  fail "missing offsite success marker: $SUCCESS_MARKER"
fi

success_age_min="$(find "$SUCCESS_MARKER" -mmin "+${max_age_minutes}" -print | wc -l | tr -d ' ')"
if [[ "$success_age_min" -ge 1 ]]; then
  fail "offsite success marker older than ${MAX_AGE_HOURS}h"
fi

if [[ -f "$FAILURE_MARKER" ]]; then
  # If failure marker is newer than success, report unhealthy.
  if [[ "$FAILURE_MARKER" -nt "$SUCCESS_MARKER" ]]; then
    fail "offsite failure marker newer than success marker"
  fi
fi

echo "BACKUP_HEALTH_OK: db=${db_count} uploads=${uploads_count} max_age_h=${MAX_AGE_HOURS}"
exit 0
