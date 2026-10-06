#!/bin/bash
# Owner-authorized INSIZE distributor workbook (+20% in workbook) base_price sync.
set -euo pipefail

CONFIRM_TOKEN="owner_insize_distributor_workbook_price_sync_20pct_2026_10_06"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT_DIR="/opt/karzar/Karzar/_ops/input"
AUDIT_DIR="${ROOT}/audit/insize-price-20-workbook"
WORKBOOK_BASENAME="WORKBOOK_65a92337.xlsx"
REMOTE_NAME="موجودی توزیع کننده 11 شهریور - افزایش 20 درصدی.xlsx"
EXPECTED_SHA="65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a"

if [ "${KARZAR_INSIZE_WORKBOOK_SYNC_CONFIRM:-}" != "$CONFIRM_TOKEN" ]; then
  echo "STATUS=BLOCKED_CONFIRM_TOKEN"
  exit 10
fi

echo "=== IDENTITY ==="
echo "hostname=$(hostname)"
if [ "$(hostname)" != "srv5944957438" ]; then
  echo "STATUS=BLOCKED_HOSTNAME"
  exit 11
fi
if ! docker inspect lathe_api >/dev/null 2>&1 || ! docker inspect lathe_postgres >/dev/null 2>&1; then
  echo "STATUS=BLOCKED_CONTAINERS"
  exit 12
fi

mkdir -p "$INPUT_DIR" "$AUDIT_DIR"
SRC="${ROOT}/audit/insize-price-20-workbook/${WORKBOOK_BASENAME}"
if [ ! -f "$SRC" ]; then
  echo "STATUS=BLOCKED_WORKBOOK_MISSING checkout=${SRC}"
  exit 13
fi
LOCAL_SHA="$(sha256sum "$SRC" | awk '{print $1}')"
if [ "$LOCAL_SHA" != "$EXPECTED_SHA" ]; then
  echo "STATUS=BLOCKED_SHA local=${LOCAL_SHA}"
  exit 14
fi
DEST="${INPUT_DIR}/${REMOTE_NAME}"
cp -f "$SRC" "$DEST"
REMOTE_SHA="$(sha256sum "$DEST" | awk '{print $1}')"
echo "local_path=${SRC}"
echo "remote_path=${DEST}"
echo "sha256=${REMOTE_SHA}"

export KARZAR_ALLOW_PRODUCTION_WRITE=1
export KARZAR_INGESTION_CATEGORY=B

CONTAINER_XLSX="/tmp/insize_distributor_workbook_65a92337.xlsx"
CONTAINER_OUT="/tmp/insize-price-20-workbook-audit"

run_py() {
  docker cp "${ROOT}/scripts/ops/insize_distributor_price_workbook_sync.py" \
    lathe_api:/app/scripts/ops/insize_distributor_price_workbook_sync.py
  docker cp "$DEST" "lathe_api:${CONTAINER_XLSX}"
  docker exec lathe_api mkdir -p "$CONTAINER_OUT"
  set +e
  docker exec \
    -e KARZAR_ALLOW_PRODUCTION_WRITE=1 \
    -e KARZAR_INGESTION_CATEGORY=B \
    -e KARZAR_INSIZE_WORKBOOK_SYNC_INSIDE_API=1 \
    lathe_api \
    python /app/scripts/ops/insize_distributor_price_workbook_sync.py \
    --xlsx "$CONTAINER_XLSX" \
    --out-dir "$CONTAINER_OUT" \
    "$@"
  code=$?
  set -e
  docker cp "lathe_api:${CONTAINER_OUT}/." "$AUDIT_DIR/" 2>/dev/null || true
  return "$code"
}

echo "=== DRY_RUN ==="
run_py --skip-identity || {
  echo "STATUS=BLOCKED_DRY_RUN"
  exit 20
}

if [ "${KARZAR_INSIZE_WORKBOOK_SYNC_APPLY:-0}" = "1" ]; then
  echo "=== APPLY ==="
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  run_py \
    --apply \
    --skip-identity \
    --confirm-production-write \
    --recovery-snapshot-path "${CONTAINER_OUT}/RECOVERY_PREWRITE_${STAMP}.json" || {
    echo "STATUS=APPLY_FAILED"
    exit 30
  }
  echo "=== IDEMPOTENT_RERUN ==="
  run_py --skip-identity || true
fi

echo "STATUS=OK"
