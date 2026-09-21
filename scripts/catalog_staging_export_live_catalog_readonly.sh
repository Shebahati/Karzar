#!/usr/bin/env bash
# Read-only catalog export from CR-011 live (Production) for isolated staging seed.
#
# SAFETY:
# - Uses SSH + docker exec psql/pg_dump against live ONLY in read-only dump mode
# - Does NOT mutate live
# - Exports catalog tables only (no users/orders/payments/tokens)
# - Writes under /tmp (never commit)
#
# Usage:
#   bash scripts/catalog_staging_export_live_catalog_readonly.sh /tmp/catalog-seed-DIR
set -euo pipefail

OUT_DIR="${1:?Usage: $0 /tmp/out-dir}"
mkdir -p "${OUT_DIR}"
HOST_ALIAS="${KARZAR_LIVE_SSH_HOST:-karzar-vps}"
LIVE_DB_USER="${KARZAR_LIVE_DB_USER:-karzar_staging}"
LIVE_DB_NAME="${KARZAR_LIVE_DB_NAME:-karzar_staging}"

# Catalog-only table allowlist (FK-complete for products).
TABLES=(
  brands
  categories
  product_types
  products
  product_images
)

{
  echo "export_started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "ssh_host=${HOST_ALIAS}"
  echo "live_db=${LIVE_DB_NAME}"
  echo "tables=${TABLES[*]}"
  echo "mode=READ_ONLY_PG_DUMP_DATA_ONLY"
} > "${OUT_DIR}/export_meta.txt"

DUMP="${OUT_DIR}/catalog_only.dump"
# Custom-format data-only dump of allowlisted tables (schema already from Alembic).
ssh -o BatchMode=yes "${HOST_ALIAS}" \
  "docker exec lathe_postgres pg_dump -U ${LIVE_DB_USER} -d ${LIVE_DB_NAME} \
    --format=custom --data-only --no-owner --no-privileges \
    $(printf -- '-t %s ' "${TABLES[@]}")" \
  > "${DUMP}"

sha256sum "${DUMP}" | tee "${OUT_DIR}/catalog_only.dump.sha256"
# Capture live counts for later comparison (read-only)
ssh -o BatchMode=yes "${HOST_ALIAS}" \
  "docker exec -i lathe_postgres psql -U ${LIVE_DB_USER} -d ${LIVE_DB_NAME} -v ON_ERROR_STOP=1" \
  > "${OUT_DIR}/live_counts.txt" <<'SQL'
BEGIN READ ONLY;
SELECT
  (SELECT COUNT(*) FROM products WHERE deleted_at IS NULL) AS live_products,
  (SELECT COUNT(*) FROM products p JOIN brands b ON b.id=p.brand_id
     WHERE p.deleted_at IS NULL AND b.id=8) AS zcc_ct,
  (SELECT COUNT(*) FROM products p JOIN brands b ON b.id=p.brand_id
     WHERE p.deleted_at IS NULL AND b.id=20) AS san_ou,
  (SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND id BETWEEN 7116 AND 7290) AS active_cohort,
  (SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND id BETWEEN 7291 AND 7599) AS draft_cohort;
ROLLBACK;
SQL

echo "OK export -> ${DUMP}"
