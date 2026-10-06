#!/usr/bin/env bash
# Owner-authorized INSIZE workbook trailing-A alias price reconciliation.
set -euo pipefail

CONFIRM_TOKEN="owner_insize_workbook_trailing_a_reconcile_2026_10_06"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT_DIR="/opt/karzar/Karzar/_ops/input"
AUDIT_DIR="${ROOT}/audit/insize-price-20-trailing-a"
WORKBOOK_BASENAME="WORKBOOK_65a92337.xlsx"
REMOTE_NAME="موجودی توزیع کننده 11 شهریور - افزایش 20 درصدی.xlsx"
EXPECTED_SHA="65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a"
LIB_SRC="${ROOT}/scripts/insize_sales_activation_lib.py"
SCRIPT_SRC="${ROOT}/scripts/ops/insize_workbook_trailing_a_price_reconcile.py"

if [ "${KARZAR_INSIZE_TRAILING_A_CONFIRM:-}" != "$CONFIRM_TOKEN" ]; then
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

# Prefer already-verified input workbook; fall back to prior audit copy.
if [ -f "${INPUT_DIR}/${REMOTE_NAME}" ]; then
  SRC="${INPUT_DIR}/${REMOTE_NAME}"
elif [ -f "${ROOT}/audit/insize-price-20-workbook/${WORKBOOK_BASENAME}" ]; then
  SRC="${ROOT}/audit/insize-price-20-workbook/${WORKBOOK_BASENAME}"
  cp -f "$SRC" "${INPUT_DIR}/${REMOTE_NAME}"
  SRC="${INPUT_DIR}/${REMOTE_NAME}"
else
  echo "STATUS=BLOCKED_WORKBOOK_MISSING"
  exit 13
fi

REMOTE_SHA="$(sha256sum "$SRC" | awk '{print $1}')"
if [ "$REMOTE_SHA" != "$EXPECTED_SHA" ]; then
  echo "STATUS=BLOCKED_SHA remote=${REMOTE_SHA}"
  exit 14
fi
echo "workbook_path=${SRC}"
echo "sha256=${REMOTE_SHA}"

CONTAINER_XLSX="/tmp/insize_distributor_workbook_65a92337.xlsx"
CONTAINER_OUT="/tmp/insize-price-20-trailing-a-audit"

run_py() {
  docker cp "$LIB_SRC" lathe_api:/app/scripts/insize_sales_activation_lib.py
  docker cp "$SCRIPT_SRC" lathe_api:/app/scripts/ops/insize_workbook_trailing_a_price_reconcile.py
  docker cp "$SRC" "lathe_api:${CONTAINER_XLSX}"
  docker exec lathe_api mkdir -p /app/scripts/ops "$CONTAINER_OUT"
  set +e
  docker exec \
    -e KARZAR_ALLOW_PRODUCTION_WRITE=1 \
    -e KARZAR_INGESTION_CATEGORY=B \
    -e KARZAR_INSIZE_WORKBOOK_SYNC_INSIDE_API=1 \
    lathe_api \
    python /app/scripts/ops/insize_workbook_trailing_a_price_reconcile.py \
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

if [ "${KARZAR_INSIZE_TRAILING_A_APPLY:-0}" = "1" ]; then
  echo "=== APPLY ==="
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  run_py \
    --apply \
    --skip-identity \
    --confirm-production-write \
    --recovery-snapshot-path "${CONTAINER_OUT}/RECOVERY_TRAILING_A_${STAMP}.json" || {
    echo "STATUS=APPLY_FAILED"
    exit 30
  }
  echo "=== IDEMPOTENT_RERUN ==="
  run_py --skip-identity || true
fi

echo "STATUS=OK"
