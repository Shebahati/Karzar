#!/bin/bash
# Read-only live census for a possible non-INSIZE +20% price change.
# Refuses SQL that is not a SELECT/SHOW/transaction script. Does not deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SQL_DIR="${ROOT}/scripts/ops"

forbid_writes() {
  local file="$1"
  if grep -Eiq '(^|;)[[:space:]]*(insert|update|delete|alter|drop|truncate|create|grant|revoke|copy|call|do|merge)[[:space:]]' "$file"; then
    echo "REFUSING non-read SQL in ${file}" >&2
    exit 1
  fi
}

for f in \
  non_insize_price_audit_brand.sql \
  non_insize_price_audit_fingerprint.sql \
  non_insize_price_audit_global.sql \
  non_insize_price_audit_census.sql
do
  forbid_writes "${SQL_DIR}/${f}"
done

echo "=== IDENTITY ==="
echo "hostname=$(hostname)"
echo "utc_now=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "runner_user=$(id -un)"

if ! docker inspect lathe_api >/dev/null 2>&1; then
  echo "ERROR: lathe_api not found" >&2
  exit 1
fi
if ! docker inspect lathe_postgres >/dev/null 2>&1; then
  echo "ERROR: lathe_postgres not found" >&2
  exit 1
fi

echo "api_name=$(docker inspect -f '{{.Name}}' lathe_api)"
echo "api_image=$(docker inspect -f '{{.Config.Image}}' lathe_api)"
echo "api_image_id=$(docker inspect -f '{{.Image}}' lathe_api)"
echo "api_status=$(docker inspect -f '{{.State.Status}}' lathe_api)"
echo "api_started=$(docker inspect -f '{{.State.StartedAt}}' lathe_api)"
echo "postgres_name=$(docker inspect -f '{{.Name}}' lathe_postgres)"
echo "postgres_image=$(docker inspect -f '{{.Config.Image}}' lathe_postgres)"
echo "postgres_status=$(docker inspect -f '{{.State.Status}}' lathe_postgres)"
pg_started_before="$(docker inspect -f '{{.State.StartedAt}}' lathe_postgres)"
redis_started_before="$(docker inspect -f '{{.State.StartedAt}}' lathe_redis 2>/dev/null || true)"
echo "postgres_started=${pg_started_before}"
echo "redis_started=${redis_started_before}"
echo "postgres_mounts<<EOF"
docker inspect -f '{{range .Mounts}}{{.Type}}|{{.Name}}|{{.Destination}}{{println}}{{end}}' lathe_postgres
echo "EOF"

allow_env() {
  local key="$1"
  local raw
  raw="$(docker exec lathe_api printenv "$key" 2>/dev/null || true)"
  case "$key" in
    PURCHASE_CHECKOUT_ENABLED)
      case "$raw" in
        true|false|"") echo "${key}=${raw:-unset}" ;;
        *) echo "ERROR: ${key} is not a boolean" >&2; exit 1 ;;
      esac
      ;;
    *)
      echo "${key}=${raw:-unset}"
      ;;
  esac
}

allow_env APP_ENV
allow_env KARZAR_DATA_PLANE
allow_env PURCHASE_CHECKOUT_ENABLED
allow_env POSTGRES_SERVER
allow_env POSTGRES_PORT
allow_env POSTGRES_DB

echo "postgres_db_container=$(docker exec lathe_postgres printenv POSTGRES_DB 2>/dev/null || true)"
echo "alembic_current<<EOF"
docker exec lathe_api alembic current 2>&1 | sed -n '1,20p' || true
echo "EOF"

if [ -d /opt/karzar/Karzar/.git ]; then
  echo "vps_checkout_sha=$(git -C /opt/karzar/Karzar rev-parse HEAD)"
  echo "vps_checkout_branch=$(git -C /opt/karzar/Karzar rev-parse --abbrev-ref HEAD)"
else
  echo "vps_checkout_sha=MISSING"
fi

run_sql() {
  local file="$1"
  shift
  docker exec -i \
    -e PGOPTIONS='-c default_transaction_read_only=on' \
    lathe_postgres \
    sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -f - "$@"' \
    psql "$@" < "$file"
}

echo "=== FINGERPRINT_BEFORE ==="
fp_before="$(run_sql "${SQL_DIR}/non_insize_price_audit_fingerprint.sql" | awk '/^[0-9a-f]{32}$/ {print; exit}')"
echo "catalog_fingerprint_before=${fp_before:-MISSING}"

echo "=== GLOBAL ==="
run_sql "${SQL_DIR}/non_insize_price_audit_global.sql"

echo "=== INSIZE_CANDIDATES ==="
brand_out="$(run_sql "${SQL_DIR}/non_insize_price_audit_brand.sql")"
printf '%s\n' "$brand_out"
insize_id="$(
  printf '%s\n' "$brand_out" | python3 -c '
import json, sys
rows = []
for line in sys.stdin:
    line = line.strip()
    if not line.startswith("{"):
        continue
    rows.append(json.loads(line))
print(len(rows))
if len(rows) == 1:
    print(rows[0]["id"])
'
)"
candidate_count="$(printf '%s\n' "$insize_id" | sed -n '1p')"
resolved_id="$(printf '%s\n' "$insize_id" | sed -n '2p')"
echo "insize_candidate_count=${candidate_count}"

if [ "${candidate_count}" = "1" ] && printf '%s' "${resolved_id}" | grep -Eq '^[0-9]+$'; then
  echo "insize_resolved_id=${resolved_id}"
  echo "=== CENSUS ==="
  run_sql "${SQL_DIR}/non_insize_price_audit_census.sql" -v "insize_id=${resolved_id}"
else
  echo "insize_resolved_id=NONE"
  echo "CENSUS_SKIPPED=brand_not_unique"
fi

echo "=== FINGERPRINT_AFTER ==="
fp_after="$(run_sql "${SQL_DIR}/non_insize_price_audit_fingerprint.sql" | awk '/^[0-9a-f]{32}$/ {print; exit}')"
echo "catalog_fingerprint_after=${fp_after:-MISSING}"
if [ -n "${fp_before}" ] && [ "${fp_before}" = "${fp_after}" ]; then
  echo "catalog_fingerprint_unchanged=YES"
else
  echo "catalog_fingerprint_unchanged=NO"
fi

pg_started_after="$(docker inspect -f '{{.State.StartedAt}}' lathe_postgres)"
redis_started_after="$(docker inspect -f '{{.State.StartedAt}}' lathe_redis 2>/dev/null || true)"
if [ "${pg_started_after}" = "${pg_started_before}" ]; then
  echo "postgres_restarted=NO"
else
  echo "postgres_restarted=YES"
fi
if [ "${redis_started_after}" = "${redis_started_before}" ]; then
  echo "redis_restarted=NO"
else
  echo "redis_restarted=YES"
fi

echo "=== COMMERCE_FREEZE ==="
probe_host="$(python3 - <<'PY'
from pathlib import Path
host = ""
path = Path("/opt/karzar/Karzar/.env")
if path.exists():
    for line in path.read_bytes().splitlines():
        if line.startswith(b"TRUSTED_HOSTS="):
            raw = line.split(b"=", 1)[1].strip().strip(b"\"'").decode("utf-8", "replace")
            host = raw.split(",")[0].strip()
            break
print(host or "api.karzartools.com")
PY
)"
echo "probe_host=${probe_host}"
status_file="$(mktemp)"
status_code="$(curl -sS -o "$status_file" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" \
  -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8000/api/v1/commerce/purchase-status || true)"
echo "purchase_status_http=${status_code}"
python3 - "$status_file" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("purchase_checkout_enabled=unparsed")
    raise SystemExit(0)
enabled = data.get("purchase_checkout_enabled")
print("purchase_checkout_enabled=%s" % enabled)
message = data.get("message")
print("purchase_status_message_present=%s" % ("YES" if message else "NO"))
PY
rm -f "$status_file"

echo "HESABFA_WRITE_THIS_PHASE=NO"
echo "MUTATION_PERFORMED=NO"
echo "AUDIT_COMPLETE=YES"

if [ "${fp_before}" != "${fp_after}" ]; then
  echo "ERROR: catalog fingerprint changed during a read-only audit" >&2
  exit 2
fi
