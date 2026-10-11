#!/usr/bin/env bash
# Regression guard: staging backend Dockerfile PyPI index fallback (structural only).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE="${SCRIPT_DIR}/../Dockerfile.staging"

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "FAIL: missing ${DOCKERFILE}" >&2
  exit 1
fi

if ! grep -q 'mirrors.aliyun.com/pypi/simple' "$DOCKERFILE"; then
  echo "FAIL: primary Aliyun mirror not configured" >&2
  exit 1
fi

if ! grep -q 'pypi.tuna.tsinghua.edu.cn/simple' "$DOCKERFILE"; then
  echo "FAIL: verified Tsinghua fallback index missing" >&2
  exit 1
fi

if grep -vE '^\s*#' "$DOCKERFILE" | grep -qE '(^|[[:space:]])--extra-index-url'; then
  echo "FAIL: --extra-index-url must not be used (one index per install attempt)" >&2
  exit 1
fi

# Same requirements.txt on primary and fallback attempts.
REQ_COUNT=$(grep -cE 'pip install.*-r requirements\.txt' "$DOCKERFILE" || true)
if [[ "$REQ_COUNT" -lt 2 ]]; then
  echo "FAIL: expected at least two pip install -r requirements.txt attempts" >&2
  exit 1
fi

# Conditional fallback after primary failure (shell || chain).
if ! grep -qE '\|\|' "$DOCKERFILE" || ! grep -q 'Primary PyPI mirror failed' "$DOCKERFILE"; then
  echo "FAIL: fallback must be conditional on primary pip install failure" >&2
  exit 1
fi

if ! grep -q 'PIP_INDEX_URL=.*tuna\.tsinghua' "$DOCKERFILE"; then
  echo "FAIL: fallback must set PIP_INDEX_URL for alternate mirror only" >&2
  exit 1
fi

echo "PASS: Dockerfile PyPI mirror fallback contract"
