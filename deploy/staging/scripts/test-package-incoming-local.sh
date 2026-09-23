#!/usr/bin/env bash
# Local selftest for Phase 1 package-incoming-local (no VPS, no docker, no SSH).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Minimal fake mirror: use real repo as shared clone source via local bare
MIRROR="$TMP/mirror.git"
git clone --bare "$ROOT" "$MIRROR" >/dev/null
SHA="$(git -C "$ROOT" rev-parse HEAD)"

export KARZAR_ROOT="$TMP/karzar"
export KARZAR_MIRROR="$MIRROR"
export KARZAR_WORKSPACE="$TMP/karzar/workspace"
export KARZAR_INCOMING_BASE="$TMP/karzar/incoming"
export KARZAR_DEPLOY_LOG_DIR="$TMP/karzar/logs/deploy"
export KARZAR_PACKAGE_DRY_RUN=1
export FORCE_REPACKAGE=1
export KARZAR_PACKAGE_CLEANUP_AFTER=0
export GITHUB_SHA="$SHA"

mkdir -p "$KARZAR_INCOMING_BASE" "$KARZAR_WORKSPACE" "$KARZAR_DEPLOY_LOG_DIR"
# Simulate runner ownership constraints (non-root already)

bash "${SCRIPT_DIR}/package-incoming-local.sh"

test -f "${KARZAR_INCOMING_BASE}/${SHA}/HANDOFF_COMPLETE"
test -f "${KARZAR_INCOMING_BASE}/${SHA}/deploy-manifest.sha256"
grep -q 'transport=local-package' "${KARZAR_INCOMING_BASE}/${SHA}/HANDOFF_COMPLETE"
test -f "${KARZAR_INCOMING_BASE}/${SHA}/frontend-images/DRY_RUN_SKIPPED"

# consume verify
HANDOFF_VERIFY_MODE=consume \
  GITHUB_SHA="$SHA" EXPECTED_SHA="$SHA" \
  INCOMING_DIR="${KARZAR_INCOMING_BASE}/${SHA}" \
  bash "${SCRIPT_DIR}/verify-incoming-source.sh"

# cleanup simulation
export KARZAR_PACKAGE_CLEANUP_AFTER=1
# re-package then cleanup via dry-run helper pieces
FORCE_REPACKAGE=1 KARZAR_PACKAGE_CLEANUP_AFTER=1 \
  bash "${SCRIPT_DIR}/package-incoming-local.sh"
test ! -e "${KARZAR_INCOMING_BASE}/${SHA}"

echo "SELFTEST_OK package-incoming-local sha=${SHA}"
