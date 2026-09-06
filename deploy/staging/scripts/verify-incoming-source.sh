#!/usr/bin/env bash
# Verify a locally staged incoming tree against the GitHub-generated manifest.
# Runs on karzar-vps. Never fetches from GitHub or Azure. Never writes live trees.
#
# HANDOFF_VERIFY_MODE=prepare  — GitHub-hosted SSH session; EXPECTED_MANIFEST_SHA
#   is computed in the same package job (not a cross-job Actions output).
# HANDOFF_VERIFY_MODE=consume  — self-hosted; expected manifest SHA is read from
#   HANDOFF_COMPLETE only. EXPECTED_MANIFEST_SHA must not be required.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-tree-lib.sh
source "${SCRIPT_DIR}/deploy-tree-lib.sh"

if [[ "${1:-}" == --selftest ]]; then
  exec "${SCRIPT_DIR}/test-delta-rsync-handoff.sh"
fi

: "${GITHUB_SHA:?GITHUB_SHA is required}"
EXPECTED_SHA="${EXPECTED_SHA:-$GITHUB_SHA}"
INCOMING="${INCOMING_DIR:-/opt/karzar/incoming/${GITHUB_SHA}}"
STAGED="${STAGED_DIR:-${INCOMING}/tree}"
MODE="${HANDOFF_VERIFY_MODE:-consume}"

case "$MODE" in
  prepare)
    : "${EXPECTED_MANIFEST_SHA:?EXPECTED_MANIFEST_SHA is required for prepare mode}"
    karzar_verify_prepared_handoff "$INCOMING" "$EXPECTED_SHA" "$EXPECTED_MANIFEST_SHA"
    karzar_write_handoff_complete "$INCOMING" "$EXPECTED_SHA" "$EXPECTED_MANIFEST_SHA"
    echo "HANDOFF_COMPLETE written for sha=${EXPECTED_SHA}"
    ;;
  consume)
    karzar_verify_completed_handoff "$INCOMING" "$EXPECTED_SHA"
    ;;
  *)
    echo "unknown HANDOFF_VERIFY_MODE=${MODE}" >&2
    exit 1
    ;;
esac

# Optional local materialize for callers that still want a copy. Default STAGED
# is the incoming tree itself — no extra copy, no live mutation.
if [[ "$STAGED" != "${INCOMING}/tree" ]]; then
  mkdir -p "$STAGED"
  rsync -a --delete --exclude="${KARZAR_PARTIAL_DIR}/" "${INCOMING}/tree"/ "$STAGED"/
fi
