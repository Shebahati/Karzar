#!/usr/bin/env bash
# Verify a locally staged incoming package and extract it.
# Runs on karzar-vps. Never fetches from GitHub or Azure.
set -euo pipefail

if [[ "${1:-}" == --selftest ]]; then
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  mkdir -p "$tmp/in" "$tmp/empty"
  if INCOMING_DIR="$tmp/empty" STAGED_DIR="$tmp/out" GITHUB_SHA=deadbeef EXPECTED_DIGEST=deadbeef \
      "$0"; then
    echo "selftest: empty incoming should fail" >&2
    exit 1
  fi
  mkdir -p "$tmp/tree/deploy/staging/scripts" "$tmp/tree/frontend/Storefront" "$tmp/tree/app"
  echo ok > "$tmp/tree/deploy/staging/scripts/deploy-frontend.sh"
  echo ok > "$tmp/tree/app/main.py"
  tar -C "$tmp/tree" -czf "$tmp/in/src.tgz" .
  sha256sum "$tmp/in/src.tgz" | awk '{print $1"  src.tgz"}' > "$tmp/in/src.tgz.sha256"
  expected="$(awk '{print $1}' "$tmp/in/src.tgz.sha256")"
  INCOMING_DIR="$tmp/in" STAGED_DIR="$tmp/out" GITHUB_SHA=deadbeef EXPECTED_DIGEST="$expected" "$0"
  test -f "$tmp/out/deploy/staging/scripts/deploy-frontend.sh"
  echo "selftest: ok"
  exit 0
fi

: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${EXPECTED_DIGEST:?EXPECTED_DIGEST is required}"
INCOMING="${INCOMING_DIR:-/opt/karzar/incoming/${GITHUB_SHA}}"
STAGED="${STAGED_DIR:-${RUNNER_TEMP:-/tmp}/staging-src}"

test -d "$INCOMING"
test -f "$INCOMING/src.tgz"
test -f "$INCOMING/src.tgz.sha256"
(
  cd "$INCOMING"
  sha256sum -c src.tgz.sha256
)
DIGEST="$(awk '{print $1}' "$INCOMING/src.tgz.sha256")"
if [[ "$DIGEST" != "$EXPECTED_DIGEST" ]]; then
  echo "incoming digest does not match GitHub-hosted package digest" >&2
  exit 1
fi

rm -rf "$STAGED"
mkdir -p "$STAGED"
tar -xzf "$INCOMING/src.tgz" -C "$STAGED"

test -f "$STAGED/deploy/staging/scripts/deploy-frontend.sh"
test -d "$STAGED/frontend/Storefront"
test -d "$STAGED/app"

echo "HANDOFF_OK sha=${GITHUB_SHA} transport=ssh-push digest=${DIGEST}"
