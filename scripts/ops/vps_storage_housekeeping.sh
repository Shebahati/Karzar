#!/usr/bin/env bash
# Karzar VPS storage housekeeping: disk reporting, age-filtered BuildKit cache, backup retention.
# Default mode is dry-run. Destructive actions require --apply.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/ops/vps_storage_housekeeping_lib.sh
source "${SCRIPT_DIR}/vps_storage_housekeeping_lib.sh"

MODE="dry-run"
VSH_VERBOSE=0
VSH_LOCK_FD=200
VSH_LOCK_FILE="${KARZAR_HOUSEKEEPING_LOCK_FILE:-/run/lock/karzar-storage-housekeeping.lock}"

HOST_VERIFIED="NO"
LOCK_ACQUIRED="NO"
ACTIVE_BUILD_OR_DEPLOY="UNKNOWN"
BUILD_CACHE_RECLAIMED="0"
BACKUP_SAFETY_GATE="UNKNOWN"
DB_BACKUPS_DELETED=0
UPLOAD_BACKUPS_DELETED=0
BACKUP_BYTES_RECLAIMED=0
MANUAL_OPERATOR_INTERVENTION_REQUIRED="NO"
KARZAR_HOUSEKEEPING_RESULT="UNKNOWN"
BUILDKIT_CLEANUP="SKIPPED"
RETENTION_DELETE="SKIPPED"

usage() {
  cat <<'EOF'
Usage: vps_storage_housekeeping.sh [--dry-run] [--apply] [--verbose]

Default: --dry-run (no prune, no backup deletion).

Environment (optional):
  KARZAR_EXPECTED_HOSTNAME   (default: srv5944957438)
  KARZAR_ROOT                (default: /opt/karzar/Karzar)
  KARZAR_BACKUP_DIR          (default: $KARZAR_ROOT/backups)
  KARZAR_DISK_WARNING_PERCENT (default: 65)
  KARZAR_DISK_CRITICAL_PERCENT (default: 80)
  KARZAR_BUILDKIT_CACHE_UNTIL_HOURS (default: 168)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry-run"; shift ;;
    --apply) MODE="apply"; shift ;;
    --verbose) VSH_VERBOSE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

vsh_emit_summary() {
  cat <<EOF
KARZAR_HOUSEKEEPING_RESULT=${KARZAR_HOUSEKEEPING_RESULT}
MODE=${MODE}
HOST_VERIFIED=${HOST_VERIFIED}
LOCK_ACQUIRED=${LOCK_ACQUIRED}
ACTIVE_BUILD_OR_DEPLOY=${ACTIVE_BUILD_OR_DEPLOY}
DISK_BEFORE_PERCENT=${DISK_BEFORE_PERCENT:-}
DISK_AFTER_PERCENT=${DISK_AFTER_PERCENT:-}
DISK_STATE_BEFORE=${DISK_STATE_BEFORE:-}
DISK_STATE_AFTER=${DISK_STATE_AFTER:-}
BUILD_CACHE_BEFORE=${BUILD_CACHE_BEFORE:-}
BUILD_CACHE_RECLAIMABLE=${BUILD_CACHE_RECLAIMABLE:-}
BUILD_CACHE_RECLAIMED=${BUILD_CACHE_RECLAIMED}
BACKUP_SAFETY_GATE=${BACKUP_SAFETY_GATE}
DB_BACKUPS_DELETED=${DB_BACKUPS_DELETED}
UPLOAD_BACKUPS_DELETED=${UPLOAD_BACKUPS_DELETED}
BACKUP_BYTES_RECLAIMED=${BACKUP_BYTES_RECLAIMED}
MANUAL_OPERATOR_INTERVENTION_REQUIRED=${MANUAL_OPERATOR_INTERVENTION_REQUIRED}
EOF
}

on_exit() {
  local code=$?
  vsh_emit_summary
  exit "$code"
}
trap on_exit EXIT

vsh_log "INFO" "mode=${MODE} hostname=$(vsh_hostname)"

mkdir -p "$(dirname "$VSH_LOCK_FILE")"
exec {VSH_LOCK_FD}>"$VSH_LOCK_FILE"
if ! flock -n "$VSH_LOCK_FD"; then
  vsh_log "WARN" "HOUSEKEEPING_LOCK=BUSY"
  KARZAR_HOUSEKEEPING_RESULT="lock_busy"
  LOCK_ACQUIRED="NO"
  exit 0
fi
LOCK_ACQUIRED="YES"

if ! vsh_verify_host_identity; then
  vsh_log "ERROR" "HOUSEKEEPING_ABORTED"
  KARZAR_HOUSEKEEPING_RESULT="host_identity_fail"
  exit 10
fi
HOST_VERIFIED="YES"

vsh_read_disk_stats
DISK_BEFORE_PERCENT="$DISK_PERCENT"
DISK_STATE_BEFORE="$DISK_STATE"
vsh_log "INFO" "DISK_TOTAL=${DISK_TOTAL} DISK_USED=${DISK_USED} DISK_FREE=${DISK_FREE} DISK_PERCENT=${DISK_PERCENT} DISK_STATE=${DISK_STATE}"

if vsh_active_build_or_deploy; then
  ACTIVE_BUILD_OR_DEPLOY="YES"
  vsh_log "WARN" "ACTIVE_BUILD_OR_DEPLOY=YES"
  BUILDKIT_CLEANUP="SKIPPED"
  RETENTION_DELETE="SKIPPED"
else
  ACTIVE_BUILD_OR_DEPLOY="NO"
fi

vsh_capture_build_cache_summary
BUILD_CACHE_BEFORE="$BUILD_CACHE_TOTAL"
BUILD_CACHE_RECLAIMABLE="${BUILD_CACHE_RECLAIMABLE:-unknown}"

vsh_log "INFO" "=== BEFORE DOCKER DF ==="
docker system df 2>/dev/null || true
vsh_log "INFO" "=== BEFORE BUILDER DU ==="
docker builder du 2>/dev/null | tail -5 || true

# --- BuildKit cleanup (age-filtered only) ---
BUILDKIT_UNTIL_HOURS="${KARZAR_BUILDKIT_CACHE_UNTIL_HOURS:-168}"
if [[ "$ACTIVE_BUILD_OR_DEPLOY" == "YES" ]]; then
  vsh_log "WARN" "BUILDKIT_CLEANUP=SKIPPED active_build_or_deploy"
elif ! vsh_docker_builder_until_supported; then
  vsh_log "ERROR" "BUILDKIT_CLEANUP=UNSUPPORTED docker builder prune --filter until= not available"
  BUILDKIT_CLEANUP="UNSUPPORTED"
  if [[ "$MODE" == "apply" ]]; then
    KARZAR_HOUSEKEEPING_RESULT="builder_unsupported"
    exit 11
  fi
else
  if [[ "$MODE" == "dry-run" ]]; then
    vsh_log "INFO" "BUILDKIT_CLEANUP=DRY_RUN would run: docker builder prune -a -f --filter until=${BUILDKIT_UNTIL_HOURS}h"
    BUILDKIT_CLEANUP="DRY_RUN"
  else
    vsh_log "INFO" "BUILDKIT_CLEANUP=APPLY filter=until=${BUILDKIT_UNTIL_HOURS}h"
    prune_out="$(docker builder prune -a -f --filter "until=${BUILDKIT_UNTIL_HOURS}h" 2>&1)" || {
      vsh_log "ERROR" "BUILDKIT_CLEANUP=FAILED"
      KARZAR_HOUSEKEEPING_RESULT="builder_prune_failed"
      exit 12
    }
    echo "$prune_out"
    reclaimed_line="$(echo "$prune_out" | grep -E 'Total:|Total reclaimed space:' | tail -1 || true)"
    BUILD_CACHE_RECLAIMED="${reclaimed_line:-0}"
    BUILDKIT_CLEANUP="APPLIED"
  fi
fi

if [[ "$DISK_STATE_BEFORE" == "CRITICAL" && "$BUILDKIT_CLEANUP" != "APPLIED" ]]; then
  MANUAL_OPERATOR_INTERVENTION_REQUIRED="YES"
  vsh_log "WARN" "DISK_STATE=CRITICAL manual_operator_intervention_may_be_required"
fi

# --- Backup retention ---
backup_dir="$(vsh_backup_dir_canonical)" || backup_dir=""
retention_json=""
if [[ -n "$backup_dir" ]]; then
  retention_json="$(python3 "${SCRIPT_DIR}/backup_retention.py" --backup-dir "$backup_dir" --json 2>/dev/null || true)"
fi

if [[ -n "$retention_json" ]]; then
  vsh_log "INFO" "=== RETENTION PLAN ==="
  vsh_print_retention_table "$retention_json"
fi

if [[ "$ACTIVE_BUILD_OR_DEPLOY" == "YES" ]]; then
  BACKUP_SAFETY_GATE="SKIPPED"
elif ! vsh_backup_safety_gate; then
  BACKUP_SAFETY_GATE="FAIL"
  RETENTION_DELETE="SKIPPED"
  vsh_log "WARN" "RETENTION_DELETE=SKIPPED backup_safety_gate_fail"
else
  BACKUP_SAFETY_GATE="PASS"
  if [[ "$MODE" == "dry-run" ]]; then
    RETENTION_DELETE="DRY_RUN"
  elif [[ -n "$retention_json" ]]; then
    apply_out="$(vsh_apply_retention_deletes "$retention_json" "$backup_dir" 2>&1)" || {
      vsh_log "ERROR" "RETENTION_DELETE=FAILED"
      KARZAR_HOUSEKEEPING_RESULT="retention_delete_failed"
      exit 13
    }
    echo "$apply_out"
    RETENTION_DELETE="APPLIED"
    if [[ "$apply_out" =~ DB_BACKUPS_DELETED=([0-9]+) ]]; then
      DB_BACKUPS_DELETED="${BASH_REMATCH[1]}"
    fi
    if [[ "$apply_out" =~ UPLOAD_BACKUPS_DELETED=([0-9]+) ]]; then
      UPLOAD_BACKUPS_DELETED="${BASH_REMATCH[1]}"
    fi
    if [[ "$apply_out" =~ BACKUP_BYTES_RECLAIMED=([0-9]+) ]]; then
      BACKUP_BYTES_RECLAIMED="${BASH_REMATCH[1]}"
    fi
  fi
fi

vsh_read_disk_stats
DISK_AFTER_PERCENT="$DISK_PERCENT"
DISK_STATE_AFTER="$DISK_STATE"

vsh_log "INFO" "=== AFTER DF ==="
df -hT / 2>/dev/null || true
vsh_log "INFO" "=== AFTER DOCKER DF ==="
docker system df 2>/dev/null || true
vsh_log "INFO" "=== AFTER BUILDER DU ==="
docker builder du 2>/dev/null | tail -5 || true

if [[ "$DISK_STATE_AFTER" == "CRITICAL" ]]; then
  MANUAL_OPERATOR_INTERVENTION_REQUIRED="YES"
fi

KARZAR_HOUSEKEEPING_RESULT="success"
exit 0
