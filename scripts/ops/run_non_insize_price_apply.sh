#!/bin/bash
# Owner-authorized non-INSIZE +20% catalog price apply.
# Refuses to run unless the workflow sets the confirm token.
# Does not print the price manifest.
set -euo pipefail

CONFIRM_TOKEN="owner_non_insize_price_increase_20pct_2026_09_29"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SQL_DIR="${ROOT}/scripts/ops"
BACKUP_DIR="/opt/karzar/rollout-backups/non-insize-price-20pct-2026-09-29"
STATUS="BLOCKED_NO_MUTATION"
WRITE_STARTED=0
TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

finish() {
  local code="$1"
  echo "STATUS=${STATUS}"
  echo "MUTATION_PHASE_EXIT=${code}"
  exit "$code"
}

blocked() {
  STATUS="BLOCKED_NO_MUTATION"
  echo "BLOCK_REASON=$1"
  finish 10
}

rolled_back() {
  STATUS="ROLLED_BACK_BEFORE_COMMIT"
  echo "ROLLBACK_REASON=$1"
  finish 20
}

rollback_required() {
  STATUS="ROLLBACK_REQUIRED"
  echo "ROLLBACK_REQUIRED_REASON=$1"
  if [ -n "${MANIFEST_PATH:-}" ]; then
    echo "ROLLBACK_ARTIFACT=${MANIFEST_PATH}"
    echo "MANIFEST_SHA256=${MANIFEST_SHA256:-MISSING}"
  fi
  finish 30
}

if [ "${KARZAR_PRICE_APPLY_CONFIRM:-}" != "$CONFIRM_TOKEN" ]; then
  blocked "confirm_token_missing"
fi

echo "=== IDENTITY ==="
echo "hostname=$(hostname)"
echo "utc_now=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [ "$(hostname)" != "srv5944957438" ]; then
  blocked "hostname"
fi
if ! docker inspect lathe_api >/dev/null 2>&1 || ! docker inspect lathe_postgres >/dev/null 2>&1; then
  blocked "containers_missing"
fi
api_name="$(docker inspect -f '{{.Name}}' lathe_api)"
pg_name="$(docker inspect -f '{{.Name}}' lathe_postgres)"
pg_mount="$(docker inspect -f '{{range .Mounts}}{{.Name}}{{println}}{{end}}' lathe_postgres)"
api_db="$(docker exec lathe_api printenv POSTGRES_DB)"
api_server="$(docker exec lathe_api printenv POSTGRES_SERVER)"
app_env="$(docker exec lathe_api printenv APP_ENV)"
data_plane="$(docker exec lathe_api printenv KARZAR_DATA_PLANE || true)"
purchase_flag="$(docker exec lathe_api printenv PURCHASE_CHECKOUT_ENABLED)"
alembic_line="$(docker exec lathe_api alembic current 2>/dev/null | awk '/t3u4v5w6x7y8/ {print; exit}' || true)"
echo "api_name=${api_name}"
echo "postgres_name=${pg_name}"
echo "postgres_mount=${pg_mount}"
echo "postgres_db=${api_db}"
echo "postgres_server=${api_server}"
echo "app_env=${app_env}"
echo "data_plane=${data_plane:-unset}"
echo "purchase_checkout_enabled=${purchase_flag}"
echo "alembic=${alembic_line}"
echo "api_image=$(docker inspect -f '{{.Config.Image}}' lathe_api)"
echo "api_image_id=$(docker inspect -f '{{.Image}}' lathe_api)"
if [ "$api_name" != "/lathe_api" ] || [ "$pg_name" != "/lathe_postgres" ]; then
  blocked "container_name"
fi
if [ "$pg_mount" != "karzar_postgres_data" ] || [ "$api_db" != "karzar_staging" ] || [ "$api_server" != "db" ]; then
  blocked "data_plane_identity"
fi
if [ "$app_env" != "staging" ]; then
  blocked "app_env"
fi
if [ -n "$data_plane" ]; then
  blocked "data_plane_explicit"
fi
if [ "$purchase_flag" != "false" ]; then
  blocked "purchase_flag"
fi
if [ "$alembic_line" != "t3u4v5w6x7y8 (head)" ] && [ "$alembic_line" != "t3u4v5w6x7y8" ]; then
  blocked "alembic"
fi

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
status_file="${TMP_DIR}/purchase-status.json"
status_code="$(curl -sS -o "$status_file" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" \
  -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8000/api/v1/commerce/purchase-status || true)"
purchase_enabled="$(python3 - "$status_file" <<'PY'
import json, sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print("unparsed")
    raise SystemExit(0)
print(str(data.get("purchase_checkout_enabled")).lower())
PY
)"
echo "purchase_status_http=${status_code}"
echo "purchase_status_enabled=${purchase_enabled}"
if [ "$status_code" != "200" ] || [ "$purchase_enabled" != "false" ]; then
  blocked "commerce_not_frozen"
fi
echo "COMMERCE_FREEZE_BEFORE=false"

psql_read() {
  docker exec -i \
    -e PGOPTIONS='-c default_transaction_read_only=on' \
    lathe_postgres \
    sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -f -' < "$1"
}

echo "=== CENSUS ==="
psql_read "${SQL_DIR}/non_insize_price_apply_export.sql" > "${TMP_DIR}/export.txt" || blocked "export_failed"
python3 - "${TMP_DIR}/export.txt" "${TMP_DIR}/manifest.jsonl" "${TMP_DIR}/insize.jsonl" "${TMP_DIR}/summary.env" <<'PY'
import pathlib, sys
src, manifest_path, insize_path, summary_path = map(pathlib.Path, sys.argv[1:])
lines = src.read_text(encoding="utf-8").splitlines()
section = "summary"
summary = []
manifest = []
insize = []
for line in lines:
    if line == "---MANIFEST---":
        section = "manifest"
        continue
    if line == "---INSIZE---":
        section = "insize"
        continue
    if line == "---END---":
        section = "end"
        continue
    if section == "summary":
        summary.append(line)
    elif section == "manifest":
        manifest.append(line)
    elif section == "insize":
        insize.append(line)
if not manifest or not insize:
    raise SystemExit("export_sections_missing")
manifest_path.write_text("\n".join(manifest) + "\n", encoding="utf-8")
insize_path.write_text("\n".join(insize) + "\n", encoding="utf-8")
summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")
PY
# Summary lines are counts and identity, not row prices.
python3 - "${TMP_DIR}/summary.env" <<'PY'
import pathlib, sys
allowed = {
    "transaction_read_only", "database_name", "insize_candidates", "insize_id",
    "insize_live", "insize_priced", "target_count", "class_a", "class_b",
    "class_c", "class_d", "class_f", "fractional_raw", "change_log_reason_rows",
    "target_mapped", "target_unmapped", "product_triggers",
}
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key in allowed:
        print(f"{key}={value}")
PY
python3 - "${TMP_DIR}/summary.env" "${TMP_DIR}/summary.safe" <<'PY'
import pathlib, sys
allowed = {
    "transaction_read_only", "database_name", "insize_candidates", "insize_id",
    "insize_live", "insize_priced", "target_count", "class_a", "class_b",
    "class_c", "class_d", "class_f", "fractional_raw", "change_log_reason_rows",
    "target_mapped", "target_unmapped", "product_triggers",
}
out = []
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key in allowed and all(ch.isalnum() or ch in "._-" for ch in value):
        out.append(f"{key}={value}")
pathlib.Path(sys.argv[2]).write_text("\n".join(out) + "\n", encoding="utf-8")
PY
python3 - "${TMP_DIR}/summary.env" <<'PY'
import pathlib, sys
vals = {}
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.startswith("insize_name=") or line.startswith("insize_slug="):
        key, value = line.split("=", 1)
        vals[key] = value
name = vals.get("insize_name", "")
slug = vals.get("insize_slug", "")
print("insize_name_present=" + ("YES" if name else "NO"))
print("insize_slug_present=" + ("YES" if slug else "NO"))
PY
insize_name_code=0
python3 - "${TMP_DIR}/summary.env" <<'PY' || insize_name_code=$?
import pathlib, sys
vals = {}
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.startswith("insize_name=") or line.startswith("insize_slug="):
        key, value = line.split("=", 1)
        vals[key] = value
blob = (vals.get("insize_name", "") + " " + vals.get("insize_slug", "")).lower().replace("\u200c", "")
if "insize" not in blob and "اینسایز" not in blob:
    raise SystemExit(2)
PY
if [ "$insize_name_code" -ne 0 ]; then
  blocked "insize_name"
fi
cat "${TMP_DIR}/summary.safe"
set -a
# shellcheck disable=SC1091
source "${TMP_DIR}/summary.safe"
set +a
if [ "${transaction_read_only:-}" != "on" ] || [ "${database_name:-}" != "karzar_staging" ]; then
  blocked "export_identity"
fi
if [ "${insize_candidates:-}" != "1" ] || [ "${insize_id:-}" != "3" ]; then
  blocked "insize_identity"
fi
if [ "${insize_live:-}" != "872" ] || [ "${insize_priced:-}" != "487" ]; then
  blocked "insize_counts"
fi
if [ "${target_count:-}" != "4065" ] || [ "${class_a:-}" != "4058" ] || [ "${class_b:-}" != "7" ]; then
  blocked "target_counts"
fi
if [ "${class_c:-}" != "0" ] || [ "${class_d:-}" != "0" ] || [ "${class_f:-}" != "0" ]; then
  blocked "unexpected_class"
fi
if [ "${fractional_raw:-}" != "17" ]; then
  blocked "fractional_raw"
fi
if [ "${change_log_reason_rows:-}" != "0" ]; then
  blocked "already_applied"
fi
if [ "${target_mapped:-}" != "1994" ] || [ "${target_unmapped:-}" != "2071" ]; then
  blocked "hesabfa_mapping_drift"
fi
if [ "${product_triggers:-}" != "trg_products_updated_at" ]; then
  blocked "product_triggers"
fi

python3 "${SQL_DIR}/non_insize_price_apply_check.py" validate "${TMP_DIR}/manifest.jsonl" \
  > "${TMP_DIR}/validate.txt" || blocked "manifest_decimal_check"
cat "${TMP_DIR}/validate.txt"
MANIFEST_SHA256="$(awk -F= '/^manifest_sha256=/{print $2}' "${TMP_DIR}/validate.txt")"
if [ -z "$MANIFEST_SHA256" ]; then
  blocked "manifest_sha_missing"
fi

echo "=== FINGERPRINT_BEFORE ==="
psql_read "${SQL_DIR}/non_insize_price_apply_fingerprint.sql" > "${TMP_DIR}/fp-before.txt" || blocked "fingerprint_before_failed"
grep -E '^(transaction_read_only|nonprice_fp|insize_price_fp|nontarget_price_fp|orders_fp|order_items_fp|payments_fp)=' "${TMP_DIR}/fp-before.txt"
FP_BEFORE_NONPRICE="$(awk -F= '/^nonprice_fp=/{print $2}' "${TMP_DIR}/fp-before.txt")"
FP_BEFORE_INSIZE="$(awk -F= '/^insize_price_fp=/{print $2}' "${TMP_DIR}/fp-before.txt")"
FP_BEFORE_NONTARGET="$(awk -F= '/^nontarget_price_fp=/{print $2}' "${TMP_DIR}/fp-before.txt")"
FP_BEFORE_ORDERS="$(awk -F= '/^orders_fp=/{print $2}' "${TMP_DIR}/fp-before.txt")"
FP_BEFORE_ITEMS="$(awk -F= '/^order_items_fp=/{print $2}' "${TMP_DIR}/fp-before.txt")"
FP_BEFORE_PAYMENTS="$(awk -F= '/^payments_fp=/{print $2}' "${TMP_DIR}/fp-before.txt")"

echo "=== MANIFEST_STORE ==="
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
MANIFEST_NAME="manifest-${STAMP}.jsonl"
INSIZE_NAME="insize-prices-${STAMP}.jsonl"
META_NAME="meta-${STAMP}.json"
python3 - "$STAMP" "$MANIFEST_SHA256" "${TMP_DIR}/meta.json" <<'PY'
import json, sys
from pathlib import Path
payload = {
    "manifest_generated_at": sys.argv[1],
    "database": "karzar_staging",
    "host": "srv5944957438",
    "insize_brand_id": 3,
    "target_count": 4065,
    "class_a": 4058,
    "class_b": 7,
    "fractional_raw": 17,
    "manifest_sha256": sys.argv[2],
    "alembic": "t3u4v5w6x7y8",
    "reason": "owner_non_insize_price_increase_20pct_2026_09_29",
}
Path(sys.argv[3]).write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
PY
docker run --rm --network none --user 0 --entrypoint sh \
  -v /opt/karzar/rollout-backups:/dest \
  -v "${TMP_DIR}/manifest.jsonl":/src/manifest.jsonl:ro \
  -v "${TMP_DIR}/insize.jsonl":/src/insize.jsonl:ro \
  -v "${TMP_DIR}/meta.json":/src/meta.json:ro \
  postgres:15-alpine \
  -c "set -euo pipefail
      dir=/dest/non-insize-price-20pct-2026-09-29
      mkdir -p \"\$dir\"
      cp /src/manifest.jsonl \"\$dir/${MANIFEST_NAME}\"
      cp /src/insize.jsonl \"\$dir/${INSIZE_NAME}\"
      cp /src/meta.json \"\$dir/${META_NAME}\"
      chown root:root \"\$dir\" \"\$dir/${MANIFEST_NAME}\" \"\$dir/${INSIZE_NAME}\" \"\$dir/${META_NAME}\"
      chmod 700 \"\$dir\"
      chmod 600 \"\$dir/${MANIFEST_NAME}\" \"\$dir/${INSIZE_NAME}\" \"\$dir/${META_NAME}\"
      sha256sum \"\$dir/${MANIFEST_NAME}\"" \
  > "${TMP_DIR}/stored-sha.txt" || blocked "manifest_store_failed"
STORED_SHA="$(awk '{print $1}' "${TMP_DIR}/stored-sha.txt")"
MANIFEST_PATH="${BACKUP_DIR}/${MANIFEST_NAME}"
echo "MANIFEST=${MANIFEST_PATH}"
echo "MANIFEST_SHA256=${STORED_SHA}"
echo "MANIFEST_ROWS=4065"
if [ "$STORED_SHA" != "$MANIFEST_SHA256" ]; then
  blocked "stored_manifest_sha"
fi

echo "=== APPLY ==="
WRITE_STARTED=1
set +e
{
  printf '%s\n' 'BEGIN ISOLATION LEVEL REPEATABLE READ;'
  printf '%s\n' 'CREATE TEMP TABLE manifest_raw (line jsonb);'
  printf '%s\n' 'COPY manifest_raw (line) FROM STDIN;'
  cat "${TMP_DIR}/manifest.jsonl"
  printf '%s\n' '\.'
  cat "${SQL_DIR}/non_insize_price_apply_tx.sql"
} | docker exec -i lathe_postgres \
  sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -f -' \
  > "${TMP_DIR}/apply-out.txt"
apply_code=$?
set -e
grep -E '^(base_price_rows_changed|original_price_rows_changed|insize_price_rows_changed|non_target_price_rows_changed|product_change_log_rows|old_total|raw_total|rounded_total|rounding_delta|target_mapped|target_unmapped|commit_gate|committed)=' \
  "${TMP_DIR}/apply-out.txt" || true
if grep -q 'APPLY_ABORT' "${TMP_DIR}/apply-out.txt"; then
  grep 'APPLY_ABORT' "${TMP_DIR}/apply-out.txt" || true
fi

echo "=== POST_COMMIT ==="
psql_read "${SQL_DIR}/non_insize_price_apply_current.sql" > "${TMP_DIR}/current.txt" || rollback_required "post_export_failed"
python3 - "${TMP_DIR}/current.txt" "${TMP_DIR}/current.jsonl" "${TMP_DIR}/insize-after.jsonl" <<'PY'
import pathlib, sys
src, current_path, insize_path = map(pathlib.Path, sys.argv[1:])
section = None
current, insize = [], []
for line in src.read_text(encoding="utf-8").splitlines():
    if line == "---CURRENT---":
        section = "current"
        continue
    if line == "---INSIZE---":
        section = "insize"
        continue
    if line == "---END---":
        break
    if section == "current":
        current.append(line)
    elif section == "insize":
        insize.append(line)
if not current or not insize:
    raise SystemExit("post_export_missing")
current_path.write_text("\n".join(current) + "\n", encoding="utf-8")
insize_path.write_text("\n".join(insize) + "\n", encoding="utf-8")
PY
python3 "${SQL_DIR}/non_insize_price_apply_check.py" state \
  "${TMP_DIR}/manifest.jsonl" "${TMP_DIR}/current.jsonl" | tee "${TMP_DIR}/price-state.txt"
price_state="$(awk -F= '/^price_state=/{print $2}' "${TMP_DIR}/price-state.txt")"
if [ "$price_state" = "unchanged" ]; then
  rolled_back "apply_transaction_failed"
fi
if [ "$price_state" != "applied" ]; then
  rollback_required "target_price_diverged"
fi
if grep -q '^committed=YES$' "${TMP_DIR}/apply-out.txt"; then
  echo "commit_marker=YES"
else
  echo "commit_marker=MISSING_BUT_PRICES_MATCH_MANIFEST"
fi
python3 "${SQL_DIR}/non_insize_price_apply_check.py" compare \
  "${TMP_DIR}/manifest.jsonl" "${TMP_DIR}/current.jsonl" || rollback_required "target_price_mismatch"
python3 "${SQL_DIR}/non_insize_price_apply_check.py" compare-insize \
  "${TMP_DIR}/insize.jsonl" "${TMP_DIR}/insize-after.jsonl" || rollback_required "insize_price_mismatch"

echo "=== FINGERPRINT_AFTER ==="
psql_read "${SQL_DIR}/non_insize_price_apply_fingerprint.sql" > "${TMP_DIR}/fp-after.txt" || rollback_required "fingerprint_after_failed"
grep -E '^(transaction_read_only|nonprice_fp|insize_price_fp|nontarget_price_fp|orders_fp|order_items_fp|payments_fp)=' "${TMP_DIR}/fp-after.txt"
FP_AFTER_NONPRICE="$(awk -F= '/^nonprice_fp=/{print $2}' "${TMP_DIR}/fp-after.txt")"
FP_AFTER_INSIZE="$(awk -F= '/^insize_price_fp=/{print $2}' "${TMP_DIR}/fp-after.txt")"
FP_AFTER_NONTARGET="$(awk -F= '/^nontarget_price_fp=/{print $2}' "${TMP_DIR}/fp-after.txt")"
FP_AFTER_ORDERS="$(awk -F= '/^orders_fp=/{print $2}' "${TMP_DIR}/fp-after.txt")"
FP_AFTER_ITEMS="$(awk -F= '/^order_items_fp=/{print $2}' "${TMP_DIR}/fp-after.txt")"
FP_AFTER_PAYMENTS="$(awk -F= '/^payments_fp=/{print $2}' "${TMP_DIR}/fp-after.txt")"
echo "nonprice_fp_unchanged=$([ "$FP_BEFORE_NONPRICE" = "$FP_AFTER_NONPRICE" ] && echo YES || echo NO)"
echo "insize_price_fp_unchanged=$([ "$FP_BEFORE_INSIZE" = "$FP_AFTER_INSIZE" ] && echo YES || echo NO)"
echo "nontarget_price_fp_unchanged=$([ "$FP_BEFORE_NONTARGET" = "$FP_AFTER_NONTARGET" ] && echo YES || echo NO)"
echo "orders_fp_unchanged=$([ "$FP_BEFORE_ORDERS" = "$FP_AFTER_ORDERS" ] && echo YES || echo NO)"
echo "order_items_fp_unchanged=$([ "$FP_BEFORE_ITEMS" = "$FP_AFTER_ITEMS" ] && echo YES || echo NO)"
echo "payments_fp_unchanged=$([ "$FP_BEFORE_PAYMENTS" = "$FP_AFTER_PAYMENTS" ] && echo YES || echo NO)"
if [ "$FP_AFTER_INSIZE" != "$FP_BEFORE_INSIZE" ] || [ "$FP_AFTER_NONTARGET" != "$FP_BEFORE_NONTARGET" ]; then
  rollback_required "post_commit_price_fingerprint"
fi
if [ "$FP_AFTER_NONPRICE" != "$FP_BEFORE_NONPRICE" ]; then
  rollback_required "post_commit_nonprice_fingerprint"
fi

echo "=== API_CANARY ==="
psql_read "${SQL_DIR}/non_insize_price_apply_canary.sql" > "${TMP_DIR}/canary-db.txt" || rollback_required "canary_query_failed"
set +e
python3 - "${TMP_DIR}/canary-db.txt" "$probe_host" <<'PY'
import json, subprocess, sys
from decimal import Decimal
from pathlib import Path
host = sys.argv[2]
rows = []
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.startswith("{"):
        rows.append(json.loads(line))
if len(rows) < 7:
    print(f"canary_rows={len(rows)}")
    raise SystemExit(3)
failures = 0
public_matches = 0
for row in rows:
    product_id = row["product_id"]
    db_price = Decimal(str(row["base_price"]))
    expected = format(db_price, "f").rstrip("0").rstrip(".") if "." in format(db_price, "f") else format(db_price, "f")
    proc = subprocess.run(
        [
            "curl", "-sS", "-o", "-", "-w", "\n%{http_code}", "--max-time", "15",
            "-H", f"Host: {host}",
            "-H", "X-Forwarded-Proto: https",
            f"http://127.0.0.1:8000/api/v1/products/{product_id}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    body, _, code = proc.stdout.rpartition("\n")
    code = code.strip()
    api_price = ""
    if code == "200":
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict) and "base_price" not in payload and isinstance(payload.get("data"), dict):
            payload = payload["data"]
        api_price = "" if payload.get("base_price") is None else str(payload.get("base_price"))
    public = "YES" if code == "200" else "NO"
    match = "YES" if code == "200" and api_price == expected else ("NOT_PUBLIC" if code == "404" else "NO")
    if match == "YES":
        public_matches += 1
    elif match == "NO":
        failures += 1
    print(
        f"canary id={product_id} brand_id={row.get('brand_id')} sku={row.get('sku')} "
        f"label={row.get('label')} public={public} http={code} db={expected} api={api_price or '-'} match={match}"
    )
print(f"canary_failures={failures}")
print(f"canary_public_matches={public_matches}")
raise SystemExit(0 if failures == 0 and public_matches >= 1 else 3)
PY
canary_code=$?
set -e
if [ "$canary_code" -ne 0 ]; then
  rollback_required "api_canary"
fi

echo "=== COMMERCE_FREEZE_AFTER ==="
purchase_flag_after="$(docker exec lathe_api printenv PURCHASE_CHECKOUT_ENABLED)"
status_code_after="$(curl -sS -o "$status_file" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" \
  -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8000/api/v1/commerce/purchase-status || true)"
purchase_enabled_after="$(python3 - "$status_file" <<'PY'
import json, sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print("unparsed")
    raise SystemExit(0)
print(str(data.get("purchase_checkout_enabled")).lower())
PY
)"
echo "purchase_checkout_enabled=${purchase_flag_after}"
echo "purchase_status_http=${status_code_after}"
echo "purchase_status_enabled=${purchase_enabled_after}"
if [ "$purchase_flag_after" != "false" ] || [ "$purchase_enabled_after" != "false" ]; then
  rollback_required "commerce_freeze_lost"
fi

if [ "$FP_AFTER_PAYMENTS" != "$FP_BEFORE_PAYMENTS" ]; then
  rollback_required "payment_fingerprint"
fi
echo "PAYMENT_MUTATION=NO"
if [ "$FP_AFTER_ORDERS" = "$FP_BEFORE_ORDERS" ] && [ "$FP_AFTER_ITEMS" = "$FP_BEFORE_ITEMS" ]; then
  echo "ORDER_MUTATION=NO"
else
  echo "ORDER_FINGERPRINT_DRIFT=YES"
  echo "ORDER_SQL_STATEMENTS=NONE"
  rollback_required "order_fingerprint"
fi

echo "HESABFA_API_WRITE=0"
echo "PRICE_MUTATION=YES"
echo "TARGET_ROWS_CHANGED=4065"
echo "INSIZE_ROWS_CHANGED=0"
echo "AVAILABILITY_CHANGED=NO"
echo "STOCK_CHANGED=NO"
echo "HESABFA_WRITE=NO"
echo "PURCHASE_CHECKOUT_ENABLED_CHANGED=NO"
echo "DEPLOY=NO"
echo "EMALLS_READ_IMPACT=next_read_uses_stored_base_price"
echo "ROLLBACK_ARTIFACT=${MANIFEST_PATH}"
STATUS="APPLIED_AND_VERIFIED"
finish 0
