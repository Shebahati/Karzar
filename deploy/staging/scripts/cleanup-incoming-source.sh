#!/usr/bin/env bash
# Delete /opt/karzar/incoming/<github.sha> as SSH_USER after a successful deploy.
# Runs on GitHub-hosted ubuntu-latest. Streams the local delete over IPv4 SSH.
# Never writes live /opt/karzar/{Karzar,frontend}. Never logs key material.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

KARZAR_INCOMING_BASE="${KARZAR_INCOMING_BASE:-/opt/karzar/incoming}"

karzar_resolve_incoming_target() {
  local sha="${1:-}"
  local base="${KARZAR_INCOMING_BASE:-/opt/karzar/incoming}"

  KARZAR_CLEANUP_BASE=""
  KARZAR_CLEANUP_TARGET=""

  if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
    echo "CLEANUP=FAIL invalid sha" >&2
    return 1
  fi
  if [[ "$base" != /* ]]; then
    echo "CLEANUP=FAIL incoming base must be absolute" >&2
    return 1
  fi
  case "$base" in
    *..*)
      echo "CLEANUP=FAIL incoming base contains .." >&2
      return 1
      ;;
  esac

  local target="${base}/${sha}"
  if [[ "$target" != "${base}/"* ]]; then
    echo "CLEANUP=FAIL target escapes incoming base" >&2
    return 1
  fi
  if [[ "$target" == "$base" || "$target" == "/" ]]; then
    echo "CLEANUP=FAIL refused to delete incoming base" >&2
    return 1
  fi

  KARZAR_CLEANUP_BASE="$base"
  KARZAR_CLEANUP_TARGET="$target"
}

karzar_remove_incoming_path() {
  local path="$1"
  if [[ -n "${KARZAR_CLEANUP_RM:-}" ]]; then
    "$KARZAR_CLEANUP_RM" -- "$path"
  else
    rm -rf -- "$path"
  fi
}

# Local delete. Used on the VPS via SSH and in selftests via KARZAR_INCOMING_BASE.
karzar_cleanup_incoming_local() {
  local sha="${GITHUB_SHA:-}"
  karzar_resolve_incoming_target "$sha" || return 1
  local base="$KARZAR_CLEANUP_BASE"
  local target="$KARZAR_CLEANUP_TARGET"

  karzar_remove_incoming_path "$target"
  if [[ -e "$target" ]]; then
    echo "CLEANUP=FAIL target still exists" >&2
    return 1
  fi
  echo "CLEANUP_OK sha=${sha}"

  find "$base" \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -mtime +1 \
    -exec rm -rf -- {} + || echo "::warning::stale incoming cleanup failed"
}

karzar_cleanup_incoming_via_ssh() {
  : "${SSH_HOST:?SSH_HOST secret is required}"
  : "${SSH_USER:?SSH_USER secret is required}"
  : "${SSH_PRIVATE_KEY:?SSH_PRIVATE_KEY secret is required}"
  SSH_PORT="${SSH_PORT:-22}"

  local root known_hosts keyfile
  root="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
  known_hosts="${KNOWN_HOSTS_FILE:-$root/deploy/staging/ssh/known_hosts}"
  test -f "$known_hosts"
  if [[ ! -s "$known_hosts" ]]; then
    echo "known_hosts is empty" >&2
    exit 1
  fi

  keyfile="$(mktemp)"
  trap 'rm -f "$keyfile"' EXIT
  umask 077
  printf '%s\n' "$SSH_PRIVATE_KEY" > "$keyfile"
  if ! grep -q 'BEGIN .*PRIVATE KEY' "$keyfile"; then
    echo "SSH_PRIVATE_KEY does not look like a private key block" >&2
    exit 1
  fi
  chmod 600 "$keyfile"

  local ssh_base=(
    ssh -4
    -i "$keyfile"
    -p "$SSH_PORT"
    -o IdentitiesOnly=yes
    -o PreferredAuthentications=publickey
    -o PasswordAuthentication=no
    -o KbdInteractiveAuthentication=no
    -o UserKnownHostsFile="$known_hosts"
    -o StrictHostKeyChecking=yes
    -o BatchMode=yes
    -o ConnectTimeout=25
    -o ServerAliveInterval=10
    -o ServerAliveCountMax=3
  )

  {
    declare -f karzar_resolve_incoming_target
    declare -f karzar_remove_incoming_path
    declare -f karzar_cleanup_incoming_local
    printf 'set -euo pipefail\n'
    printf 'KARZAR_INCOMING_BASE=/opt/karzar/incoming\n'
    printf 'GITHUB_SHA=%q\n' "$GITHUB_SHA"
    printf 'karzar_cleanup_incoming_local\n'
  } | "${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" bash -s
}

if [[ "${1:-}" == --selftest ]]; then
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  FAIL=0
  pass() { echo "PASS: $*"; }
  fail() { echo "FAIL: $*" >&2; FAIL=1; }

  hex40() { printf '%040x' "$1"; }
  SHA_A="$(hex40 1)"
  SHA_B="$(hex40 2)"
  BASE="$TMP/incoming"
  export KARZAR_INCOMING_BASE="$BASE"

  mkdir -p "$BASE/$SHA_A/tree" "$BASE/$SHA_B/tree"
  echo a > "$BASE/$SHA_A/tree/f"
  echo b > "$BASE/$SHA_B/tree/f"
  GITHUB_SHA="$SHA_A" karzar_cleanup_incoming_local
  if [[ -e "$BASE/$SHA_A" ]]; then
    fail "EXACT_SHA_CLEANUP target remains"
  else
    pass "EXACT_SHA_CLEANUP"
  fi

  preserve="$TMP/preserve"
  mkdir -p "$preserve/keep" "$BASE/$SHA_B"
  echo stay > "$preserve/keep/x"
  PRESERVE_HASH="$(sha256sum "$preserve/keep/x")"
  for bad in abc ../x / '' AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA \
             aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; do
    if GITHUB_SHA="$bad" karzar_cleanup_incoming_local 2>/dev/null; then
      fail "INVALID_SHA_REJECTED accepted: ${bad:-empty}"
    fi
    if [[ ! -f "$preserve/keep/x" ]] || [[ "$(sha256sum "$preserve/keep/x")" != "$PRESERVE_HASH" ]]; then
      fail "INVALID_SHA_REJECTED mutated preserve fixture"
    fi
    if [[ ! -d "$BASE/$SHA_B" ]]; then
      fail "INVALID_SHA_REJECTED deleted sibling"
    fi
  done
  pass "INVALID_SHA_REJECTED"

  if [[ ! -d "$BASE" ]]; then
    fail "BASE_PRESERVED incoming base deleted"
  else
    pass "BASE_PRESERVED"
  fi

  if [[ ! -d "$BASE/$SHA_B" ]]; then
    fail "SIBLING_PRESERVED sha-B deleted"
  else
    pass "SIBLING_PRESERVED"
  fi

  OUT="$TMP/outside"
  mkdir -p "$OUT/Karzar" "$OUT/frontend" "$OUT/backups" "$OUT/uploads"
  echo secret > "$OUT/.deploy-secrets"
  echo be > "$OUT/Karzar/app.py"
  echo fe > "$OUT/frontend/x"
  echo bak > "$OUT/backups/db.sql"
  echo up > "$OUT/uploads/f"
  chmod 0600 "$OUT/.deploy-secrets"
  OUT_HASH="$(sha256sum "$OUT/.deploy-secrets" "$OUT/Karzar/app.py" "$OUT/frontend/x" "$OUT/backups/db.sql" "$OUT/uploads/f")"
  OUT_MODE="$(stat -c '%a' "$OUT/.deploy-secrets")"
  SHA_C="$(hex40 3)"
  mkdir -p "$BASE/$SHA_C"
  GITHUB_SHA="$SHA_C" karzar_cleanup_incoming_local
  if [[ "$(sha256sum "$OUT/.deploy-secrets" "$OUT/Karzar/app.py" "$OUT/frontend/x" "$OUT/backups/db.sql" "$OUT/uploads/f")" != "$OUT_HASH" ]]; then
    fail "OUTSIDE_TREE_UNCHANGED content changed"
  elif [[ "$(stat -c '%a' "$OUT/.deploy-secrets")" != "$OUT_MODE" ]]; then
    fail "OUTSIDE_TREE_UNCHANGED mode changed"
  else
    pass "OUTSIDE_TREE_UNCHANGED"
  fi

  SHA_D="$(hex40 4)"
  mkdir -p "$BASE/$SHA_D/tree"
  echo stuck > "$BASE/$SHA_D/tree/f"
  KARZAR_CLEANUP_RM="$TMP/fail-rm"
  cat > "$KARZAR_CLEANUP_RM" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  chmod 0755 "$KARZAR_CLEANUP_RM"
  if GITHUB_SHA="$SHA_D" KARZAR_CLEANUP_RM="$KARZAR_CLEANUP_RM" karzar_cleanup_incoming_local 2>/dev/null; then
    fail "CURRENT_DELETE_FAILURE_PROPAGATES succeeded"
  elif [[ ! -d "$BASE/$SHA_D" ]]; then
    fail "CURRENT_DELETE_FAILURE_PROPAGATES deleted target despite rm failure"
  else
    pass "CURRENT_DELETE_FAILURE_PROPAGATES"
  fi
  unset KARZAR_CLEANUP_RM

  SHA_E="$(hex40 5)"
  SHA_STALE="$(hex40 6)"
  SHA_FRESH="$(hex40 7)"
  mkdir -p "$BASE/$SHA_E" "$BASE/$SHA_STALE/nested" "$BASE/$SHA_FRESH"
  echo stale > "$BASE/$SHA_STALE/nested/x"
  echo fresh > "$BASE/$SHA_FRESH/x"
  touch -d '2 days ago' "$BASE/$SHA_STALE"
  GITHUB_SHA="$SHA_E" karzar_cleanup_incoming_local
  if [[ -e "$BASE/$SHA_E" ]]; then
    fail "STALE_CLEANUP_BOUNDED current target remains"
  elif [[ -e "$BASE/$SHA_STALE" ]]; then
    fail "STALE_CLEANUP_BOUNDED stale child not removed"
  elif [[ ! -f "$BASE/$SHA_FRESH/x" ]]; then
    fail "STALE_CLEANUP_BOUNDED fresh sibling removed"
  else
    pass "STALE_CLEANUP_BOUNDED"
  fi

  WF="$(cd "${SCRIPT_DIR}/../../.." && pwd)/.github/workflows/deploy-staging.yml"
  PROD="$(awk 'BEGIN{p=1} /^if \[\[ "\$\{1:-\}" == --selftest \]\]/{p=0} p' "$0")"
  if printf '%s\n' "$PROD" | grep -E 'chmod[[:space:]]+-?R?[[:space:]]*777|chown[[:space:]].*/opt/karzar/(Karzar|frontend)'; then
    fail "NO_WORLD_WRITE found chmod 777 or live-tree chown in cleanup script"
  elif grep -E 'chmod[[:space:]]+-?R?[[:space:]]*777|chown[[:space:]].*/opt/karzar/(Karzar|frontend)' "$WF"; then
    fail "NO_WORLD_WRITE found chmod 777 or live-tree chown in workflow"
  else
    pass "NO_WORLD_WRITE"
  fi

  echo "ALL_CLEANUP_SELFTESTS_OK"
  exit "$FAIL"
fi

: "${GITHUB_SHA:?GITHUB_SHA is required}"
if [[ -n "${SSH_HOST:-}" ]]; then
  karzar_cleanup_incoming_via_ssh
else
  karzar_cleanup_incoming_local
fi
