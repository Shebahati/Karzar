# shellcheck shell=bash
# Shared helpers for vps_storage_housekeeping.sh (sourced, not executed directly).

vsh_log() {
  local level="$1"
  shift
  local msg="$*"
  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "${ts} [${level}] ${msg}"
}

vsh_verbose() {
  if [[ "${VSH_VERBOSE:-0}" == "1" ]]; then
    vsh_log "INFO" "$*"
  fi
}

vsh_disk_state() {
  local pct="$1"
  local warn="${KARZAR_DISK_WARNING_PERCENT:-65}"
  local crit="${KARZAR_DISK_CRITICAL_PERCENT:-80}"
  if (( pct < 50 )); then
    echo "NORMAL"
  elif (( pct >= crit )); then
    echo "CRITICAL"
  elif (( pct >= warn )); then
    echo "WARNING"
  else
    echo "NORMAL"
  fi
}

vsh_read_disk_stats() {
  # Sets DISK_TOTAL DISK_USED DISK_FREE DISK_PERCENT DISK_STATE
  local line
  line="$(df -P / | awk 'NR==2 {print $2" "$3" "$4" "$5}')"
  DISK_TOTAL_KB="$(echo "$line" | awk '{print $1}')"
  DISK_USED_KB="$(echo "$line" | awk '{print $2}')"
  DISK_FREE_KB="$(echo "$line" | awk '{print $3}')"
  DISK_PERCENT="$(echo "$line" | awk '{print $4}' | tr -d '%')"
  DISK_TOTAL="$(numfmt --to=iec-i --suffix=B "${DISK_TOTAL_KB}K" 2>/dev/null || echo "${DISK_TOTAL_KB}K")"
  DISK_USED="$(numfmt --to=iec-i --suffix=B "${DISK_USED_KB}K" 2>/dev/null || echo "${DISK_USED_KB}K")"
  DISK_FREE="$(numfmt --to=iec-i --suffix=B "${DISK_FREE_KB}K" 2>/dev/null || echo "${DISK_FREE_KB}K")"
  DISK_STATE="$(vsh_disk_state "$DISK_PERCENT")"
}

vsh_hostname() {
  if [[ -n "${KARZAR_HOUSEKEEPING_MOCK_HOSTNAME:-}" ]]; then
    echo "${KARZAR_HOUSEKEEPING_MOCK_HOSTNAME}"
  else
    hostname
  fi
}

vsh_verify_host_identity() {
  local expected="${KARZAR_EXPECTED_HOSTNAME:-srv5944957438}"
  local root="${KARZAR_ROOT:-/opt/karzar/Karzar}"
  local hn
  hn="$(vsh_hostname)"

  if [[ "$hn" != "$expected" ]]; then
    vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL unexpected hostname=${hn} expected=${expected}"
    return 1
  fi
  if [[ ! -d "$root" ]]; then
    vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL missing KARZAR_ROOT=${root}"
    return 1
  fi
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'lathe_api'; then
    vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL lathe_api container not running"
    return 1
  fi
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'lathe_postgres'; then
    vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL lathe_postgres container not running"
    return 1
  fi
  local fs_type fs_size
  fs_type="$(df -PT / | awk 'NR==2 {print $2}')"
  fs_size="$(df -PT / | awk 'NR==2 {print $3}')"
  if [[ -z "$fs_type" || -z "$fs_size" ]]; then
    vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL cannot read root filesystem"
    return 1
  fi
  vsh_verbose "root_fs type=${fs_type} size=${fs_size}"
  return 0
}

vsh_self_cmdline() {
  tr '\0' ' ' < "/proc/$$/cmdline" 2>/dev/null || echo "vps_storage_housekeeping"
}

vsh_active_build_or_deploy() {
  if [[ "${KARZAR_HOUSEKEEPING_MOCK_ACTIVE_BUILD:-}" == "1" ]]; then
    return 0
  fi
  if [[ "${KARZAR_HOUSEKEEPING_MOCK_ACTIVE_BUILD:-}" == "0" ]]; then
    return 1
  fi

  local self
  self="$(vsh_self_cmdline)"

  if pgrep -f 'Runner\.Worker' >/dev/null 2>&1; then
    return 0
  fi
  if pgrep -f '[/ ]docker build( |$)' >/dev/null 2>&1; then
    return 0
  fi
  if pgrep -f 'docker buildx' >/dev/null 2>&1; then
    return 0
  fi
  if pgrep -f 'buildctl ' >/dev/null 2>&1; then
    return 0
  fi
  if pgrep -f 'deploy-backend\.sh' >/dev/null 2>&1; then
    return 0
  fi
  if pgrep -f 'deploy-frontend\.sh' >/dev/null 2>&1; then
    return 0
  fi
  if pgrep -f 'deploy-staging' >/dev/null 2>&1; then
    # exclude this housekeeping script if path contains deploy-staging in self - unlikely
    if ! grep -q 'vps_storage_housekeeping' <<<"$self"; then
      return 0
    fi
  fi
  return 1
}

vsh_docker_builder_until_supported() {
  if [[ "${KARZAR_HOUSEKEEPING_MOCK_BUILDER_UNTIL:-}" == "1" ]]; then
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  docker builder prune --help 2>&1 | grep -q -- '--filter'
}

vsh_capture_build_cache_summary() {
  # Sets BUILD_CACHE_TOTAL BUILD_CACHE_RECLAIMABLE from docker system df
  BUILD_CACHE_TOTAL="unknown"
  BUILD_CACHE_RECLAIMABLE="unknown"
  local line
  line="$(docker system df 2>/dev/null | awk '/Build Cache/ {print $(NF-1), $NF}')"
  if [[ -n "$line" ]]; then
    BUILD_CACHE_TOTAL="$(echo "$line" | awk '{print $1}')"
    BUILD_CACHE_RECLAIMABLE="$(echo "$line" | awk '{print $2}')"
  fi
}

vsh_backup_dir_canonical() {
  local root="${KARZAR_ROOT:-/opt/karzar/Karzar}"
  local dir="${KARZAR_BACKUP_DIR:-$root/backups}"
  if [[ ! -d "$dir" ]]; then
    echo ""
    return 1
  fi
  readlink -f "$dir"
}

vsh_backup_safety_gate() {
  # Sets BACKUP_SAFETY_GATE=PASS|FAIL
  BACKUP_SAFETY_GATE="FAIL"
  local dir
  dir="$(vsh_backup_dir_canonical)" || {
    vsh_log "ERROR" "backup directory missing or not canonical"
    return 1
  }

  local -a db_files=()
  local f name mtime age_sec size
  while IFS= read -r -d '' f; do
    db_files+=("$f")
  done < <(find "$dir" -maxdepth 1 -type f -name 'karzar_*.sql.gz' ! -type l -print0 2>/dev/null)

  if ((${#db_files[@]} < 2)); then
    vsh_log "ERROR" "backup safety: fewer than 2 DB backups"
    return 1
  fi

  local latest=""
  local latest_mtime=0
  for f in "${db_files[@]}"; do
    name="$(basename "$f")"
    if [[ ! "$name" =~ ^karzar_[0-9]{8}_[0-9]{6}\.sql\.gz$ ]]; then
      continue
    fi
    mtime="$(stat -c %Y "$f")"
    if (( mtime > latest_mtime )); then
      latest_mtime=$mtime
      latest="$f"
    fi
  done

  if [[ -z "$latest" ]]; then
    vsh_log "ERROR" "backup safety: no canonical latest DB backup"
    return 1
  fi

  size="$(stat -c %s "$latest")"
  if (( size <= 0 )); then
    vsh_log "ERROR" "backup safety: latest DB backup zero bytes"
    return 1
  fi

  age_sec=$(( $(date +%s) - latest_mtime ))
  if (( age_sec > 36 * 3600 )); then
    vsh_log "ERROR" "backup safety: latest DB backup older than 36h (${age_sec}s)"
    return 1
  fi

  if ! gzip -t "$latest" 2>/dev/null; then
    vsh_log "ERROR" "backup safety: gzip integrity failed for latest DB backup"
    return 1
  fi

  BACKUP_SAFETY_GATE="PASS"
  return 0
}

vsh_print_retention_table() {
  local json="$1"
  python3 - "$json" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
print("TYPE | TIMESTAMP | SIZE | DECISION | REASON | PATH")
for row in sorted(payload["rows"], key=lambda r: r["path"]):
    print(
        f"{row['type']} | {row['timestamp']} | {row['size']} | "
        f"{row['decision']} | {row['reason']} | {row['path']}"
    )
for k, v in payload["summary"].items():
    print(f"{k}={v}")
PY
}

vsh_apply_retention_deletes() {
  local json="$1"
  local backup_dir="$2"
  python3 - "$json" "$backup_dir" <<'PY'
import json, os, sys
payload = json.loads(sys.argv[1])
backup_dir = os.path.realpath(sys.argv[2])
db_deleted = 0
upload_deleted = 0
bytes_reclaimed = 0
for row in payload["rows"]:
    if row["decision"] != "DELETE_CANDIDATE":
        continue
    path = os.path.realpath(row["path"])
    if not path.startswith(backup_dir + os.sep):
        raise SystemExit("path outside backup dir")
    if os.path.islink(path):
        raise SystemExit("refuse symlink delete")
    os.remove(path)
    bytes_reclaimed += int(row["size"])
    if row["type"] == "db":
        db_deleted += 1
    elif row["type"] == "upload":
        upload_deleted += 1
print(f"DB_BACKUPS_DELETED={db_deleted}")
print(f"UPLOAD_BACKUPS_DELETED={upload_deleted}")
print(f"BACKUP_BYTES_RECLAIMED={bytes_reclaimed}")
PY
}
