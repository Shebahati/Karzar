#!/usr/bin/env bash
# Build Storefront + Admin staging images on GitHub-hosted runner (npm/registry here, not VPS).
# Tags immutable sha-* refs and verifies OCI revision labels before handoff packaging.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=frontend-image-lib.sh
source "${SCRIPT_DIR}/frontend-image-lib.sh"

: "${GITHUB_SHA:?GITHUB_SHA is required}"
if [[ ! "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid GITHUB_SHA" >&2
  exit 1
fi

ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
SHOP_DIR="${ROOT}/frontend/Storefront"
ADMIN_DIR="${ROOT}/frontend/admin-panel"
DOCKERFILE_SHOP="${ROOT}/deploy/staging/frontend/Dockerfile.storefront"
DOCKERFILE_ADMIN="${ROOT}/deploy/staging/frontend/Dockerfile.admin"

SHOP_TAG="$(karzar_frontend_shop_image_tag "$GITHUB_SHA")"
ADMIN_TAG="$(karzar_frontend_admin_image_tag "$GITHUB_SHA")"

NEXT_PUBLIC_USE_MOCK="${NEXT_PUBLIC_USE_MOCK:-false}"
NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-https://api.karzartools.com/api/v1}"
NEXT_PUBLIC_SITE_URL="${NEXT_PUBLIC_SITE_URL:-https://www.karzartools.com}"
NEXT_PUBLIC_SEO_INDEXABLE="${NEXT_PUBLIC_SEO_INDEXABLE:-true}"
NEXT_PUBLIC_GA_MEASUREMENT_ID="${NEXT_PUBLIC_GA_MEASUREMENT_ID:-G-NT8ZT3G6HC}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org/}"
GIT_REVISION="$GITHUB_SHA"
IMAGE_SOURCE="${IMAGE_SOURCE:-$KARZAR_IMAGE_SOURCE_DEFAULT}"
IMAGE_CREATED="${IMAGE_CREATED:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

common_build_args=(
  --build-arg "GIT_REVISION=${GIT_REVISION}"
  --build-arg "IMAGE_SOURCE=${IMAGE_SOURCE}"
  --build-arg "IMAGE_CREATED=${IMAGE_CREATED}"
  --build-arg "NPM_REGISTRY=${NPM_REGISTRY}"
  --build-arg "NEXT_PUBLIC_USE_MOCK=${NEXT_PUBLIC_USE_MOCK}"
  --build-arg "NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}"
)

[[ -d "$SHOP_DIR" && -d "$ADMIN_DIR" ]] || { echo "missing frontend directories under $ROOT/frontend" >&2; exit 1; }

if [[ "${KARZAR_SKIP_DOCKER_BUILD:-}" == "1" ]]; then
  echo "KARZAR_SKIP_DOCKER_BUILD=1 — skipping docker build (selftest)"
  exit 0
fi

build_one() {
  local dockerfile="$1"
  local context="$2"
  local tag="$3"
  local cache_scope="$4"
  shift 4
  local extra_args=("$@")
  local cache_from=()
  local cache_to=()
  if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    cache_from=(--cache-from "type=gha,scope=${cache_scope}")
    cache_to=(--cache-to "type=gha,mode=max,scope=${cache_scope}")
  fi
  docker buildx build \
    --load \
    "${cache_from[@]}" \
    "${cache_to[@]}" \
    -f "$dockerfile" \
    "${common_build_args[@]}" \
    "${extra_args[@]}" \
    -t "$tag" \
    "$context"
}

echo "Building ${SHOP_TAG} ..."
build_one "$DOCKERFILE_SHOP" "$SHOP_DIR" "$SHOP_TAG" karzar-storefront \
  --build-arg "NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}" \
  --build-arg "NEXT_PUBLIC_SEO_INDEXABLE=${NEXT_PUBLIC_SEO_INDEXABLE}" \
  --build-arg "NEXT_PUBLIC_GA_MEASUREMENT_ID=${NEXT_PUBLIC_GA_MEASUREMENT_ID}"

echo "Building ${ADMIN_TAG} ..."
build_one "$DOCKERFILE_ADMIN" "$ADMIN_DIR" "$ADMIN_TAG" karzar-admin

for ref in "$SHOP_TAG" "$ADMIN_TAG"; do
  karzar_verify_image_revision "$ref" "$GITHUB_SHA"
done

echo "FRONTEND_IMAGES_BUILT shop=${SHOP_TAG} admin=${ADMIN_TAG} sha=${GITHUB_SHA}"
