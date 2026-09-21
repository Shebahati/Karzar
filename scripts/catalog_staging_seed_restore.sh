#!/usr/bin/env bash
# Restore catalog-only dump into isolated catalog-staging DB.
# Requires: migrations applied, environment_identity bootstrapped, dump from export script.
set -euo pipefail

DUMP="${1:?Usage: $0 /path/to/catalog_only.dump}"
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
  echo "FATAL: refusing restore into live DB name" >&2
  exit 2
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"
echo "Pre-seed counts:"
psql -h "${POSTGRES_SERVER}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c \
  "SELECT COUNT(*) AS products FROM products; SELECT plane FROM environment_identity WHERE id=1;"

# Truncate catalog tables in FK-safe order inside staging only
psql -h "${POSTGRES_SERVER}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
TRUNCATE product_images, products, product_types, categories, brands RESTART IDENTITY CASCADE;
COMMIT;
SQL

# pg_restore data-only; disable triggers briefly if needed — custom format with --data-only
# Prefer host pg_restore; operators may instead:
# docker cp DUMP karzar_catalog_staging_db:/tmp/ && docker exec ... pg_restore
pg_restore -h "${POSTGRES_SERVER}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  --data-only --no-owner --no-privileges --disable-triggers \
  "${DUMP}" || {
    # Some Postgres builds need session_replication_role instead
    echo "pg_restore with --disable-triggers failed; retrying via session_replication_role" >&2
    psql -h "${POSTGRES_SERVER}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 \
      -c "SELECT set_config('session_replication_role','replica',false);"
    # Prefer host pg_restore; operators may instead:
# docker cp DUMP karzar_catalog_staging_db:/tmp/ && docker exec ... pg_restore
pg_restore -h "${POSTGRES_SERVER}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
      --data-only --no-owner --no-privileges "${DUMP}"
    psql -h "${POSTGRES_SERVER}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 \
      -c "SELECT set_config('session_replication_role','origin',false);"
  }

# Re-assert sentinel after restore (truncate may have wiped it if FK cascade — it shouldn't;
# environment_identity is separate. Re-upsert anyway.)
psql -h "${POSTGRES_SERVER}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO environment_identity (id, plane, label, notes)
VALUES (1, 'catalog_staging', 'karzar-catalog-staging', 'restored after catalog seed')
ON CONFLICT (id) DO UPDATE SET plane='catalog_staging', label=EXCLUDED.label, notes=EXCLUDED.notes;
SELECT COUNT(*) AS products FROM products;
SELECT plane FROM environment_identity WHERE id=1;
SQL
echo "OK seed restore"
