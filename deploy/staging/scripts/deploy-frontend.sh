#!/usr/bin/env bash
# Build and run Storefront (:3000) + Admin (:3001) on loopback for staging.
#
# Required env:
#   FRONTEND_ROOT  — path containing Storefront/ and admin-panel/
#   NEXT_PUBLIC_API_BASE_URL — e.g. https://api.example.com/api/v1
#
# Example:
#   export FRONTEND_ROOT=/opt/karzar/frontend
#   export NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1
#   bash deploy/staging/scripts/deploy-frontend.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
: "${FRONTEND_ROOT:?Set FRONTEND_ROOT to the frontend repo root}"
: "${NEXT_PUBLIC_API_BASE_URL:?Set NEXT_PUBLIC_API_BASE_URL}"

SHOP_DIR="$FRONTEND_ROOT/Storefront"
ADMIN_DIR="$FRONTEND_ROOT/admin-panel"

[[ -d "$SHOP_DIR" ]] || { echo "Missing $SHOP_DIR" >&2; exit 1; }
[[ -d "$ADMIN_DIR" ]] || { echo "Missing $ADMIN_DIR" >&2; exit 1; }

# Ensure remote CDN images work on live catalog (idempotent patch if still locked down)
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
    print(f"patched remotePatterns in {path}")
else:
    print(f"skip patch (pattern not found): {path}")
PY
  fi
done

# Default mock off in env.ts if still true-by-default
for envts in "$SHOP_DIR/src/config/env.ts" "$ADMIN_DIR/src/config/env.ts"; do
  if [[ -f "$envts" ]] && grep -q '?? "true"' "$envts"; then
    sed -i 's/?? "true").toLowerCase() !== "false"/?? "false").toLowerCase() === "true"/' "$envts" || true
    echo "patched USE_MOCK default in $envts"
  fi
done

echo "Building shop image..."
docker build \
  -f "$ROOT_DIR/deploy/staging/frontend/Dockerfile.storefront" \
  --build-arg NEXT_PUBLIC_USE_MOCK=false \
  --build-arg "NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL" \
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
  -e PORT=3001 karzar-admin:staging

echo "Frontends up on 127.0.0.1:3000 (shop) and :3001 (admin)"
