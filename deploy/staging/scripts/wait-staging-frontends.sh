#!/usr/bin/env bash
# Wait for Storefront + Admin loopback HTTP after container (re)start.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHOP_BASE="${SHOP_BASE:-http://127.0.0.1:3000}"
ADMIN_BASE="${ADMIN_BASE:-http://127.0.0.1:3001}"

export WAIT_DOCKER_CONTAINER=karzar_shop
"$SCRIPT_DIR/wait-staging-http.sh" shop "${SHOP_BASE}/" 200
unset WAIT_DOCKER_CONTAINER

export WAIT_DOCKER_CONTAINER=karzar_admin
"$SCRIPT_DIR/wait-staging-http.sh" admin "${ADMIN_BASE}/login" 200
unset WAIT_DOCKER_CONTAINER

echo "Frontends readiness OK (${SHOP_BASE}, ${ADMIN_BASE})"
