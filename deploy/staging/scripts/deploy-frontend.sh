#!/usr/bin/env bash
# Build and run Storefront (:3000) + Admin (:3001) on loopback for staging.
#
# Required env:
#   FRONTEND_ROOT  — path containing Storefront/ and admin-panel/
#   NEXT_PUBLIC_API_BASE_URL — e.g. https://api.example.com/api/v1
#   ADMIN_SESSION_SECRET — min 32 chars; HMAC for admin edge session cookie
#
# Build-time args (baked into Next.js bundles — must match commit, no post-deploy sed):
#   NEXT_PUBLIC_USE_MOCK=false (default in Dockerfiles)
#   NEXT_PUBLIC_API_BASE_URL (required)
#   NEXT_PUBLIC_ASSET_BASE_URL (optional; Storefront CDN/origin for images)
#
# Example:
#   export FRONTEND_ROOT=/opt/karzar/frontend
#   export NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1
#   export ADMIN_SESSION_SECRET="$(openssl rand -hex 32)"
#   bash deploy/staging/scripts/deploy-frontend.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
: "${FRONTEND_ROOT:?Set FRONTEND_ROOT to the frontend repo root}"
: "${NEXT_PUBLIC_API_BASE_URL:?Set NEXT_PUBLIC_API_BASE_URL}"
: "${ADMIN_SESSION_SECRET:?Set ADMIN_SESSION_SECRET (min 32 chars)}"
if [[ "${#ADMIN_SESSION_SECRET}" -lt 32 ]]; then
  echo "ADMIN_SESSION_SECRET must be at least 32 characters" >&2
  exit 1
fi

SHOP_DIR="$FRONTEND_ROOT/Storefront"
ADMIN_DIR="$FRONTEND_ROOT/admin-panel"

[[ -d "$SHOP_DIR" ]] || { echo "Missing $SHOP_DIR" >&2; exit 1; }
[[ -d "$ADMIN_DIR" ]] || { echo "Missing $ADMIN_DIR" >&2; exit 1; }

SHOP_BUILD_ARGS=(
  --build-arg NEXT_PUBLIC_USE_MOCK=false
  --build-arg "NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL"
)
if [[ -n "${NEXT_PUBLIC_ASSET_BASE_URL:-}" ]]; then
  SHOP_BUILD_ARGS+=(--build-arg "NEXT_PUBLIC_ASSET_BASE_URL=$NEXT_PUBLIC_ASSET_BASE_URL")
fi

echo "Building shop image..."
docker build \
  -f "$ROOT_DIR/deploy/staging/frontend/Dockerfile.storefront" \
  "${SHOP_BUILD_ARGS[@]}" \
  -t karzar-shop:staging \
  "$SHOP_DIR"

echo "Building admin image..."
docker build \
  -f "$ROOT_DIR/deploy/staging/frontend/Dockerfile.admin" \
  --build-arg NEXT_PUBLIC_USE_MOCK=false \
  --build-arg "NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL" \
  -t karzar-admin:staging \
  "$ADMIN_DIR"

# Restart shop even if admin rebuild is retried later
docker rm -f karzar_shop 2>/dev/null || true
docker run -d --name karzar_shop --restart unless-stopped \
  -p 127.0.0.1:3000:3000 karzar-shop:staging

docker rm -f karzar_admin 2>/dev/null || true
docker run -d --name karzar_admin --restart unless-stopped \
  -p 127.0.0.1:3001:3001 \
  -e PORT=3001 \
  -e "ADMIN_SESSION_SECRET=$ADMIN_SESSION_SECRET" \
  karzar-admin:staging

echo "Frontends up on 127.0.0.1:3000 (shop) and :3001 (admin)"
