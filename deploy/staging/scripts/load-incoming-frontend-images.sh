#!/usr/bin/env bash
# Load prebuilt frontend images from incoming/<sha>/frontend-images/ on the VPS.
# Fail closed: marker + checksum + OCI revision must match before container swap.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=frontend-image-lib.sh
source "${SCRIPT_DIR}/frontend-image-lib.sh"

if [[ "${1:-}" == --selftest ]]; then
  exec "${SCRIPT_DIR}/test-prebuilt-frontend-handoff.sh"
fi

: "${GITHUB_SHA:?GITHUB_SHA is required}"
EXPECTED_SHA="${EXPECTED_SHA:-$GITHUB_SHA}"
if [[ "$EXPECTED_SHA" != "$GITHUB_SHA" ]]; then
  echo "EXPECTED_SHA mismatch" >&2
  exit 1
fi

DIR="$(karzar_frontend_images_incoming_dir "$GITHUB_SHA")"
MARKER="${DIR}/${KARZAR_FRONTEND_IMAGES_MARKER}"
BUNDLE="${DIR}/${KARZAR_FRONTEND_BUNDLE_NAME}"
CHECKSUM="${DIR}/${KARZAR_FRONTEND_CHECKSUM_NAME}"

if [[ "${KARZAR_FE_VERIFY_ONLY:-}" == "1" ]]; then
  test -f "$MARKER"
  test -f "$BUNDLE"
  test -f "$CHECKSUM"
  karzar_read_frontend_images_handoff_marker "$MARKER"
  echo "FRONTEND_IMAGES_VERIFY_OK sha=${GITHUB_SHA}"
  exit 0
fi

test -f "$MARKER" || { echo "VERIFY=FAIL missing ${KARZAR_FRONTEND_IMAGES_MARKER}" >&2; exit 1; }
test -f "$BUNDLE" || { echo "VERIFY=FAIL missing bundle" >&2; exit 1; }
test -f "$CHECKSUM" || { echo "VERIFY=FAIL missing checksum file" >&2; exit 1; }

karzar_read_frontend_images_handoff_marker "$MARKER"

(
  cd "$DIR"
  sha256sum -c "${KARZAR_FRONTEND_CHECKSUM_NAME}"
)

SHOP_TAG="${KARZAR_FE_HANDOFF_SHOP:-$(karzar_frontend_shop_image_tag "$GITHUB_SHA")}"
ADMIN_TAG="${KARZAR_FE_HANDOFF_ADMIN:-$(karzar_frontend_admin_image_tag "$GITHUB_SHA")}"

if [[ "${KARZAR_SKIP_DOCKER_LOAD:-}" != "1" ]]; then
  docker load -i "$BUNDLE"
fi

karzar_verify_image_revision "$SHOP_TAG" "$GITHUB_SHA"
karzar_verify_image_revision "$ADMIN_TAG" "$GITHUB_SHA"

STAGING_SHOP="$(karzar_staging_shop_alias)"
STAGING_ADMIN="$(karzar_staging_admin_alias)"

if [[ "${KARZAR_SKIP_DOCKER_TAG:-}" != "1" ]]; then
  docker tag "$SHOP_TAG" "$STAGING_SHOP"
  docker tag "$ADMIN_TAG" "$STAGING_ADMIN"
fi

export KARZAR_SHOP_IMAGE="$SHOP_TAG"
export KARZAR_ADMIN_IMAGE="$ADMIN_TAG"
export KARZAR_STAGING_SHOP_IMAGE="$STAGING_SHOP"
export KARZAR_STAGING_ADMIN_IMAGE="$STAGING_ADMIN"

echo "FRONTEND_IMAGES_LOADED shop=${SHOP_TAG} admin=${ADMIN_TAG} staging_shop=${STAGING_SHOP} staging_admin=${STAGING_ADMIN}"
