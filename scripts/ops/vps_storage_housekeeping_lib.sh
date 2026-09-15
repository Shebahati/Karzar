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
  if [[ -n "${KARZAR_HOUSEKEEPING_MOCK_DOCKER_PS:-}" ]]; then
    if ! tr ',' '\n' <<<"${KARZAR_HOUSEKEEPING_MOCK_DOCKER_PS}" | grep -qx 'lathe_api'; then
      vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL lathe_api container not running (mock)"
      return 1
    fi
    if ! tr ',' '\n' <<<"${KARZAR_HOUSEKEEPING_MOCK_DOCKER_PS}" | grep -qx 'lathe_postgres'; then
      vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL lathe_postgres container not running (mock)"
      return 1
    fi
  else
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'lathe_api'; then
      vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL lathe_api container not running"
      return 1
    fi
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'lathe_postgres'; then
      vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL lathe_postgres container not running"
      return 1
    fi
  fi
  local fs_type fs_size
  fs_type="$(df -PT / | awk 'NR==2 {print $2}')"
  fs_size="$(df -PT / | awk 'NR==2 {print $3}')"
  if [[ -z "$fs_type" || -z "$fs_size" ]]; then
    vsh_log "ERROR" "HOST_IDENTITY_GATE=FAIL cannot read root filesystem"
    return 1
  fi
  vsh_verbose "root_fs type=${fs_type} size=${fs_size}"
  vsh_log "INFO" "HOST_IDENTITY_GATE=PASS"
  return 0
}

# Match a process cmdline regex, excluding this shell and its parent (avoids pgrep self-match).
vsh_process_cmdline_matches() {
  local regex="$1"
  local self=$$ ppid=${PPID:-0} pid cmd
  local pid
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    [[ "$pid" == "$self" || "$pid" == "$ppid" ]] && continue
    cmd="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
    [[ -z "$cmd" ]] && continue
    if [[ "$cmd" =~ $regex ]]; then
      return 0
    fi
  done < <(pgrep -f "$regex" 2>/dev/null || true)
  return 1
}

vsh_active_build_or_deploy() {
  if [[ "${KARZAR_HOUSEKEEPING_MOCK_ACTIVE_BUILD:-}" == "1" ]]; then
    return 0
  fi
  if [[ "${KARZAR_HOUSEKEEPING_MOCK_ACTIVE_BUILD:-}" == "0" ]]; then
    return 1
  fi

  # Runner.Listener idle daemon must not block housekeeping.
  if vsh_process_cmdline_matches 'Runner\.Worker'; then
    return 0
  fi
  if vsh_process_cmdline_matches 'docker[[:space:]]+build([[:space:]]|$)'; then
    return 0
  fi
  if vsh_process_cmdline_matches 'docker[[:space:]]+buildx'; then
    return 0
  fi
  if vsh_process_cmdline_matches 'buildctl[[:space:]]'; then
    return 0
  fi
  if vsh_process_cmdline_matches 'deploy-backend\.sh'; then
    return 0
  fi
  if vsh_process_cmdline_matches 'deploy-frontend\.sh'; then
    return 0
  fi
  if vsh_process_cmdline_matches 'deploy-staging'; then
    return 0
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
  # Presence of --filter alone is insufficient; we require until/duration semantics.
  # Apply still fails closed if `docker builder prune --filter until=…` is rejected.
  docker builder prune --help 2>&1 | grep -qiE 'until|duration'
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
  # Sets BACKUP_SAFETY_GATE=PASS|FAIL (canonical filename UTC timestamp is authoritative).
  BACKUP_SAFETY_GATE="FAIL"
  local dir script_dir
  dir="$(vsh_backup_dir_canonical)" || {
    vsh_log "ERROR" "backup directory missing or not canonical"
    return 1
  }
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local gate_out
  if ! gate_out="$(python3 "${script_dir}/backup_safety.py" "$dir" 2>&1)"; then
    vsh_log "ERROR" "${gate_out}"
    return 1
  fi
  if grep -q 'BACKUP_SAFETY_GATE=PASS' <<<"$gate_out"; then
    BACKUP_SAFETY_GATE="PASS"
    return 0
  fi
  vsh_log "ERROR" "${gate_out}"
  return 1
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
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  printf '%s' "$json" | python3 "${script_dir}/backup_retention.py" \
    --backup-dir "$backup_dir" --apply-deletes
}
