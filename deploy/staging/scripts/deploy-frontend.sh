#!/usr/bin/env bash
# Restart Storefront (:3000) + Admin (:3001) from prebuilt images on staging.
# Canonical Deploy Staging loads images via load-incoming-frontend-images.sh first.
# VPS npm/docker build: deploy-frontend-build-local.sh only.
#
# Required env:
#   FRONTEND_ROOT  — path containing Storefront/ and admin-panel/ (config patches)
#   NEXT_PUBLIC_API_BASE_URL
#   ADMIN_SESSION_SECRET — runtime only (never baked into images)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
# shellcheck source=frontend-image-lib.sh
source "${SCRIPT_DIR}/frontend-image-lib.sh"

: "${FRONTEND_ROOT:?Set FRONTEND_ROOT to the frontend repo root}"
: "${NEXT_PUBLIC_API_BASE_URL:?Set NEXT_PUBLIC_API_BASE_URL}"
: "${ADMIN_SESSION_SECRET:?Set ADMIN_SESSION_SECRET (min 32 chars)}"
if [[ "${#ADMIN_SESSION_SECRET}" -lt 32 ]]; then
  echo "ADMIN_SESSION_SECRET must be at least 32 characters" >&2
  exit 1
fi

if [[ "${KARZAR_REQUIRE_PREBUILT_FRONTEND_IMAGES:-}" == "1" ]]; then
  : "${GITHUB_SHA:?GITHUB_SHA required for prebuilt frontend deploy}"
  SHOP_IMAGE="${KARZAR_SHOP_IMAGE:-$(karzar_frontend_shop_image_tag "$GITHUB_SHA")}"
  ADMIN_IMAGE="${KARZAR_ADMIN_IMAGE:-$(karzar_frontend_admin_image_tag "$GITHUB_SHA")}"
  karzar_verify_image_revision "$SHOP_IMAGE" "$GITHUB_SHA" || exit 1
  karzar_verify_image_revision "$ADMIN_IMAGE" "$GITHUB_SHA" || exit 1
else
  SHOP_IMAGE="${KARZAR_SHOP_IMAGE:-$(karzar_staging_shop_alias)}"
  ADMIN_IMAGE="${KARZAR_ADMIN_IMAGE:-$(karzar_staging_admin_alias)}"
fi

SHOP_DIR="$FRONTEND_ROOT/Storefront"
ADMIN_DIR="$FRONTEND_ROOT/admin-panel"
[[ -d "$SHOP_DIR" && -d "$ADMIN_DIR" ]] || { echo "Missing Storefront or admin-panel under FRONTEND_ROOT" >&2; exit 1; }

karzar_print_frontend_deploy_diagnostics() {
  local attempted_shop="$1"
  local attempted_admin="$2"
  echo "DIAG previous_shop_image=$(docker inspect karzar_shop --format '{{.Config.Image}}' 2>/dev/null || echo none)"
  echo "DIAG previous_admin_image=$(docker inspect karzar_admin --format '{{.Config.Image}}' 2>/dev/null || echo none)"
  echo "DIAG attempted_shop_image=${attempted_shop}"
  echo "DIAG attempted_admin_image=${attempted_admin}"
  docker ps -a --filter name=karzar_shop --filter name=karzar_admin --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null || true
}

# Idempotent source patches (no image build)
for cfg in "$SHOP_DIR/next.config.ts" "$ADMIN_DIR/next.config.ts"; do
  if [[ -f "$cfg" ]] && grep -q 'picsum.photos' "$cfg" && ! grep -q 'hostname: "\*\*"' "$cfg"; then
    python3 - "$cfg" <<'PY'
import pathlib, re, sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
new = """images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
      { protocol: "http", hostname: "localhost" },
      { protocol: "http", hostname: "127.0.0.1" },
    ],
  },"""
text2, n = re.subn(
    r"images:\s*\{[\s\S]*?remotePatterns:\s*\[[\s\S]*?\],\s*\},",
    new,
    text,
    count=1,
)
if n:
    path.write_text(text2)
PY
  fi
done

for envts in "$SHOP_DIR/src/config/env.ts" "$ADMIN_DIR/src/config/env.ts"; do
  if [[ -f "$envts" ]] && grep -q '?? "true"' "$envts"; then
    sed -i 's/?? "true").toLowerCase() !== "false"/?? "false").toLowerCase() === "true"/' "$envts" || true
  fi
done

docker image inspect "$SHOP_IMAGE" >/dev/null
docker image inspect "$ADMIN_IMAGE" >/dev/null

echo "Deploying shop container from ${SHOP_IMAGE} ..."
karzar_print_frontend_deploy_diagnostics "$SHOP_IMAGE" "$ADMIN_IMAGE"

shop_started=0
admin_started=0

if ! docker rm -f karzar_shop 2>/dev/null; then true; fi
if docker run -d --name karzar_shop --restart unless-stopped \
  -p 127.0.0.1:3000:3000 "$SHOP_IMAGE"; then
  shop_started=1
else
  echo "ERROR: failed to start karzar_shop" >&2
  karzar_print_frontend_deploy_diagnostics "$SHOP_IMAGE" "$ADMIN_IMAGE"
  exit 1
fi

if ! docker rm -f karzar_admin 2>/dev/null; then true; fi
if docker run -d --name karzar_admin --restart unless-stopped \
  -p 127.0.0.1:3001:3001 \
  -e PORT=3001 \
  -e "ADMIN_SESSION_SECRET=$ADMIN_SESSION_SECRET" \
  "$ADMIN_IMAGE"; then
  admin_started=1
else
  echo "ERROR: failed to start karzar_admin after shop restart" >&2
  karzar_print_frontend_deploy_diagnostics "$SHOP_IMAGE" "$ADMIN_IMAGE"
  exit 1
fi

echo "Frontends containers started; waiting for HTTP readiness ..."
SHOP_BASE="${SHOP_BASE:-http://127.0.0.1:3000}"
ADMIN_BASE="${ADMIN_BASE:-http://127.0.0.1:3001}"
if ! bash "$ROOT_DIR/deploy/staging/scripts/wait-staging-frontends.sh"; then
  karzar_print_frontend_deploy_diagnostics "$SHOP_IMAGE" "$ADMIN_IMAGE"
  exit 1
fi
echo "Frontends up on 127.0.0.1:3000 (shop) and :3001 (admin)"
