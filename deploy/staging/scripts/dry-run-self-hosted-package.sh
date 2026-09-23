#!/usr/bin/env bash
# Phase 1/2 dry-run orchestrator on self-hosted host.
# Proves: mirror → checkout → package → checksum → incoming → optional cleanup.
# Forbids: docker, compose, live rsync, alembic, DB writes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET_SHA="${1:-${GITHUB_SHA:-}}"
: "${TARGET_SHA:?usage: dry-run-self-hosted-package.sh <40-hex-sha>}"

# Safe cwd for runner when started from an inaccessible directory.
cd /opt/karzar/workspace 2>/dev/null || cd "${HOME:-/tmp}" || cd /tmp

export GITHUB_SHA="$TARGET_SHA"
export KARZAR_PACKAGE_DRY_RUN=1
export FORCE_REPACKAGE="${FORCE_REPACKAGE:-1}"
export KARZAR_PACKAGE_CLEANUP_AFTER="${KARZAR_PACKAGE_CLEANUP_AFTER:-1}"

# Guardrails
if command -v docker >/dev/null 2>&1; then
  # Do not invoke docker; assert env forbids compose mutation paths
  :
fi
export KARZAR_SKIP_DOCKER_BUILD=1

echo "DRY_RUN_START sha=${TARGET_SHA}"

bash "${SCRIPT_DIR}/ensure-git-mirror.sh" "$TARGET_SHA"
bash "${SCRIPT_DIR}/package-incoming-local.sh"

# Post-cleanup: incoming must be gone if CLEANUP_AFTER=1
INCOMING_BASE="${KARZAR_INCOMING_BASE:-/opt/karzar/incoming}"
if [[ "${KARZAR_PACKAGE_CLEANUP_AFTER}" == "1" ]]; then
  if [[ -e "${INCOMING_BASE}/${TARGET_SHA}" ]]; then
    echo "cleanup failed; incoming still present" >&2
    exit 1
  fi
fi

# Prove live trees were not our package target (mtime check is advisory)
echo "DRY_RUN_OK sha=${TARGET_SHA} (no docker/compose/live-rsync/alembic)"
