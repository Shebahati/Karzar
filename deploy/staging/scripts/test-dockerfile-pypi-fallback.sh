#!/usr/bin/env bash
# Regression guard: staging backend Dockerfile must retry official PyPI on mirror failure.
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

if ! grep -q 'pypi.org/simple' "$DOCKERFILE"; then
  echo "FAIL: official PyPI fallback URL missing" >&2
  exit 1
fi

if grep -vE '^\s*#' "$DOCKERFILE" | grep -qE '(^|[[:space:]])--extra-index-url'; then
  echo "FAIL: --extra-index-url must not be used (one index per install attempt)" >&2
  exit 1
fi

if ! grep -q 'requirements.txt' "$DOCKERFILE"; then
  echo "FAIL: requirements.txt install missing" >&2
  exit 1
fi

echo "PASS: Dockerfile PyPI mirror fallback contract"
