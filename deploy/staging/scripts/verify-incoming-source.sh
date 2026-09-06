#!/usr/bin/env bash
# Verify a locally staged incoming tree against the GitHub-generated manifest.
# Runs on karzar-vps. Never fetches from GitHub or Azure. Never writes live trees.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-tree-lib.sh
source "${SCRIPT_DIR}/deploy-tree-lib.sh"

if [[ "${1:-}" == --selftest ]]; then
  exec "${SCRIPT_DIR}/test-delta-rsync-handoff.sh"
fi

: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${EXPECTED_MANIFEST_SHA:?EXPECTED_MANIFEST_SHA is required}"
EXPECTED_SHA="${EXPECTED_SHA:-$GITHUB_SHA}"
INCOMING="${INCOMING_DIR:-/opt/karzar/incoming/${GITHUB_SHA}}"
STAGED="${STAGED_DIR:-${INCOMING}/tree}"
REQUIRE_HANDOFF_COMPLETE="${REQUIRE_HANDOFF_COMPLETE:-1}"
WRITE_HANDOFF_COMPLETE="${WRITE_HANDOFF_COMPLETE:-0}"

if [[ "${REQUIRE_HANDOFF_COMPLETE}" != "0" ]]; then
  karzar_require_handoff_complete "$INCOMING" "$EXPECTED_SHA"
fi

karzar_verify_incoming_tree "$INCOMING" "$EXPECTED_SHA" "$EXPECTED_MANIFEST_SHA"

if [[ "${WRITE_HANDOFF_COMPLETE}" == "1" ]]; then
  karzar_write_handoff_complete "$INCOMING" "$EXPECTED_SHA" "$EXPECTED_MANIFEST_SHA"
  echo "HANDOFF_COMPLETE written for sha=${EXPECTED_SHA}"
fi

# Optional local materialize for callers that still want a copy. Default STAGED
# is the incoming tree itself — no extra copy, no live mutation.
if [[ "$STAGED" != "${INCOMING}/tree" ]]; then
  mkdir -p "$STAGED"
  rsync -a --delete --exclude="${KARZAR_PARTIAL_DIR}/" "${INCOMING}/tree"/ "$STAGED"/
fi
