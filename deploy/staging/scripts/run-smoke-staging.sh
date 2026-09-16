#!/usr/bin/env bash
# Run post-deploy smoke; fail fast on non-zero exit (do not poll markers for an hour).
#
# Usage (from repo root on VPS):
#   API_BASE=... SHOP_BASE=... ADMIN_BASE=... bash deploy/staging/scripts/run-smoke-staging.sh
#
# Optional: SMOKE_LOG=/tmp/deploy-fe-smoke.log tees stdout/stderr for tailing.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

SMOKE_LOG="${SMOKE_LOG:-}"

run_smoke() {
  bash deploy/staging/scripts/smoke-staging.sh
}

if [[ -n "$SMOKE_LOG" ]]; then
  exec > >(tee -a "$SMOKE_LOG") 2>&1
fi

run_smoke
