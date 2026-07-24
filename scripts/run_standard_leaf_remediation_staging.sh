#!/usr/bin/env bash
# Run standard-leaf remediation on staging API from inside the VPS.
# Reads credentials from /opt/karzar/Karzar/.env — never echoes secrets.
set -euo pipefail

cd /opt/karzar/Karzar
PHONE=$(grep -E '^INITIAL_SUPER_ADMIN_PHONE=' .env | tail -1 | cut -d= -f2-)
PASS=$(grep -E '^INITIAL_SUPER_ADMIN_PASSWORD=' .env | tail -1 | cut -d= -f2-)
PIN=$(grep -E '^ADMIN_STEP_UP_PIN=' .env | tail -1 | cut -d= -f2-)

# Staging uvicorn redirects HTTP→HTTPS on :8000; use public TLS API.
API="${API:-https://api.karzartools.com/api/v1}"
MODE="${1:-dry-run}" # dry-run | apply
SCRIPT=/opt/karzar/Karzar/scripts/remediate_standard_leaves.py

if [[ "$MODE" != "apply" ]]; then
  python3 "$SCRIPT" --api "$API"
  exit 0
fi

TOKEN=$(curl -sS -X POST "$API/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=${PHONE}&password=${PASS}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')

if [[ -z "$TOKEN" ]]; then
  echo "FAIL: login produced empty token" >&2
  exit 1
fi
echo "login: ok"

if [[ -z "$PIN" ]]; then
  echo "WARN: ADMIN_STEP_UP_PIN missing; renames only (--skip-deletes)" >&2
  python3 "$SCRIPT" --api "$API" --token "$TOKEN" --apply --skip-deletes
else
  echo "auth: ok; applying renames + deletes + insert collapse (fresh step-up per DELETE)"
  # Pass --pin so each DELETE mints a fresh single-use step-up token.
  python3 "$SCRIPT" --api "$API" --token "$TOKEN" --pin "$PIN" --apply --collapse-insert
fi
