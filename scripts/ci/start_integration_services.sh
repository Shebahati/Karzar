#!/usr/bin/env bash
# Start Postgres + Redis for backend CI heavy tests (no GHA job-level services on R0/R1).
set -euo pipefail
docker rm -f ci-postgres ci-redis >/dev/null 2>&1 || true
docker run -d --name ci-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=karzar_ci \
  -p 5432:5432 \
  postgres:15
docker run -d --name ci-redis -p 6379:6379 redis:7
for i in $(seq 1 30); do
  if docker exec ci-postgres pg_isready -U postgres >/dev/null 2>&1 && docker exec ci-redis redis-cli ping | grep -q PONG; then
    echo "Integration services ready"
    exit 0
  fi
  sleep 2
done
echo "Timed out waiting for Postgres/Redis" >&2
exit 1
