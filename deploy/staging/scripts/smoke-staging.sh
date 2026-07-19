#!/usr/bin/env bash
# Staging smoke checks after deploy.
# Usage:
#   API_BASE=https://api.example.com SHOP_BASE=https://shop.example.com \
#   ADMIN_BASE=https://admin.example.com bash deploy/staging/scripts/smoke-staging.sh
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
SHOP_BASE="${SHOP_BASE:-http://127.0.0.1:3000}"
ADMIN_BASE="${ADMIN_BASE:-http://127.0.0.1:3001}"

fail=0

check() {
  local name="$1" url="$2" expect="${3:-200}"
  local body
  body="$(mktemp)"
  code="$(curl -sS -o "$body" -w '%{http_code}' "$url" || true)"
  if [[ "$code" == "$expect" ]]; then
    echo "OK  $name ($code) $url"
  else
    echo "FAIL $name (got $code, want $expect) $url" >&2
    head -c 240 "$body" >&2 || true
    echo >&2
    fail=1
  fi
  rm -f "$body"
}

check "api_health" "$API_BASE/health"
check "api_ready" "$API_BASE/ready"
check "api_products" "$API_BASE/api/v1/products/?limit=1"
check "shop_home" "$SHOP_BASE/"
check "admin_home" "$ADMIN_BASE/"

if [[ "$fail" -ne 0 ]]; then
  echo "Smoke failed." >&2
  exit 1
fi
echo "Smoke passed."
