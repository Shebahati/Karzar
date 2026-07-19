#!/usr/bin/env bash
# One-shot staging remediations: sync code, rebuild API/FE, HSTS, mirror images.
# Run from the developer machine (has SSH key to VPS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FE_ROOT="${FE_ROOT:-/home/moahmmad/Projects/kar/karzar-frontend-main (1)/karzar-frontend-main}"
VPS="${VPS_HOST:-195.177.255.198}"
REMOTE_BE="${REMOTE_BE:-/opt/karzar/Karzar}"
REMOTE_FE="${REMOTE_FE:-/opt/karzar/frontend}"

echo "==> rsync backend → $VPS:$REMOTE_BE"
rsync -az --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.env' \
  --exclude '.deploy-secrets' \
  --exclude '.env.staging.generated' \
  --exclude 'backups/' \
  --exclude 'data/uploads/' \
  --exclude 'logs/' \
  --exclude '*.pyc' \
  "$ROOT/" "root@$VPS:$REMOTE_BE/"

echo "==> rsync frontend → $VPS:$REMOTE_FE"
rsync -az \
  --exclude 'node_modules/' \
  --exclude '.next/' \
  --exclude '.git/' \
  "$FE_ROOT/Storefront/" "root@$VPS:$REMOTE_FE/Storefront/"
rsync -az \
  --exclude 'node_modules/' \
  --exclude '.next/' \
  --exclude '.git/' \
  "$FE_ROOT/admin-panel/" "root@$VPS:$REMOTE_FE/admin-panel/"

echo "==> remote: env + HSTS + rebuild + mirror + frontend"
ssh "root@$VPS" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/karzar/Karzar

# Ensure staging env knobs (idempotent; no secret echo)
grep -q '^TRUSTED_PROXIES=' .env || echo 'TRUSTED_PROXIES=127.0.0.1' >> .env
grep -q '^PUBLIC_ASSET_BASE=' .env || echo 'PUBLIC_ASSET_BASE=https://api.karzartools.com' >> .env
# Normalize values if placeholders remain
sed -i 's|^PUBLIC_ASSET_BASE=.*|PUBLIC_ASSET_BASE=https://api.karzartools.com|' .env
sed -i 's|^TRUSTED_PROXIES=.*|TRUSTED_PROXIES=127.0.0.1|' .env

chmod +x deploy/staging/scripts/*.sh scripts/mirror_product_images.py || true
bash deploy/staging/scripts/enable-hsts.sh

bash deploy/staging/scripts/deploy-backend.sh

echo "Mirroring product images (may take several minutes)..."
docker compose -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.image.yml \
  exec -T app python scripts/mirror_product_images.py </dev/null || true

export FRONTEND_ROOT=/opt/karzar/frontend
export NEXT_PUBLIC_API_BASE_URL=https://api.karzartools.com/api/v1
bash deploy/staging/scripts/deploy-frontend.sh

echo "Smoke:"
curl -sS http://127.0.0.1:8000/ready; echo
curl -sI http://127.0.0.1:8000/api/v1/products/ | head -5 || true
REMOTE

echo "==> external smoke"
curl -sI 'https://api.karzartools.com/api/v1/products' | head -15
curl -sI 'https://www.karzartools.com/' | grep -iE 'HTTP/|strict-transport|content-security' | head -10
curl -s 'https://api.karzartools.com/api/v1/products/?page=1&page_size=3' | python3 -c 'import sys,json; d=json.load(sys.stdin); print([(x.get("id"), (x.get("thumbnail") or "")[:60]) for x in d.get("data",[])])'

echo "DONE"
