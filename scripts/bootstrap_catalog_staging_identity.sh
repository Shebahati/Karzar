#!/usr/bin/env bash
# Bootstrap / flip environment_identity sentinel for catalog-staging DB only.
# Usage (after migrations against catalog-staging):
#   POSTGRES_* + KARZAR_DATA_PLANE=catalog_staging \
#     bash scripts/bootstrap_catalog_staging_identity.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${POSTGRES_SERVER:?}"
: "${POSTGRES_PORT:?}"
: "${POSTGRES_USER:?}"
: "${POSTGRES_PASSWORD:?}"
: "${POSTGRES_DB:?}"

if [[ "${KARZAR_DATA_PLANE:-}" != "catalog_staging" ]]; then
  echo "FATAL: KARZAR_DATA_PLANE must be catalog_staging" >&2
  exit 2
fi
if [[ "${POSTGRES_DB}" == "karzar_staging" ]]; then
  echo "FATAL: refusing to mark live DB name karzar_staging as catalog_staging" >&2
  exit 2
fi
if [[ "${POSTGRES_DB}" != "karzar_catalog_staging" && "${POSTGRES_DB}" != "${KARZAR_CATALOG_STAGING_DB_NAME:-karzar_catalog_staging}" ]]; then
  echo "FATAL: unexpected POSTGRES_DB=${POSTGRES_DB}" >&2
  exit 2
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"
psql -h "${POSTGRES_SERVER}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO environment_identity (id, plane, label, notes)
VALUES (
  1,
  'catalog_staging',
  'karzar-catalog-staging',
  'Isolated catalog rehearsal plane — not CR-011 live'
)
ON CONFLICT (id) DO UPDATE
SET plane = EXCLUDED.plane,
    label = EXCLUDED.label,
    notes = EXCLUDED.notes;
SELECT id, plane, label FROM environment_identity WHERE id = 1;
SQL
echo "OK: environment_identity.plane=catalog_staging"
