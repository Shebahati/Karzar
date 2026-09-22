#!/usr/bin/env bash
# Offsite backup sync (OPS-02). Copies local DB/upload backups to an external destination.
#
# Required env (host secrets — never commit):
#   BACKUP_OFFSITE_URI   e.g. s3://bucket/karzar/  or  rsync://user@host:/path/  or  user@host:/path/
# Optional (S3 / S3-compatible):
#   BACKUP_S3_ENDPOINT_URL    https://… endpoint (required for most non-AWS S3-compatible providers)
#   BACKUP_S3_REGION          sets AWS_DEFAULT_REGION for the aws invocation only
# Credentials: standard AWS CLI mechanisms (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, profile, etc.)
# Optional:
#   BACKUP_LOCAL_DIR          default: <repository>/backups
#   BACKUP_RETENTION_DAYS     default: 14 (LOCAL only; does NOT enforce remote retention)
#   BACKUP_OFFSITE_LOCK       default: /var/lock/karzar-backup-offsite.lock
#
# Local retention deletes aged files under BACKUP_LOCAL_DIR only.
# Offsite/remote retention, at-rest encryption, and Object Lock/immutability are
# destination-side policy — this script never mutates bucket lifecycle settings.
# For rsync destinations, this script uses --delete, so the remote tree mirrors the
# currently retained local set (remote history beyond local retention is removed).
# Note: rsync --delete runs before local retention deletion in the same run, so a
# file deleted locally by that retention pass may remain remotely until the next
# successful sync.
#
# Encryption: transport/at-rest encryption depends on the destination (TLS for S3/SSH,
# bucket SSE, disk encryption, etc.). This script does not implement custom encryption.
#
# Usage:
#   bash scripts/backup_offsite_sync.sh
#   bash scripts/backup_offsite_sync.sh --preflight   # non-mutating config / head-bucket probe
#
# Prerequisites: aws CLI (for s3://) or rsync (for rsync:// / ssh paths).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_DIR="${BACKUP_LOCAL_DIR:-$ROOT_DIR/backups}"
URI="${BACKUP_OFFSITE_URI:-}"
S3_ENDPOINT="${BACKUP_S3_ENDPOINT_URL:-}"
S3_REGION="${BACKUP_S3_REGION:-}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
LOCK_FILE="${BACKUP_OFFSITE_LOCK:-/var/lock/karzar-backup-offsite.lock}"
SUCCESS_MARKER="${LOCAL_DIR}/offsite-last-success.txt"
FAILURE_MARKER="${LOCAL_DIR}/offsite-last-failure.txt"
PREFLIGHT=0

for arg in "$@"; do
  case "$arg" in
    --preflight) PREFLIGHT=1 ;;
    -h|--help)
      sed -n '1,35p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg (supported: --preflight)" >&2
      exit 1
      ;;
  esac
done

sanitize_offsite_destination() {
  # Minimal sanitizer: strip userinfo / query / fragment; never log credentials.
  local raw="${1:-}"
  local out="$raw"
  out="${out%%\?*}"
  out="${out%%\#*}"
  if [[ "$out" == *"://"* ]]; then
    out="$(printf '%s' "$out" | sed -E 's#(://)[^/@]+@#\1#')"
  elif [[ "$out" == *@*:* ]] || [[ "$out" == *@*/* ]]; then
    out="${out#*@}"
  fi
  printf '%s' "$out"
}

sanitize_endpoint_for_log() {
  # Prefer scheme://host only (no userinfo, query, path secrets).
  local raw="${1:-}"
  local cleaned
  cleaned="$(sanitize_offsite_destination "$raw")"
  if [[ "$cleaned" == https://* ]]; then
    local rest="${cleaned#https://}"
    printf 'https://%s' "${rest%%/*}"
  elif [[ "$cleaned" == http://* ]]; then
    local rest="${cleaned#http://}"
    printf 'http://%s' "${rest%%/*}"
  else
    printf '%s' "$cleaned"
  fi
}

extract_s3_bucket() {
  local uri="$1"
  local rest="${uri#s3://}"
  rest="${rest%%\?*}"
  rest="${rest%%\#*}"
  if [[ "$rest" == *@* ]]; then
    rest="${rest#*@}"
  fi
  local bucket="${rest%%/*}"
  if [[ -z "$bucket" ]]; then
    return 1
  fi
  printf '%s' "$bucket"
}

validate_s3_endpoint_url() {
  local ep="$1"
  if [[ -z "$ep" ]]; then
    return 0
  fi
  if [[ "$ep" == http://* ]]; then
    echo "BACKUP_S3_ENDPOINT_URL must use https:// (http:// refused for offsite)." >&2
    return 1
  fi
  if [[ "$ep" != https://* ]]; then
    echo "BACKUP_S3_ENDPOINT_URL must be an https:// URL." >&2
    return 1
  fi
  local host
  host="$(sanitize_endpoint_for_log "$ep")"
  host="${host#https://}"
  if [[ -z "$host" || "$host" == *" "* ]]; then
    echo "BACKUP_S3_ENDPOINT_URL host is missing or malformed." >&2
    return 1
  fi
  return 0
}

write_marker() {
  local path="$1"
  local status="$2"
  local summary="$3"
  shift 3 || true
  mkdir -p "$(dirname "$path")"
  {
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "exit_status=${status}"
    echo "summary=${summary}"
    # Extra non-secret metadata lines (optional).
    local extra
    for extra in "$@"; do
      printf '%s\n' "$extra"
    done
  } >"$path"
}

record_failure() {
  local status="$1"
  local summary="$2"
  shift 2 || true
  if [[ -d "$LOCAL_DIR" ]] || mkdir -p "$LOCAL_DIR" 2>/dev/null; then
    write_marker "$FAILURE_MARKER" "$status" "$summary" "$@"
  fi
}

require_aws_cli() {
  if ! command -v aws >/dev/null 2>&1; then
    echo "Offsite S3 sync refused: aws CLI not installed" >&2
    return 1
  fi
  return 0
}

run_aws() {
  # Invoke aws with optional per-call region; never print credentials.
  local -a cmd=("aws")
  cmd+=("$@")
  if [[ -n "$S3_REGION" ]]; then
    AWS_DEFAULT_REGION="$S3_REGION" "${cmd[@]}"
  else
    "${cmd[@]}"
  fi
}

if [[ -z "$URI" ]]; then
  echo "BACKUP_OFFSITE_URI is not set — refusing to pretend offsite backup succeeded." >&2
  echo "Configure S3/S3-compatible/rsync destination in host secrets (/opt/karzar/.deploy-secrets), then re-run." >&2
  record_failure 1 "BACKUP_OFFSITE_URI unset"
  exit 1
fi

if [[ "$PREFLIGHT" -eq 0 && ! -d "$LOCAL_DIR" ]]; then
  echo "Local backup dir missing: $LOCAL_DIR" >&2
  record_failure 1 "local backup dir missing"
  exit 1
fi

DEST_DESC="$(sanitize_offsite_destination "$URI")"

if [[ "$PREFLIGHT" -eq 0 ]]; then
  # Non-overlap guard (util-linux flock; present on current Ubuntu VPS bootstrap).
  mkdir -p "$(dirname "$LOCK_FILE")" 2>/dev/null || true
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "Offsite sync already running (lock: $LOCK_FILE)." >&2
    record_failure 1 "offsite sync lock busy"
    exit 1
  fi
fi

# --- S3 / S3-compatible -------------------------------------------------------
if [[ "$URI" == s3://* ]]; then
  if ! require_aws_cli; then
    record_failure 1 "aws CLI not installed"
    exit 1
  fi

  if ! validate_s3_endpoint_url "$S3_ENDPOINT"; then
    record_failure 1 "invalid BACKUP_S3_ENDPOINT_URL"
    exit 1
  fi

  ENDPOINT_DESC="aws-default"
  if [[ -n "$S3_ENDPOINT" ]]; then
    ENDPOINT_DESC="$(sanitize_endpoint_for_log "$S3_ENDPOINT")"
    echo "S3 endpoint: ${ENDPOINT_DESC}"
  fi

  BUCKET="$(extract_s3_bucket "$URI" || true)"
  if [[ -z "$BUCKET" ]]; then
    echo "Malformed BACKUP_OFFSITE_URI: empty S3 bucket (sanitized: ${DEST_DESC})." >&2
    record_failure 1 "malformed s3 URI empty bucket"
    exit 1
  fi

  if [[ "$PREFLIGHT" -eq 1 ]]; then
    echo "Preflight S3: destination=${DEST_DESC} endpoint=${ENDPOINT_DESC} bucket=${BUCKET}"
    set +e
    if [[ -n "$S3_ENDPOINT" ]]; then
      run_aws s3api head-bucket --bucket "$BUCKET" --endpoint-url "$S3_ENDPOINT"
      PF_RC=$?
    else
      run_aws s3api head-bucket --bucket "$BUCKET"
      PF_RC=$?
    fi
    set -e
    if [[ "$PF_RC" -ne 0 ]]; then
      echo "Preflight head-bucket failed (exit ${PF_RC})." >&2
      record_failure "$PF_RC" "preflight head-bucket failed" \
        "destination_type=s3" \
        "destination=${DEST_DESC}" \
        "endpoint=${ENDPOINT_DESC}"
      exit "$PF_RC"
    fi
    echo "Preflight OK (non-mutating; no sync)."
    exit 0
  fi

  echo "Syncing $LOCAL_DIR → ${DEST_DESC}"
  set +e
  if [[ -n "$S3_ENDPOINT" ]]; then
    run_aws s3 sync "$LOCAL_DIR" "$URI" --endpoint-url "$S3_ENDPOINT" --only-show-errors
    SYNC_RC=$?
  else
    run_aws s3 sync "$LOCAL_DIR" "$URI" --only-show-errors
    SYNC_RC=$?
  fi
  set -e

  if [[ "$SYNC_RC" -ne 0 ]]; then
    echo "Offsite sync failed (exit ${SYNC_RC})." >&2
    record_failure "$SYNC_RC" "sync command failed" \
      "destination_type=s3" \
      "destination=${DEST_DESC}" \
      "endpoint=${ENDPOINT_DESC}"
    exit "$SYNC_RC"
  fi

  find "$LOCAL_DIR" -type f \
    ! -name 'offsite-last-success.txt' \
    ! -name 'offsite-last-failure.txt' \
    -mtime "+${RETENTION_DAYS}" -print -delete || true

  write_marker "$SUCCESS_MARKER" 0 "offsite sync ok" \
    "destination_type=s3" \
    "destination=${DEST_DESC}" \
    "endpoint=${ENDPOINT_DESC}"
  echo "Offsite sync OK."
  echo "REMINDER: run a restore drill quarterly — see docs/OPERATIONS.md § Backup / restore."
  echo "NOTE: BACKUP_RETENTION_DAYS applies to local files only; remote retention is destination-side."
  exit 0
fi

# --- rsync / SSH-style --------------------------------------------------------
if [[ "$URI" == rsync://* ]] || [[ "$URI" == *:* ]]; then
  if ! command -v rsync >/dev/null 2>&1; then
    echo "Offsite rsync sync refused: rsync not installed" >&2
    record_failure 1 "rsync not installed"
    exit 1
  fi

  if [[ "$PREFLIGHT" -eq 1 ]]; then
    echo "Preflight rsync/SSH: destination=${DEST_DESC}"
    if command -v ssh >/dev/null 2>&1; then
      echo "ssh: present"
    else
      echo "ssh: absent (may be required for SSH-style destinations)"
    fi
    echo "Preflight OK (local tooling only; no remote mutation)."
    exit 0
  fi

  echo "Syncing $LOCAL_DIR → ${DEST_DESC}"
  set +e
  # --delete: remote tree mirrors currently retained local files (see header).
  rsync -az --delete "$LOCAL_DIR"/ "$URI"
  SYNC_RC=$?
  set -e

  if [[ "$SYNC_RC" -ne 0 ]]; then
    echo "Offsite sync failed (exit ${SYNC_RC})." >&2
    record_failure "$SYNC_RC" "sync command failed" \
      "destination_type=rsync" \
      "destination=${DEST_DESC}"
    exit "$SYNC_RC"
  fi

  find "$LOCAL_DIR" -type f \
    ! -name 'offsite-last-success.txt' \
    ! -name 'offsite-last-failure.txt' \
    -mtime "+${RETENTION_DAYS}" -print -delete || true

  write_marker "$SUCCESS_MARKER" 0 "offsite sync ok" \
    "destination_type=rsync" \
    "destination=${DEST_DESC}"
  echo "Offsite sync OK."
  echo "REMINDER: run a restore drill quarterly — see docs/OPERATIONS.md § Backup / restore."
  echo "NOTE: BACKUP_RETENTION_DAYS applies to local files only; remote retention is destination-side."
  exit 0
fi

echo "Unsupported BACKUP_OFFSITE_URI scheme (sanitized): ${DEST_DESC}" >&2
record_failure 1 "unsupported BACKUP_OFFSITE_URI scheme"
exit 1
