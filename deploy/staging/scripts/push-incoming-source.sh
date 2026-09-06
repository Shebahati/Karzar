#!/usr/bin/env bash
# Build an isolated deploy tree, seed incoming/<sha> from live (non-mutating),
# then delta-rsync over IPv4 SSH. Runs on GitHub-hosted ubuntu-latest.
# Does not log keys. Does not write live /opt/karzar/{Karzar,frontend}.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-tree-lib.sh
source "${SCRIPT_DIR}/deploy-tree-lib.sh"

if [[ "${1:-}" == --selftest ]]; then
  exec "${SCRIPT_DIR}/test-delta-rsync-handoff.sh"
fi

: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${SSH_HOST:?SSH_HOST secret is required}"
: "${SSH_USER:?SSH_USER secret is required}"
: "${SSH_PRIVATE_KEY:?SSH_PRIVATE_KEY secret is required}"
SSH_PORT="${SSH_PORT:-22}"
# Overall rsync bound. 900s matches the previous full-SCP cap (run 34036993174
# died at ~15m / exit 124). Delta of a ~75MB tree should finish far sooner;
# this is a hang guard, not a performance target.
RSYNC_TIMEOUT_SECONDS="${RSYNC_TIMEOUT_SECONDS:-900}"
META_TIMEOUT_SECONDS="${META_TIMEOUT_SECONDS:-60}"

EXPECTED_SHA="${EXPECTED_SHA:-$GITHUB_SHA}"
if [[ "$EXPECTED_SHA" != "$GITHUB_SHA" ]]; then
  echo "EXPECTED_SHA=${EXPECTED_SHA} does not match GITHUB_SHA=${GITHUB_SHA}" >&2
  exit 1
fi
echo "EXPECTED_SHA=${EXPECTED_SHA}"

ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
KNOWN_HOSTS="${KNOWN_HOSTS_FILE:-$ROOT/deploy/staging/ssh/known_hosts}"
test -f "$KNOWN_HOSTS"
if [[ ! -s "$KNOWN_HOSTS" ]]; then
  echo "known_hosts is empty" >&2
  exit 1
fi

DEST="/opt/karzar/incoming/${GITHUB_SHA}"
WORKDIR="$(mktemp -d)"
KEYFILE="$(mktemp)"
TREE="${DEPLOY_TREE_DIR:-${RUNNER_TEMP:-$WORKDIR}/deploy-tree}"
cleanup() {
  rm -f "$KEYFILE"
  rm -rf "$WORKDIR"
  if [[ "$TREE" == "$WORKDIR"/* ]] || { [[ -n "${RUNNER_TEMP:-}" ]] && [[ "$TREE" == "${RUNNER_TEMP}/"* ]]; }; then
    rm -rf "$TREE"
  fi
}
trap cleanup EXIT

umask 077
printf '%s\n' "$SSH_PRIVATE_KEY" > "$KEYFILE"
if ! grep -q 'BEGIN .*PRIVATE KEY' "$KEYFILE"; then
  echo "SSH_PRIVATE_KEY does not look like a private key block" >&2
  exit 1
fi
chmod 600 "$KEYFILE"
# umask 077 is only for the keyfile. The deploy-tree and deploy-manifest.sha256
# must not inherit 0600 — scp preserves that mode and the self-hosted runner
# may be a different Unix user than SSH_USER (run 34040385983).
umask 022

echo "Building isolated deploy tree (checkout left untouched)"
rm -rf "$TREE"
karzar_copy_tracked_deploy_tree "$ROOT" "$TREE"

MANIFEST="${WORKDIR}/${KARZAR_MANIFEST_NAME}"
karzar_write_deploy_manifest "$TREE" "$MANIFEST"
echo "DEPLOY_TREE files=${KARZAR_FILE_COUNT} bytes=${KARZAR_TOTAL_BYTES} manifest=${KARZAR_MANIFEST_SHA}"

ssh_base=(
  ssh -4
  -i "$KEYFILE"
  -p "$SSH_PORT"
  -o IdentitiesOnly=yes
  -o PreferredAuthentications=publickey
  -o PasswordAuthentication=no
  -o KbdInteractiveAuthentication=no
  -o UserKnownHostsFile="$KNOWN_HOSTS"
  -o StrictHostKeyChecking=yes
  -o BatchMode=yes
  -o ConnectTimeout=25
  -o ServerAliveInterval=10
  -o ServerAliveCountMax=3
)

ssh_cmd="ssh -4 -i ${KEYFILE} -p ${SSH_PORT} -o IdentitiesOnly=yes -o PreferredAuthentications=publickey -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o UserKnownHostsFile=${KNOWN_HOSTS} -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=25 -o ServerAliveInterval=10 -o ServerAliveCountMax=3"

echo "Seeding incoming tree from live source (incoming only; live not mutated)"
{
  declare -f karzar_backend_rsync_excludes
  declare -f karzar_frontend_rsync_excludes
  declare -f karzar_read_null_args
  declare -f karzar_prepare_incoming_dest
  declare -f karzar_seed_incoming_tree
  printf 'set -euo pipefail\n'
  printf 'KARZAR_PARTIAL_DIR=%q\n' "$KARZAR_PARTIAL_DIR"
  printf 'chmod 755 /opt/karzar /opt/karzar/incoming\n'
  printf 'karzar_prepare_incoming_dest %q\n' "$DEST"
  printf 'karzar_seed_incoming_tree /opt/karzar/Karzar /opt/karzar/frontend %q\n' "${DEST}/tree"
  printf 'chmod 755 /opt/karzar /opt/karzar/incoming %q\n' "$DEST"
} | "${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" bash -s

echo "Delta rsync deploy-tree → incoming/${GITHUB_SHA}/tree (timeout=${RSYNC_TIMEOUT_SECONDS}s, io-timeout=${KARZAR_RSYNC_IO_TIMEOUT}s)"
export KARZAR_RSYNC_RSH="$ssh_cmd"
if ! timeout --foreground "${RSYNC_TIMEOUT_SECONDS}s" \
    bash "${SCRIPT_DIR}/deploy-tree-lib.sh" rsync-delta \
    "$TREE" "${SSH_USER}@${SSH_HOST}:${DEST}/tree"; then
  echo "VERIFY=FAIL rsync transfer failed or timed out; live mutation skipped" >&2
  exit 124
fi

echo "Uploading integrity manifest"
timeout --foreground "${META_TIMEOUT_SECONDS}s" \
  "${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" \
  "rm -rf '${DEST}/tree/${KARZAR_PARTIAL_DIR}' && rm -f '${DEST}/${KARZAR_HANDOFF_MARKER}' && mkdir -p '$DEST'"

timeout --foreground "${META_TIMEOUT_SECONDS}s" \
  scp -4 \
  -i "$KEYFILE" \
  -P "$SSH_PORT" \
  -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no \
  -o KbdInteractiveAuthentication=no \
  -o UserKnownHostsFile="$KNOWN_HOSTS" \
  -o StrictHostKeyChecking=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=25 \
  -o ServerAliveInterval=10 \
  -o ServerAliveCountMax=3 \
  "$MANIFEST" \
  "${SSH_USER}@${SSH_HOST}:${DEST}/${KARZAR_MANIFEST_NAME}"

echo "Verifying staged tree against GitHub manifest (HANDOFF_COMPLETE not yet written)"
"${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" \
  env HANDOFF_VERIFY_MODE=prepare \
      GITHUB_SHA="$GITHUB_SHA" EXPECTED_SHA="$EXPECTED_SHA" \
      EXPECTED_MANIFEST_SHA="$KARZAR_MANIFEST_SHA" \
      INCOMING_DIR="$DEST" \
      bash "${DEST}/tree/deploy/staging/scripts/verify-incoming-source.sh"

echo "Normalizing incoming/${GITHUB_SHA} read/traverse permissions (incoming only)"
{
  declare -f karzar_normalize_incoming_permissions
  printf 'set -euo pipefail\n'
  printf 'KARZAR_MANIFEST_NAME=%q\n' "$KARZAR_MANIFEST_NAME"
  printf 'KARZAR_HANDOFF_MARKER=%q\n' "$KARZAR_HANDOFF_MARKER"
  printf 'karzar_normalize_incoming_permissions %q\n' "$DEST"
  printf 'stat -c %%A\\ %%a\\ %%n %q %q %q %q\n' \
    "$DEST" \
    "$DEST/tree" \
    "$DEST/${KARZAR_HANDOFF_MARKER}" \
    "$DEST/${KARZAR_MANIFEST_NAME}"
} | "${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" bash -s

echo "HANDOFF_OK sha=${GITHUB_SHA} transport=rsync-delta files=${KARZAR_FILE_COUNT} bytes=${KARZAR_TOTAL_BYTES}"
