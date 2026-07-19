#!/usr/bin/env bash
# Build and start Karzar API + Postgres + Redis in staging mode.
# Run from the Karzar repo root on the VPS.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy deploy/staging/.env.staging.template to .env and fill secrets." >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

: "${SECRET_KEY:?SECRET_KEY required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}"
: "${TRUSTED_HOSTS:?TRUSTED_HOSTS required}"
: "${CORS_ORIGINS:?CORS_ORIGINS required}"

if [[ "${SECRET_KEY}" == *"replace-me"* ]]; then
  echo "Refuse to deploy: SECRET_KEY still has placeholder text." >&2
  exit 1
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.staging.yml)
if [[ -f docker-compose.image.yml ]]; then
  COMPOSE+=(-f docker-compose.image.yml)
fi

if [[ -f deploy/staging/Dockerfile.staging ]]; then
  echo "Building karzar-app:staging from Dockerfile.staging ..."
  docker build -f deploy/staging/Dockerfile.staging -t karzar-app:staging .
else
  "${COMPOSE[@]}" pull || true
  "${COMPOSE[@]}" build
fi

"${COMPOSE[@]}" up -d

echo "Waiting for /ready ..."
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:8000/ready" >/dev/null; then
    echo "API ready."
    curl -sS "http://127.0.0.1:8000/ready"
    echo
    exit 0
  fi
  sleep 2
done

echo "API did not become ready in time. Recent logs:" >&2
"${COMPOSE[@]}" logs --tail=80 app >&2
exit 1
