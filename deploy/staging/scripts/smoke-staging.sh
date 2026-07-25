#!/usr/bin/env bash
# Staging smoke checks after deploy.
# Usage:
#   API_BASE=https://api.example.com SHOP_BASE=https://shop.example.com \
#   ADMIN_BASE=https://admin.example.com bash deploy/staging/scripts/smoke-staging.sh
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
SHOP_BASE="${SHOP_BASE:-http://127.0.0.1:3000}"
ADMIN_BASE="${ADMIN_BASE:-http://127.0.0.1:3001}"

# When probing loopback under TrustedHostMiddleware, send a configured Host.
if [[ -z "${API_PROBE_HOST:-}" && -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
API_PROBE_HOST="${API_PROBE_HOST:-${TRUSTED_HOSTS%%,*}}"
API_PROBE_HOST="${API_PROBE_HOST// /}"

fail=0

check() {
  local name="$1" url="$2"
  shift 2
  local expect_codes=("$@")
  if [[ ${#expect_codes[@]} -eq 0 ]]; then
    expect_codes=(200)
  fi
  local body curl_args=()
  body="$(mktemp)"
  if [[ "$url" == "$API_BASE"* && -n "${API_PROBE_HOST:-}" ]]; then
    # Mimic TLS-terminating proxy so TrustedHost + ENFORCE_HTTPS both pass.
    curl_args+=(-H "Host: ${API_PROBE_HOST}" -H "X-Forwarded-Proto: https")
  fi
  code="$(curl -sS "${curl_args[@]}" -o "$body" -w '%{http_code}' "$url" || true)"
  local ok=0
  for expect in "${expect_codes[@]}"; do
    if [[ "$code" == "$expect" ]]; then
      ok=1
      break
    fi
  done
  if [[ "$ok" -eq 1 ]]; then
    echo "OK  $name ($code) $url"
  else
    echo "FAIL $name (got $code, want ${expect_codes[*]}) $url" >&2
    head -c 240 "$body" >&2 || true
    echo >&2
    fail=1
  fi
  rm -f "$body"
}

check "api_health" "$API_BASE/health" 200
check "api_ready" "$API_BASE/ready" 200
check "api_products" "$API_BASE/api/v1/products/?limit=1" 200
check "shop_home" "$SHOP_BASE/" 200
# Admin root redirects anonymous users to login — both prove the app is up.
check "admin_home" "$ADMIN_BASE/" 200 302 307
check "admin_login" "$ADMIN_BASE/login" 200

if [[ "$fail" -ne 0 ]]; then
  echo "Smoke failed." >&2
  exit 1
fi
echo "Smoke passed."
