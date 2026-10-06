#!/usr/bin/env bash
# Owner-authorized PROVEN INSIZE 1205-*02 → *02S identity-alias price apply.
set -euo pipefail

CONFIRM_TOKEN="owner_insize_1205_02s_identity_alias_2026_10_06"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT_DIR="/opt/karzar/Karzar/_ops/input"
AUDIT_DIR="${ROOT}/audit/insize-price-20-1205-02s"
REMOTE_NAME="موجودی توزیع کننده 11 شهریور - افزایش 20 درصدی.xlsx"
EXPECTED_SHA="65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a"

if [ "${KARZAR_INSIZE_1205_02S_CONFIRM:-}" != "$CONFIRM_TOKEN" ]; then
  echo "STATUS=BLOCKED_CONFIRM_TOKEN"
  exit 10
fi

if [ "$(hostname)" != "srv5944957438" ]; then
  echo "STATUS=BLOCKED_HOSTNAME"
  exit 11
fi

mkdir -p "$AUDIT_DIR"
SRC="${INPUT_DIR}/${REMOTE_NAME}"
REMOTE_SHA="$(sha256sum "$SRC" | awk '{print $1}')"
if [ "$REMOTE_SHA" != "$EXPECTED_SHA" ]; then
  echo "STATUS=BLOCKED_SHA"
  exit 14
fi

CONTAINER_XLSX="/tmp/insize_distributor_workbook_65a92337.xlsx"
CONTAINER_OUT="/tmp/insize-1205-02s-audit"
CONTAINER_ALIAS_CSV="/tmp/INSIZE_SITE_TO_SOURCE_CODE_ALIASES.csv"

run_py() {
  docker cp "${ROOT}/scripts/insize_sales_activation_lib.py" \
    lathe_api:/app/scripts/insize_sales_activation_lib.py
  docker cp "${ROOT}/scripts/ops/insize_1205_02s_identity_alias_apply.py" \
    lathe_api:/app/scripts/ops/insize_1205_02s_identity_alias_apply.py
  docker cp "${ROOT}/docs/architecture/specs/product-naming-v1/INSIZE_SITE_TO_SOURCE_CODE_ALIASES.csv" \
    "lathe_api:${CONTAINER_ALIAS_CSV}"
  docker cp "$SRC" "lathe_api:${CONTAINER_XLSX}"
  docker exec lathe_api mkdir -p /app/scripts/ops "$CONTAINER_OUT"
  set +e
  docker exec \
    -e KARZAR_ALLOW_PRODUCTION_WRITE=1 \
    -e KARZAR_INGESTION_CATEGORY=B \
    -e KARZAR_INSIZE_WORKBOOK_SYNC_INSIDE_API=1 \
    lathe_api \
    python /app/scripts/ops/insize_1205_02s_identity_alias_apply.py \
    --xlsx "$CONTAINER_XLSX" \
    --alias-csv "$CONTAINER_ALIAS_CSV" \
    --out-dir "$CONTAINER_OUT" \
    "$@"
  code=$?
  set -e
  docker cp "lathe_api:${CONTAINER_OUT}/." "$AUDIT_DIR/" 2>/dev/null || true
  return "$code"
}

echo "=== DRY_RUN ==="
run_py || {
  echo "STATUS=BLOCKED_DRY_RUN"
  exit 20
}

if [ "${KARZAR_INSIZE_1205_02S_APPLY:-0}" = "1" ]; then
  echo "=== APPLY ==="
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  run_py \
    --apply \
    --confirm-production-write \
    --recovery-snapshot-path "${CONTAINER_OUT}/RECOVERY_1205_02S_${STAMP}.json" || {
    echo "STATUS=APPLY_FAILED"
    exit 30
  }
  echo "=== IDEMPOTENT_RERUN ==="
  run_py || true
fi

echo "STATUS=OK"
