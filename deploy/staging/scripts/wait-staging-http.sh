#!/usr/bin/env bash
# Bounded HTTP readiness for staging loopback services (deploy + smoke).
# Connection failures and HTTP 000 mean "not ready yet" until the deadline.
#
# Usage:
#   wait-staging-http.sh <service_label> <url> [accepted_http_codes...]
#
# Env (optional):
#   READINESS_DEADLINE_SEC (default 300)
#   POLL_INTERVAL_SEC (default 4)
#   CONNECT_TIMEOUT_SEC (default 3)
#   MAX_TIME_SEC (default 10)
#   STAGING_HTTP_PROBE_HOST — if set, send Host + X-Forwarded-Proto for API TrustedHost probes
#   WAIT_DOCKER_CONTAINER — container name for logs on failure (e.g. karzar_admin)
set -euo pipefail

SERVICE_LABEL="${1:?service label}"
URL="${2:?url}"
shift 2
ACCEPT_CODES=("$@")
if [[ ${#ACCEPT_CODES[@]} -eq 0 ]]; then
  ACCEPT_CODES=(200)
fi

READINESS_DEADLINE_SEC="${READINESS_DEADLINE_SEC:-300}"
POLL_INTERVAL_SEC="${POLL_INTERVAL_SEC:-4}"
CONNECT_TIMEOUT_SEC="${CONNECT_TIMEOUT_SEC:-3}"
MAX_TIME_SEC="${MAX_TIME_SEC:-10}"

deadline_epoch="$(($(date +%s) + READINESS_DEADLINE_SEC))"
attempt=0

curl_base=(curl -sS --connect-timeout "$CONNECT_TIMEOUT_SEC" --max-time "$MAX_TIME_SEC")
if [[ -n "${STAGING_HTTP_PROBE_HOST:-}" ]]; then
  curl_base+=(-H "Host: ${STAGING_HTTP_PROBE_HOST}" -H "X-Forwarded-Proto: https")
fi

print_readiness_diagnostics() {
  local code="$1"
  echo "${SERVICE_LABEL}_READINESS_FAILED: last HTTP code ${code}, want ${ACCEPT_CODES[*]} — ${URL}" >&2
  echo "Diagnostics (no secrets):" >&2
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null | head -20 >&2 || true
  if [[ -n "${WAIT_DOCKER_CONTAINER:-}" ]]; then
    docker logs --tail=200 "$WAIT_DOCKER_CONTAINER" 2>&1 >&2 || true
  fi
}

while true; do
  attempt=$((attempt + 1))
  code="$("${curl_base[@]}" -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null || echo "000")"
  for expect in "${ACCEPT_CODES[@]}"; do
    if [[ "$code" == "$expect" ]]; then
      echo "READY ${SERVICE_LABEL} (HTTP ${code}) ${URL} after ${attempt} poll(s)"
      exit 0
    fi
  done
  if [[ "$(date +%s)" -ge "$deadline_epoch" ]]; then
    print_readiness_diagnostics "$code"
    exit 1
  fi
  sleep "$POLL_INTERVAL_SEC"
done
