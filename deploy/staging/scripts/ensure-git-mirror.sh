#!/usr/bin/env bash
# Ensure bare git mirror for self-hosted package (no live-tree checkout).
# Default remote is public HTTPS (no deploy key required for public repo).
# Does not write /opt/karzar/Karzar. Does not run docker/alembic.
set -euo pipefail

KARZAR_ROOT="${KARZAR_ROOT:-/opt/karzar}"
MIRROR="${KARZAR_MIRROR:-${KARZAR_ROOT}/mirror/Karzar.git}"
REMOTE_URL="${KARZAR_MIRROR_URL:-https://github.com/Shebahati/Karzar.git}"
REQUIRED_SHA="${1:-}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "refuse to run ensure-git-mirror.sh as root; run as github-runner" >&2
  exit 1
fi

mkdir -p "$(dirname "$MIRROR")"

if [[ ! -d "$MIRROR" ]]; then
  echo "Cloning bare mirror → ${MIRROR}"
  git clone --bare "$REMOTE_URL" "$MIRROR"
else
  echo "Fetching mirror updates → ${MIRROR}"
  git -C "$MIRROR" remote set-url origin "$REMOTE_URL"
  git -C "$MIRROR" fetch --prune origin '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*'
fi

# Ensure we can resolve objects by SHA
git -C "$MIRROR" rev-parse --verify --quiet HEAD >/dev/null
echo "MIRROR_HEAD=$(git -C "$MIRROR" rev-parse HEAD)"

if [[ -n "$REQUIRED_SHA" ]]; then
  if [[ ! "$REQUIRED_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "invalid REQUIRED_SHA" >&2
    exit 1
  fi
  if ! git -C "$MIRROR" cat-file -e "${REQUIRED_SHA}^{commit}" 2>/dev/null; then
    echo "REQUIRED_SHA not in mirror after fetch: ${REQUIRED_SHA}" >&2
    exit 1
  fi
  echo "MIRROR_HAS_SHA=${REQUIRED_SHA}"
fi

echo "MIRROR_OK path=${MIRROR}"
