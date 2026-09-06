#!/usr/bin/env bash
# Pack the current checkout and push it to karzar-vps incoming/.
# Runs on GitHub-hosted ubuntu-latest. Does not log keys or the private key path contents.
set -euo pipefail

: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${SSH_HOST:?SSH_HOST secret is required}"
: "${SSH_USER:?SSH_USER secret is required}"
: "${SSH_PRIVATE_KEY:?SSH_PRIVATE_KEY secret is required}"
SSH_PORT="${SSH_PORT:-22}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
KNOWN_HOSTS="${KNOWN_HOSTS_FILE:-$ROOT/deploy/staging/ssh/known_hosts}"
test -f "$KNOWN_HOSTS"

if [[ ! -s "$KNOWN_HOSTS" ]]; then
  echo "known_hosts is empty" >&2
  exit 1
fi

DEST="/opt/karzar/incoming/${GITHUB_SHA}"
WORKDIR="$(mktemp -d)"
KEYFILE="$(mktemp)"
cleanup() {
  rm -f "$KEYFILE"
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

umask 077
printf '%s\n' "$SSH_PRIVATE_KEY" > "$KEYFILE"
if ! grep -q 'BEGIN .*PRIVATE KEY' "$KEYFILE"; then
  echo "SSH_PRIVATE_KEY does not look like a private key block" >&2
  exit 1
fi
chmod 600 "$KEYFILE"

echo "Packing source at $ROOT"
tar -C "$ROOT" -czf "$WORKDIR/src.tgz" \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  --exclude='.ruff_cache' \
  --exclude='backups' \
  --exclude='data/uploads' \
  --exclude='logs' \
  --exclude='actions-runner' \
  .
DIGEST="$(sha256sum "$WORKDIR/src.tgz" | awk '{print $1}')"
printf '%s  src.tgz\n' "$DIGEST" > "$WORKDIR/src.tgz.sha256"

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

echo "Pushing package to incoming (IPv4 SSH, host-key pinned)"
"${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" \
  "mkdir -p '$DEST' && chmod 755 /opt/karzar /opt/karzar/incoming '$DEST'"

scp -4 \
  -i "$KEYFILE" \
  -P "$SSH_PORT" \
  -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no \
  -o UserKnownHostsFile="$KNOWN_HOSTS" \
  -o StrictHostKeyChecking=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=25 \
  "$WORKDIR/src.tgz" "$WORKDIR/src.tgz.sha256" \
  "${SSH_USER}@${SSH_HOST}:${DEST}/"

"${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" \
  "cd '$DEST' && sha256sum -c src.tgz.sha256 && chmod 644 src.tgz src.tgz.sha256"

echo "PUSH_OK sha=${GITHUB_SHA} dest=${DEST} digest=${DIGEST}"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "digest=${DIGEST}" >> "$GITHUB_OUTPUT"
fi
