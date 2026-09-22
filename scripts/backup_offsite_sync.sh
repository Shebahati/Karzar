#!/usr/bin/env bash
# Offsite backup sync (OPS-02). Copies local DB/upload backups to an external destination.
#
# Required env (host secrets — never commit):
#   BACKUP_OFFSITE_URI   e.g. s3://bucket/karzar/  or  rsync://user@host:/path/  or  user@host:/path/
# Optional:
#   BACKUP_LOCAL_DIR          default: <repository>/backups
#   BACKUP_RETENTION_DAYS     default: 14 (LOCAL only; does NOT enforce remote retention)
#   BACKUP_OFFSITE_LOCK       default: /var/lock/karzar-backup-offsite.lock
#
# Local retention deletes aged files under BACKUP_LOCAL_DIR only.
# Offsite/remote retention is destination-side policy.
# For rsync destinations, this script uses --delete, so the remote tree mirrors the
# currently retained local set (remote history beyond local retention is removed).
#
# Encryption: transport/at-rest encryption depends on the destination (TLS for S3/SSH,
# bucket SSE, disk encryption, etc.). This script does not implement custom encryption.
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
LOCK_FILE="${BACKUP_OFFSITE_LOCK:-/var/lock/karzar-backup-offsite.lock}"
SUCCESS_MARKER="${LOCAL_DIR}/offsite-last-success.txt"
FAILURE_MARKER="${LOCAL_DIR}/offsite-last-failure.txt"

sanitize_offsite_destination() {
  # Minimal sanitizer: strip userinfo / query; never log credentials.
  local raw="${1:-}"
  local out="$raw"
  # Drop query string / fragment if present.
  out="${out%%\?*}"
  out="${out%%\#*}"
  if [[ "$out" == *"://"* ]]; then
    # scheme://user:pass@host/... → scheme://host/...
    out="$(printf '%s' "$out" | sed -E 's#(://)[^/@]+@#\1#')"
  elif [[ "$out" == *@*:* ]] || [[ "$out" == *@*/* ]]; then
    # user@host:path → host:path
    out="${out#*@}"
  fi
  printf '%s' "$out"
}

write_marker() {
  local path="$1"
  local status="$2"
  local summary="$3"
  mkdir -p "$(dirname "$path")"
  {
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "exit_status=${status}"
    echo "summary=${summary}"
  } >"$path"
}

record_failure() {
  local status="$1"
  local summary="$2"
  if [[ -d "$LOCAL_DIR" ]] || mkdir -p "$LOCAL_DIR" 2>/dev/null; then
    write_marker "$FAILURE_MARKER" "$status" "$summary"
  fi
}

if [[ -z "$URI" ]]; then
  echo "BACKUP_OFFSITE_URI is not set — refusing to pretend offsite backup succeeded." >&2
  echo "Configure S3/R2/rsync destination in host secrets (/opt/karzar/.deploy-secrets), then re-run." >&2
  record_failure 1 "BACKUP_OFFSITE_URI unset"
  exit 1
fi

if [[ ! -d "$LOCAL_DIR" ]]; then
  echo "Local backup dir missing: $LOCAL_DIR" >&2
  record_failure 1 "local backup dir missing"
  exit 1
fi

# Non-overlap guard (util-linux flock; present on current Ubuntu VPS bootstrap).
mkdir -p "$(dirname "$LOCK_FILE")" 2>/dev/null || true
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Offsite sync already running (lock: $LOCK_FILE)." >&2
  record_failure 1 "offsite sync lock busy"
  exit 1
fi

DEST_DESC="$(sanitize_offsite_destination "$URI")"
echo "Syncing $LOCAL_DIR → ${DEST_DESC}"

set +e
if [[ "$URI" == s3://* ]]; then
  aws s3 sync "$LOCAL_DIR" "$URI" --only-show-errors
  SYNC_RC=$?
elif [[ "$URI" == rsync://* ]] || [[ "$URI" == *:* ]]; then
  # --delete: remote tree mirrors currently retained local files (see header).
  rsync -az --delete "$LOCAL_DIR"/ "$URI"
  SYNC_RC=$?
else
  echo "Unsupported BACKUP_OFFSITE_URI scheme (sanitized): ${DEST_DESC}" >&2
  record_failure 1 "unsupported BACKUP_OFFSITE_URI scheme"
  exit 1
fi
set -e

if [[ "$SYNC_RC" -ne 0 ]]; then
  echo "Offsite sync failed (exit ${SYNC_RC})." >&2
  record_failure "$SYNC_RC" "sync command failed"
  exit "$SYNC_RC"
fi

# Local retention only — does NOT delete remote history beyond rsync --delete mirroring.
find "$LOCAL_DIR" -type f \
  ! -name 'offsite-last-success.txt' \
  ! -name 'offsite-last-failure.txt' \
  -mtime "+${RETENTION_DAYS}" -print -delete || true

write_marker "$SUCCESS_MARKER" 0 "offsite sync ok dest=${DEST_DESC}"
echo "Offsite sync OK."
echo "REMINDER: run a restore drill quarterly — see docs/OPERATIONS.md § Backup / restore."
echo "NOTE: BACKUP_RETENTION_DAYS applies to local files only; remote retention is destination-side."
