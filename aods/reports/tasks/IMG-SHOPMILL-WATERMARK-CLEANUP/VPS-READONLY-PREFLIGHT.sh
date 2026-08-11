#!/usr/bin/env bash
# READ-ONLY ShopMill production preflight for the live VPS.
# Paste on the VPS after this branch's scripts/manifests are present under /opt/karzar/Karzar.
# Does NOT apply repairs, backup uploads, chmod, restore, restart, or deploy.
set -euo pipefail

REPO="${REPO:-/opt/karzar/Karzar}"
cd "$REPO"

REPORT_DIR="/tmp/karzar-shopmill-preflight-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$REPORT_DIR"

echo "==> Discover backend container with /app/data/uploads mount"
mapfile -t CANDIDATES < <(docker ps --format '{{.ID}} {{.Names}}' )
BACKEND_CONTAINER=""
UPLOADS_DEST=""
for line in "${CANDIDATES[@]:-}"; do
  cid="${line%% *}"
  # Look for a mount whose Destination is exactly /app/data/uploads
  dest="$(docker inspect -f '{{range .Mounts}}{{println .Destination}}{{end}}' "$cid" | grep -x '/app/data/uploads' || true)"
  if [[ -n "$dest" ]]; then
    BACKEND_CONTAINER="$(docker inspect -f '{{.Name}}' "$cid" | sed 's#^/##')"
    UPLOADS_DEST="/app/data/uploads"
    break
  fi
done

if [[ -z "${BACKEND_CONTAINER}" ]]; then
  echo "ERROR: no running container with mount Destination=/app/data/uploads" >&2
  docker ps
  exit 1
fi

echo "==> Resolve volume/bind source for /app/data/uploads"
UPLOADS_VOLUME="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/app/data/uploads"}}{{println .Name}}{{end}}{{end}}' "$BACKEND_CONTAINER" | head -n1 | tr -d '\r')"
UPLOADS_SOURCE="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/app/data/uploads"}}{{println .Source}}{{end}}{{end}}' "$BACKEND_CONTAINER" | head -n1 | tr -d '\r')"
UPLOADS_TYPE="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/app/data/uploads"}}{{println .Type}}{{end}}{{end}}' "$BACKEND_CONTAINER" | head -n1 | tr -d '\r')"

if [[ "${UPLOADS_TYPE}" == "volume" && -n "${UPLOADS_VOLUME}" ]]; then
  UPLOADS_VOLUME_MOUNTPOINT="$(docker volume inspect -f '{{.Mountpoint}}' "$UPLOADS_VOLUME")"
elif [[ -n "${UPLOADS_SOURCE}" ]]; then
  # Bind mount or unnamed volume source path already on host
  UPLOADS_VOLUME="${UPLOADS_VOLUME:-bind:${UPLOADS_SOURCE}}"
  UPLOADS_VOLUME_MOUNTPOINT="${UPLOADS_SOURCE}"
else
  echo "ERROR: could not resolve uploads mount for ${BACKEND_CONTAINER}" >&2
  docker inspect "$BACKEND_CONTAINER" | head -n 200
  exit 1
fi

if [[ -z "${UPLOADS_VOLUME_MOUNTPOINT}" || ! -d "${UPLOADS_VOLUME_MOUNTPOINT}" ]]; then
  echo "ERROR: volume mountpoint missing: ${UPLOADS_VOLUME_MOUNTPOINT:-<empty>}" >&2
  exit 1
fi

PRODUCTS_STORAGE_ROOT="${UPLOADS_VOLUME_MOUNTPOINT}/products"
if [[ ! -d "${PRODUCTS_STORAGE_ROOT}" ]]; then
  echo "ERROR: PRODUCTS_STORAGE_ROOT does not exist: ${PRODUCTS_STORAGE_ROOT}" >&2
  exit 1
fi

{
  echo "BACKEND_CONTAINER=${BACKEND_CONTAINER}"
  echo "UPLOADS_VOLUME=${UPLOADS_VOLUME}"
  echo "UPLOADS_VOLUME_MOUNTPOINT=${UPLOADS_VOLUME_MOUNTPOINT}"
  echo "PRODUCTS_STORAGE_ROOT=${PRODUCTS_STORAGE_ROOT}"
  echo "REPORT_DIR=${REPORT_DIR}"
} | tee "${REPORT_DIR}/discovery.env"

echo "==> Read-only storage spot checks"
ls -ld "${PRODUCTS_STORAGE_ROOT}"
echo -n "file_count="
find "${PRODUCTS_STORAGE_ROOT}" -type f | wc -l
echo -n "total_size="
du -sh "${PRODUCTS_STORAGE_ROOT}" | awk '{print $1}'
echo "sample_paths:"
find "${PRODUCTS_STORAGE_ROOT}" -type f | head -n 5

MANIFEST="${REPO}/aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/remediation-manifest.durable-paths.csv"
if [[ ! -f "${MANIFEST}" ]]; then
  MANIFEST="${REPO}/aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/remediation-manifest.csv"
fi
if [[ ! -f "${MANIFEST}" ]]; then
  echo "ERROR: remediation manifest not found under ${REPO}/aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/" >&2
  exit 1
fi

echo "==> Run READ-ONLY preflight (reports only under ${REPORT_DIR})"
python3 "${REPO}/scripts/shopmill_production_preflight.py" \
  --manifest "${MANIFEST}" \
  --products-storage-root "${PRODUCTS_STORAGE_ROOT}" \
  --report-dir "${REPORT_DIR}" \
  --expected-target-paths 410 \
  --expected-unique-assets 163

echo "==> Done. Review:"
echo "  ${REPORT_DIR}/preflight-summary.txt"
echo "  ${REPORT_DIR}/preflight-per-path.csv"
echo "  ${REPORT_DIR}/preflight-report.json"
echo "NO PRODUCTION PRODUCT IMAGE WAS MODIFIED BY THIS PREFLIGHT."
