#!/usr/bin/env bash
# Package prebuilt frontend images and rsync to incoming/<sha>/frontend-images/ on VPS.
# Runs on GitHub-hosted ubuntu-latest. Does not log keys.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=frontend-image-lib.sh
source "${SCRIPT_DIR}/frontend-image-lib.sh"

if [[ "${1:-}" == --selftest ]]; then
  exec "${SCRIPT_DIR}/test-prebuilt-frontend-handoff.sh"
fi

: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${SSH_HOST:?SSH_HOST secret is required}"
: "${SSH_USER:?SSH_USER secret is required}"
: "${SSH_PRIVATE_KEY:?SSH_PRIVATE_KEY secret is required}"
SSH_PORT="${SSH_PORT:-22}"
RSYNC_TIMEOUT_SECONDS="${RSYNC_TIMEOUT_SECONDS:-1800}"
META_TIMEOUT_SECONDS="${META_TIMEOUT_SECONDS:-120}"

EXPECTED_SHA="${EXPECTED_SHA:-$GITHUB_SHA}"
if [[ "$EXPECTED_SHA" != "$GITHUB_SHA" ]]; then
  echo "EXPECTED_SHA mismatch" >&2
  exit 1
fi

SHOP_TAG="${SHOP_IMAGE:-$(karzar_frontend_shop_image_tag "$GITHUB_SHA")}"
ADMIN_TAG="${ADMIN_IMAGE:-$(karzar_frontend_admin_image_tag "$GITHUB_SHA")}"

ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
KNOWN_HOSTS="${KNOWN_HOSTS_FILE:-$ROOT/deploy/staging/ssh/known_hosts}"
test -f "$KNOWN_HOSTS" && [[ -s "$KNOWN_HOSTS" ]]

INCOMING="/opt/karzar/incoming/${GITHUB_SHA}"
REMOTE_DIR="${INCOMING}/${KARZAR_FRONTEND_IMAGES_SUBDIR}"

WORKDIR="$(mktemp -d)"
KEYFILE="$(mktemp)"
BUNDLE="${WORKDIR}/${KARZAR_FRONTEND_BUNDLE_NAME}"
CHECKSUM="${WORKDIR}/${KARZAR_FRONTEND_CHECKSUM_NAME}"
cleanup() {
  rm -f "$KEYFILE"
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

umask 077
printf '%s\n' "$SSH_PRIVATE_KEY" > "$KEYFILE"
grep -q 'BEGIN .*PRIVATE KEY' "$KEYFILE" || { echo "SSH_PRIVATE_KEY invalid" >&2; exit 1; }
chmod 600 "$KEYFILE"
umask 022

if [[ "${KARZAR_SKIP_DOCKER_SAVE:-}" != "1" ]]; then
  for ref in "$SHOP_TAG" "$ADMIN_TAG"; do
    docker image inspect "$ref" >/dev/null
    karzar_verify_image_revision "$ref" "$GITHUB_SHA"
  done
  docker save -o "$BUNDLE" "$SHOP_TAG" "$ADMIN_TAG"
  (cd "$WORKDIR" && sha256sum "${KARZAR_FRONTEND_BUNDLE_NAME}" > "${KARZAR_FRONTEND_CHECKSUM_NAME}")
  BUNDLE_SHA="$(awk '{print $1}' "$CHECKSUM")"
  [[ "$BUNDLE_SHA" =~ ^[0-9a-f]{64}$ ]]
else
  BUNDLE_SHA="${KARZAR_MOCK_BUNDLE_SHA:-0000000000000000000000000000000000000000000000000000000000000000}"
  echo "$BUNDLE_SHA  ${KARZAR_FRONTEND_BUNDLE_NAME}" > "$CHECKSUM"
  : > "$BUNDLE"
fi

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

ssh_cmd="$(karzar_build_ssh_cmd_string "$KEYFILE" "$SSH_PORT" "$KNOWN_HOSTS")"

echo "Preparing remote ${REMOTE_DIR}"
timeout --foreground "${META_TIMEOUT_SECONDS}s" \
  "${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" \
  "set -euo pipefail; mkdir -p '${REMOTE_DIR}'; rm -f '${REMOTE_DIR}/${KARZAR_FRONTEND_IMAGES_MARKER}'"

echo "Transferring frontend image bundle (timeout=${RSYNC_TIMEOUT_SECONDS}s)"
if ! timeout --foreground "${RSYNC_TIMEOUT_SECONDS}s" \
  rsync -a --partial \
  -e "$ssh_cmd" \
  "$BUNDLE" "$CHECKSUM" \
  "${SSH_USER}@${SSH_HOST}:${REMOTE_DIR}/"; then
  echo "VERIFY=FAIL frontend image rsync failed" >&2
  exit 124
fi

echo "Verifying bundle checksum on VPS before handoff marker"
timeout --foreground "${META_TIMEOUT_SECONDS}s" \
  "${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" bash -s <<REMOTE
set -euo pipefail
cd '${REMOTE_DIR}'
test -f '${KARZAR_FRONTEND_BUNDLE_NAME}'
test -f '${KARZAR_FRONTEND_CHECKSUM_NAME}'
sha256sum -c '${KARZAR_FRONTEND_CHECKSUM_NAME}'
REMOTE

if [[ "${KARZAR_SKIP_REMOTE_MARKER:-}" != "1" ]]; then
  timeout --foreground "${META_TIMEOUT_SECONDS}s" \
    "${ssh_base[@]}" "${SSH_USER}@${SSH_HOST}" bash -s <<REMOTE
set -euo pipefail
BUNDLE_SHA='${BUNDLE_SHA}'
cat > '${REMOTE_DIR}/${KARZAR_FRONTEND_IMAGES_MARKER}' <<EOF
sha=${GITHUB_SHA}
bundle_sha256=\${BUNDLE_SHA}
shop_image=${SHOP_TAG}
admin_image=${ADMIN_TAG}
transport=rsync-ssh-ipv4
EOF
chmod 644 '${REMOTE_DIR}/${KARZAR_FRONTEND_IMAGES_MARKER}'
REMOTE
fi

echo "FRONTEND_IMAGES_HANDOFF_OK sha=${GITHUB_SHA} bundle_sha256=${BUNDLE_SHA}"
