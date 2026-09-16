#!/usr/bin/env bash
# VPS-local frontend image build (npm/registry on host). NOT used by canonical Deploy Staging.
# Production remediate flows may call this explicitly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

: "${FRONTEND_ROOT:?Set FRONTEND_ROOT to the frontend repo root}"
: "${NEXT_PUBLIC_API_BASE_URL:?Set NEXT_PUBLIC_API_BASE_URL}"

SHOP_DIR="$FRONTEND_ROOT/Storefront"
ADMIN_DIR="$FRONTEND_ROOT/admin-panel"
# Legacy VPS/production local build: preserve npmmirror default (Iranian VPS egress).
# GitHub-hosted staging prebuild uses registry.npmjs.org via build-staging-frontend-images.sh.
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
GIT_REVISION="${GIT_REVISION:-local-build}"
IMAGE_SOURCE="${IMAGE_SOURCE:-https://github.com/Shebahati/Karzar}"
IMAGE_CREATED="${IMAGE_CREATED:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

bash "${SCRIPT_DIR}/prepare-frontend-build-source.sh"

common_build_args=(
  --build-arg "GIT_REVISION=${GIT_REVISION}"
  --build-arg "IMAGE_SOURCE=${IMAGE_SOURCE}"
  --build-arg "IMAGE_CREATED=${IMAGE_CREATED}"
  --build-arg "NPM_REGISTRY=${NPM_REGISTRY}"
  --build-arg "NEXT_PUBLIC_USE_MOCK=false"
  --build-arg "NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}"
)

echo "Building shop image (local VPS) ..."
docker build \
  -f "$ROOT_DIR/deploy/staging/frontend/Dockerfile.storefront" \
  "${common_build_args[@]}" \
  --build-arg "NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL:-https://www.karzartools.com}" \
  --build-arg "NEXT_PUBLIC_SEO_INDEXABLE=${NEXT_PUBLIC_SEO_INDEXABLE:-true}" \
  --build-arg "NEXT_PUBLIC_GA_MEASUREMENT_ID=${NEXT_PUBLIC_GA_MEASUREMENT_ID:-}" \
  -t karzar-shop:staging \
  "$SHOP_DIR"

echo "Building admin image (local VPS) ..."
docker build \
  -f "$ROOT_DIR/deploy/staging/frontend/Dockerfile.admin" \
  "${common_build_args[@]}" \
  -t karzar-admin:staging \
  "$ADMIN_DIR"

export KARZAR_SHOP_IMAGE="${KARZAR_SHOP_IMAGE:-karzar-shop:staging}"
export KARZAR_ADMIN_IMAGE="${KARZAR_ADMIN_IMAGE:-karzar-admin:staging}"
export KARZAR_REQUIRE_PREBUILT_FRONTEND_IMAGES=0

exec bash "${SCRIPT_DIR}/deploy-frontend.sh"
