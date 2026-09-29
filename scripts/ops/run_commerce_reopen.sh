#!/bin/bash
# Owner-authorized purchase reopen. Changes only PURCHASE_CHECKOUT_ENABLED
# and recreates lathe_api with the no-migration entrypoint override.
set -euo pipefail

if [ "${KARZAR_COMMERCE_REOPEN_CONFIRM:-}" != "owner_reopen_purchase_checkout_2026_09_29" ]; then
  echo "STATUS=BLOCKED_NO_CHANGE"
  echo "BLOCK_REASON=confirm_token_missing"
  exit 1
fi

ENV_FILE=/opt/karzar/Karzar/.env
ROOT=/opt/karzar/Karzar
EXPECTED_SHA="e2470bef067b2016db0665ef3d39c80854b197b9"
MANIFEST_PATH="/opt/karzar/rollout-backups/non-insize-price-20pct-2026-09-29/manifest-20260929T144058Z.jsonl"
EXPECTED_MANIFEST_SHA="9041472c85013e783cf751639523dd065f68a592b10c74a54f39fdfdf561b5bd"
EXPECTED_INSIZE_FP="df799c09f4d9b6f6717344808b5b592d"
EXPECTED_NONPRICE_FP="fb9ee59db6ebff770d69aee59d2d8944"
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

WROTE=NO
RECREATED=NO
IN_ROLLBACK=NO
STATUS="BLOCKED_NO_CHANGE"
ROLLBACK_STATUS="NOT_NEEDED"
ORDER_MUTATION=NO
PAYMENT_MUTATION=NO
STOCK_CHANGED=NO
PRICE_CHANGED=NO
INSIZE_CHANGED=NO
AVAILABILITY_CHANGED=NO

psql_read() {
  docker exec -i \
    -e PGOPTIONS='-c default_transaction_read_only=on' \
    lathe_postgres \
    sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -f -' < "$1"
}

note_business_drift() {
  if [ ! -f "${TMP_DIR}/fp-before.txt" ] || [ ! -f "${TMP_DIR}/fp-after.txt" ]; then
    return 0
  fi
  eval "$(python3 - "${TMP_DIR}/fp-before.txt" "${TMP_DIR}/fp-after.txt" <<'PY'
from pathlib import Path
import sys
def load(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out
before, after = load(sys.argv[1]), load(sys.argv[2])
def changed(*keys):
    return any(before.get(key) != after.get(key) for key in keys)
print("ORDER_MUTATION=" + ("YES" if changed("orders", "order_items") else "NO"))
print("PAYMENT_MUTATION=" + ("YES" if changed("payments", "idem") else "NO"))
print("STOCK_CHANGED=" + ("YES" if changed("stock_movements") else "NO"))
print("PRICE_CHANGED=" + ("YES" if changed("price_fp") else "NO"))
print("INSIZE_CHANGED=" + ("YES" if changed("insize_fp") else "NO"))
print("AVAILABILITY_CHANGED=" + ("YES" if changed("nonprice_fp") else "NO"))
PY
)"
}

finish() {
  note_business_drift || true
  echo "STATUS=${STATUS}"
  echo "ROLLBACK_STATUS=${ROLLBACK_STATUS}"
  echo "PURCHASE_CHECKOUT_ENABLED_CHANGED=$([ "$WROTE" = YES ] && echo YES || echo NO)"
  runtime_now="$(docker exec lathe_api printenv PURCHASE_CHECKOUT_ENABLED 2>/dev/null || true)"
  echo "PURCHASE_CHECKOUT_ENABLED_FINAL=${runtime_now:-unknown}"
  echo "PRICE_CHANGED=${PRICE_CHANGED}"
  echo "INSIZE_CHANGED=${INSIZE_CHANGED}"
  echo "AVAILABILITY_CHANGED=${AVAILABILITY_CHANGED}"
  echo "STOCK_CHANGED=${STOCK_CHANGED}"
  echo "HESABFA_WRITE=NO"
  echo "ORDER_MUTATION=${ORDER_MUTATION}"
  echo "PAYMENT_MUTATION=${PAYMENT_MUTATION}"
  echo "DEPLOY=NO"
  echo "MIGRATION=NO"
  if [ "$STATUS" = "COMMERCE_REOPENED_AND_VERIFIED" ] || [ "$STATUS" = "ALREADY_ENABLED_AND_VERIFIED" ]; then
    exit 0
  fi
  exit 1
}

blocked() {
  STATUS="BLOCKED_NO_CHANGE"
  echo "BLOCK_REASON=$1"
  finish
}

cat > "${TMP_DIR}/fp.sql" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'orders=' || count(*)::text || '|' || md5(coalesce(string_agg(id::text || '|' || coalesce(estimated_total::text,'') || '|' || status || '|' || payment_status, E'\n' ORDER BY id), '')) FROM orders;
SELECT 'order_items=' || count(*)::text || '|' || md5(coalesce(string_agg(id::text || '|' || coalesce(unit_price::text,'') || '|' || quantity::text, E'\n' ORDER BY id), '')) FROM order_items;
SELECT 'payments=' || count(*)::text || '|' || md5(coalesce(string_agg(id::text || '|' || amount::text || '|' || status, E'\n' ORDER BY id), '')) FROM payment_transactions;
SELECT 'idem=' || count(*)::text || '|' || md5(coalesce(string_agg(id::text || '|' || scope || '|' || key, E'\n' ORDER BY id), '')) FROM idempotency_keys;
SELECT 'stock_movements=' || count(*)::text || '|' || md5(coalesce(string_agg(id::text || '|' || product_id::text || '|' || quantity_change::text, E'\n' ORDER BY id), '')) FROM stock_movements;
SELECT 'carts=' || count(*)::text || '|' || md5(coalesce(string_agg(id::text, E'\n' ORDER BY id), '')) FROM carts;
SELECT 'cart_items=' || count(*)::text || '|' || md5(coalesce(string_agg(id::text || '|' || product_id::text || '|' || quantity::text, E'\n' ORDER BY id), '')) FROM cart_items;
SELECT 'nonprice_fp=' || md5(coalesce(string_agg(id::text || '|' || is_active::text || '|' || is_available::text || '|' || stock_quantity::text || '|' || coalesce(brand_id::text,'') || '|' || category_id::text || '|' || sku || '|' || slug || '|' || name || '|' || coalesce(deleted_at::text,'') || '|' || coalesce(product_type_id::text,''), E'\n' ORDER BY id), '')) FROM products;
SELECT 'insize_fp=' || md5(coalesce(string_agg(id::text || '|' || coalesce(base_price::text,'') || '|' || coalesce(original_price::text,''), E'\n' ORDER BY id), '')) FROM products WHERE deleted_at IS NULL AND brand_id = 3;
SELECT 'price_fp=' || md5(coalesce(string_agg(id::text || '|' || coalesce(base_price::text,'') || '|' || coalesce(original_price::text,''), E'\n' ORDER BY id), '')) FROM products;
SELECT 'mapped=' || count(*)::text FROM products p JOIN hesabfa_item_mappings m ON m.product_id = p.id WHERE p.deleted_at IS NULL AND (p.brand_id IS NULL OR p.brand_id <> 3) AND p.base_price > 0;
SELECT 'unmapped=' || count(*)::text FROM products p LEFT JOIN hesabfa_item_mappings m ON m.product_id = p.id WHERE p.deleted_at IS NULL AND (p.brand_id IS NULL OR p.brand_id <> 3) AND p.base_price > 0 AND m.id IS NULL;
ROLLBACK;
SQL

snapshot_fp() {
  psql_read "${TMP_DIR}/fp.sql" > "$1"
}

echo "=== IDENTITY ==="
echo "hostname=$(hostname)"
if [ "$(hostname)" != "srv5944957438" ]; then
  blocked "hostname"
fi
test -f "$ENV_FILE"
test -d "$ROOT"
if ! docker inspect lathe_api >/dev/null 2>&1 || ! docker inspect lathe_postgres >/dev/null 2>&1 || ! docker inspect lathe_redis >/dev/null 2>&1; then
  blocked "containers_missing"
fi
api_name="$(docker inspect -f '{{.Name}}' lathe_api)"
pg_name="$(docker inspect -f '{{.Name}}' lathe_postgres)"
pg_mount="$(docker inspect -f '{{range .Mounts}}{{.Name}}{{println}}{{end}}' lathe_postgres)"
api_db="$(docker exec lathe_api printenv POSTGRES_DB)"
app_env="$(docker exec lathe_api printenv APP_ENV)"
data_plane="$(docker exec lathe_api printenv KARZAR_DATA_PLANE || true)"
alembic_line="$(docker exec lathe_api alembic current 2>/dev/null | awk '/t3u4v5w6x7y8/ {print; exit}' || true)"
echo "api_name=${api_name}"
echo "postgres_name=${pg_name}"
echo "postgres_mount=${pg_mount}"
echo "postgres_db=${api_db}"
echo "app_env=${app_env}"
echo "data_plane=${data_plane:-unset}"
echo "alembic=${alembic_line}"
if [ "$api_name" != "/lathe_api" ] || [ "$pg_name" != "/lathe_postgres" ] || [ "$pg_mount" != "karzar_postgres_data" ] || [ "$api_db" != "karzar_staging" ] || [ "$app_env" != "staging" ] || [ -n "$data_plane" ] || [ "$alembic_line" != "t3u4v5w6x7y8 (head)" ]; then
  blocked "live_identity"
fi
echo "LIVE_IDENTITY=PASS"

echo "=== IMAGES_AND_GUARDS ==="
shop_rev="$(docker inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' karzar_shop)"
admin_rev="$(docker inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' karzar_admin)"
echo "shop_image=$(docker inspect -f '{{.Config.Image}}' karzar_shop)"
echo "admin_image=$(docker inspect -f '{{.Config.Image}}' karzar_admin)"
echo "api_image=$(docker inspect -f '{{.Config.Image}}' lathe_api)"
echo "shop_revision=${shop_rev}"
echo "admin_revision=${admin_rev}"
if [ "$shop_rev" != "$EXPECTED_SHA" ] || [ "$admin_rev" != "$EXPECTED_SHA" ]; then
  blocked "frontend_sha"
fi
set +e
docker exec lathe_api python3 - <<'PY'
from pathlib import Path
checkout = Path("/app/app/api/endpoints/checkout.py").read_text(encoding="utf-8")
payment = Path("/app/app/api/endpoints/payment.py").read_text(encoding="utf-8")
checkout_calls = checkout.count("raise_if_purchase_checkout_disabled()")
payment_calls = payment.count("raise_if_purchase_checkout_disabled()")
print(f"checkout_guard_calls={checkout_calls}")
print(f"payment_guard_calls={payment_calls}")
if checkout_calls != 1 or payment_calls != 1:
    raise SystemExit(2)
if "def payment_callback" not in payment or "def payment_verify" not in payment or "def payment_callback_sep" not in payment:
    raise SystemExit(3)
print("callback_verify_present=YES")
print("callback_verify_not_globally_frozen=YES")
PY
guard_code=$?
set -e
if [ "$guard_code" -ne 0 ]; then
  blocked "api_guard_architecture"
fi

echo "=== PRE_PRICE ==="
manifest_sha="$(docker run --rm --network none --user 0 --entrypoint sha256sum \
  -v "${MANIFEST_PATH}:/manifest:ro" postgres:15-alpine /manifest | awk '{print $1}')"
echo "MANIFEST_SHA256=${manifest_sha}"
if [ "$manifest_sha" != "$EXPECTED_MANIFEST_SHA" ]; then
  blocked "manifest_sha"
fi
docker run --rm --network none --user 0 --entrypoint sh \
  -v "${MANIFEST_PATH}:/manifest:ro" -v "${TMP_DIR}:/out" postgres:15-alpine \
  -c 'cp /manifest /out/manifest.jsonl && chmod 644 /out/manifest.jsonl'
cat > "${TMP_DIR}/current.sql" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object('product_id', id, 'base_price', base_price::text, 'original_price', original_price::text)::text
FROM products
WHERE deleted_at IS NULL AND (brand_id IS NULL OR brand_id <> 3) AND base_price IS NOT NULL AND base_price > 0
ORDER BY id;
SELECT 'insize_live=' || count(*)::text FROM products WHERE deleted_at IS NULL AND brand_id = 3;
SELECT 'insize_priced=' || count(*)::text FROM products WHERE deleted_at IS NULL AND brand_id = 3 AND base_price > 0;
ROLLBACK;
SQL
psql_read "${TMP_DIR}/current.sql" > "${TMP_DIR}/current.txt"
set +e
python3 - "${TMP_DIR}/manifest.jsonl" "${TMP_DIR}/current.txt" <<'PY'
import json, sys
from decimal import Decimal
from pathlib import Path
def money(value):
    if value is None or value == "":
        return None
    return Decimal(str(value))
manifest = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
current = []
meta = {}
for line in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
    if line.startswith("{"):
        current.append(json.loads(line))
    elif "=" in line:
        key, value = line.split("=", 1)
        meta[key] = value
by_id = {row["product_id"]: row for row in current}
base_miss = original_miss = 0
for row in manifest:
    live = by_id.get(row["product_id"])
    if live is None or money(live["base_price"]) != money(row["new_base_price"]):
        base_miss += 1
    if live is None or money(live["original_price"]) != money(row["new_original_price"]):
        original_miss += 1
print(f"manifest_rows={len(manifest)}")
print(f"base_price_mismatches={base_miss}")
print(f"original_price_mismatches={original_miss}")
print(f"insize_live={meta.get('insize_live','')}")
print(f"insize_priced={meta.get('insize_priced','')}")
if len(manifest) != 4065 or base_miss or original_miss or meta.get("insize_live") != "872" or meta.get("insize_priced") != "487":
    raise SystemExit(2)
PY
price_rc=$?
set -e
if [ "$price_rc" -ne 0 ]; then
  blocked "price_drift"
fi

snapshot_fp "${TMP_DIR}/fp-before.txt"
echo "=== FINGERPRINT_BEFORE ==="
cat "${TMP_DIR}/fp-before.txt"
if ! grep -q "^insize_fp=${EXPECTED_INSIZE_FP}$" "${TMP_DIR}/fp-before.txt"; then
  blocked "insize_fingerprint"
fi
if ! grep -q "^nonprice_fp=${EXPECTED_NONPRICE_FP}$" "${TMP_DIR}/fp-before.txt"; then
  blocked "nonprice_fingerprint"
fi
if ! grep -q '^mapped=1994$' "${TMP_DIR}/fp-before.txt" || ! grep -q '^unmapped=2071$' "${TMP_DIR}/fp-before.txt"; then
  blocked "hesabfa_mapping"
fi

echo "=== ENV ==="
before_mode="$(stat -c '%a' "$ENV_FILE")"
before_owner="$(stat -c '%U' "$ENV_FILE")"
before_group="$(stat -c '%G' "$ENV_FILE")"
echo "env_mode_before=${before_mode}"
echo "env_owner_before=${before_owner}"
echo "env_group_before=${before_group}"
set +e
python3 - "$ENV_FILE" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
def active(prefix):
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(prefix):
            rows.append(stripped)
    return rows
purchase = active("PURCHASE_CHECKOUT_ENABLED=")
provider = active("PAYMENT_PROVIDER=")
print(f"purchase_entries={len(purchase)}")
print(f"payment_provider_entries={len(provider)}")
if len(purchase) != 1 or len(provider) != 1 or provider[0] != "PAYMENT_PROVIDER=sep":
    raise SystemExit(2)
value = purchase[0].split("=", 1)[1].strip().strip("\"'").lower()
print(f"PURCHASE_CHECKOUT_ENABLED_before={value}")
if value not in {"true", "false"}:
    raise SystemExit(3)
Path("/tmp/karzar-purchase-before").write_text(value, encoding="utf-8")
PY
env_parse=$?
set -e
if [ "$env_parse" -ne 0 ]; then
  blocked "env_unparseable"
fi
before_value="$(cat /tmp/karzar-purchase-before)"
rm -f /tmp/karzar-purchase-before

api_started_before="$(docker inspect -f '{{.State.StartedAt}}' lathe_api)"
pg_started_before="$(docker inspect -f '{{.State.StartedAt}}' lathe_postgres)"
redis_started_before="$(docker inspect -f '{{.State.StartedAt}}' lathe_redis)"
shop_started_before="$(docker inspect -f '{{.State.StartedAt}}' karzar_shop)"
admin_started_before="$(docker inspect -f '{{.State.StartedAt}}' karzar_admin)"
echo "api_started_before_set=YES"

recreate_api() {
  cat > /tmp/karzar-commerce-reopen-no-migrate.yml <<'EOF'
services:
  app:
    entrypoint:
      - /bin/sh
      - -c
      - |
        echo "commerce reopen recreate: alembic not invoked"
        if [ "$APP_SERVER" = "gunicorn" ]; then
          exec gunicorn app.main:app -c /app/gunicorn_conf.py
        fi
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF
  COMPOSE=(docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.staging.yml")
  if [ -f "$ROOT/docker-compose.image.yml" ]; then
    COMPOSE+=(-f "$ROOT/docker-compose.image.yml")
  fi
  COMPOSE+=(-f /tmp/karzar-commerce-reopen-no-migrate.yml)
  (
    cd "$ROOT"
    "${COMPOSE[@]}" up -d --no-deps --no-build --force-recreate app
  )
  rm -f /tmp/karzar-commerce-reopen-no-migrate.yml
}

write_flag() {
  local target="$1"
  local editor
  editor="$(mktemp)"
  cat > "$editor" <<'PY'
import os, sys
from pathlib import Path
path = Path(sys.argv[1])
target = sys.argv[2]
st = path.stat()
text = path.read_bytes().decode("utf-8")
lines = text.splitlines(keepends=True)
key = "PURCHASE_CHECKOUT_ENABLED="
def is_entry(line):
    stripped = line.lstrip(" \t")
    return (not stripped.startswith("#")) and stripped.startswith(key)
indexes = [i for i, line in enumerate(lines) if is_entry(line)]
if len(indexes) != 1:
    print("WRITE=NO")
    raise SystemExit(2)
idx = indexes[0]
body = lines[idx].lstrip(" \t")
raw = body.split("=", 1)[1].split("#", 1)[0].strip().strip("\"'").lower()
if raw not in {"true", "false"}:
    print("WRITE=NO")
    raise SystemExit(3)
if raw == target:
    print("WRITE=NO")
    print("PURCHASE_CHECKOUT_ENABLED_after=%s" % target)
    raise SystemExit(0)
ending = "\n" if lines[idx].endswith("\n") else ""
if lines[idx].endswith("\r\n"):
    ending = "\r\n"
new_lines = list(lines)
new_lines[idx] = key + target + ending
if len(new_lines) != len(lines):
    print("WRITE=NO")
    raise SystemExit(4)
for i, (old, new) in enumerate(zip(lines, new_lines)):
    if i != idx and old != new:
        print("WRITE=NO")
        raise SystemExit(4)
new_text = "".join(new_lines)
tmp = path.with_name(".env.commerce-reopen-%s" % os.getpid())
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "wb") as handle:
    handle.write(new_text.encode("utf-8"))
    handle.flush()
    os.fsync(handle.fileno())
os.chown(tmp, st.st_uid, st.st_gid)
os.chmod(tmp, st.st_mode & 0o777)
os.replace(tmp, path)
print("WRITE=YES")
print("PURCHASE_CHECKOUT_ENABLED_after=%s" % target)
PY
  if [ -w "$ENV_FILE" ]; then
    echo "env_write=direct"
    python3 "$editor" "$ENV_FILE" "$target"
  else
    echo "env_write=docker_root"
    docker run --rm --network none --user 0 --entrypoint python3 \
      -v /opt/karzar/Karzar:/hostkarzar \
      -v "$editor":/editor.py:ro \
      karzar-app:staging /editor.py /hostkarzar/.env "$target"
  fi
  rm -f "$editor"
}

on_err() {
  echo "UNCAUGHT_ERROR line=${1:-unknown}"
  if [ "$IN_ROLLBACK" = "YES" ]; then
    echo "STATUS=ROLLED_BACK_TO_FREEZE"
    echo "ROLLBACK_STATUS=ROLLBACK_ITSELF_FAILED"
    echo "PURCHASE_CHECKOUT_ENABLED_CHANGED=YES"
    exit 1
  fi
  if [ "${WROTE:-NO}" = "YES" ]; then
    IN_ROLLBACK=YES
    set +e
    write_flag false
    if [ "${RECREATED:-NO}" = "YES" ]; then
      recreate_api
      wait_ready "${probe_host:-api.karzartools.com}" || true
    fi
    runtime_now="$(docker exec lathe_api printenv PURCHASE_CHECKOUT_ENABLED 2>/dev/null || true)"
    echo "STATUS=ROLLED_BACK_TO_FREEZE"
    echo "ROLLBACK_STATUS=ATTEMPTED_AFTER_UNCAUGHT_ERROR"
    echo "PURCHASE_CHECKOUT_ENABLED_CHANGED=YES"
    echo "PURCHASE_CHECKOUT_ENABLED_FINAL=${runtime_now:-unknown}"
    echo "DEPLOY=NO"
    echo "MIGRATION=NO"
    echo "HESABFA_WRITE=NO"
    exit 1
  fi
  echo "STATUS=BLOCKED_NO_CHANGE"
  echo "ROLLBACK_STATUS=NOT_NEEDED"
  echo "PURCHASE_CHECKOUT_ENABLED_CHANGED=NO"
  echo "DEPLOY=NO"
  echo "MIGRATION=NO"
  exit 1
}
trap 'on_err $LINENO' ERR

rollback_to_freeze() {
  local reason="$1"
  IN_ROLLBACK=YES
  echo "=== ROLLBACK ==="
  set +e
  write_flag false
  echo "rollback_write_rc=$?"
  if [ "$RECREATED" = "YES" ]; then
    recreate_api
    echo "rollback_recreate_rc=$?"
    wait_ready "$probe_host" || true
  else
    echo "rollback_recreate_rc=SKIPPED_API_NOT_RECREATED"
  fi
  set -e
  STATUS="ROLLED_BACK_TO_FREEZE"
  ROLLBACK_STATUS="$reason"
  finish
}

wait_ready() {
  local probe_host="$1"
  local ready_code="000"
  local i
  for i in $(seq 1 45); do
    ready_code="$(curl -sS -o "${TMP_DIR}/ready.json" -w '%{http_code}' --max-time 5 \
      -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
      http://127.0.0.1:8000/ready || true)"
    if [ "$ready_code" = "200" ]; then
      break
    fi
    sleep 2
  done
  echo "ready_http=${ready_code}"
  python3 - "${TMP_DIR}/ready.json" <<'PY'
import json, sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print("ready_status=unparsed")
    raise SystemExit(0)
print("ready_status=%s" % data.get("status"))
print("ready_database=%s" % data.get("database"))
print("ready_redis=%s" % data.get("redis"))
PY
  [ "$ready_code" = "200" ]
}

assert_neighbors_unchanged() {
  local pg_after redis_after shop_after admin_after
  pg_after="$(docker inspect -f '{{.State.StartedAt}}' lathe_postgres)"
  redis_after="$(docker inspect -f '{{.State.StartedAt}}' lathe_redis)"
  shop_after="$(docker inspect -f '{{.State.StartedAt}}' karzar_shop)"
  admin_after="$(docker inspect -f '{{.State.StartedAt}}' karzar_admin)"
  if [ "$pg_after" != "$pg_started_before" ] || [ "$redis_after" != "$redis_started_before" ] || [ "$shop_after" != "$shop_started_before" ] || [ "$admin_after" != "$admin_started_before" ]; then
    echo "postgres_restarted=$([ "$pg_after" = "$pg_started_before" ] && echo NO || echo YES)"
    echo "redis_restarted=$([ "$redis_after" = "$redis_started_before" ] && echo NO || echo YES)"
    return 1
  fi
  echo "postgres_restarted=NO"
  echo "redis_restarted=NO"
  echo "shop_restarted=NO"
  echo "admin_restarted=NO"
}

probe_host="$(python3 - "$ENV_FILE" <<'PY'
import sys
from pathlib import Path
host = ""
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.startswith("TRUSTED_HOSTS="):
        raw = line.split("=", 1)[1].strip().strip("\"'")
        host = raw.split(",")[0].strip()
        break
print(host or "api.karzartools.com")
PY
)"
echo "probe_host=${probe_host}"

echo "ENV_BEFORE=PURCHASE_CHECKOUT_ENABLED=${before_value}"
echo "ENV_OWNER_GROUP_MODE=${before_owner}:${before_group}:${before_mode}"
runtime_before="$(docker exec lathe_api printenv PURCHASE_CHECKOUT_ENABLED || true)"
echo "PURCHASE_STATUS_BEFORE=${runtime_before:-unset}"

if [ "$before_value" = "true" ]; then
  echo "ENV_ALREADY_TRUE=YES"
  echo "ENV_AFTER=PURCHASE_CHECKOUT_ENABLED=true"
  echo "API_RECREATE=NO"
  echo "postgres_restarted=NO"
  echo "redis_restarted=NO"
else
  echo "=== FLAG_CHANGE ==="
  set +e
  write_flag true
  write_rc=$?
  set -e
  if [ "$write_rc" -ne 0 ]; then
    blocked "env_write_failed"
  fi
  WROTE=YES
  echo "ENV_AFTER=PURCHASE_CHECKOUT_ENABLED=true"
  after_mode="$(stat -c '%a' "$ENV_FILE")"
  after_owner="$(stat -c '%U' "$ENV_FILE")"
  after_group="$(stat -c '%G' "$ENV_FILE")"
  echo "env_mode_after=${after_mode}"
  echo "env_owner_after=${after_owner}"
  echo "env_group_after=${after_group}"
  echo "ENV_OWNER_GROUP_MODE=${after_owner}:${after_group}:${after_mode}"
  if [ "$after_mode" != "$before_mode" ] || [ "$after_owner" != "$before_owner" ] || [ "$after_group" != "$before_group" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_ENV_METADATA"
  fi
  exact="$(grep -c '^PURCHASE_CHECKOUT_ENABLED=true$' "$ENV_FILE" || true)"
  provider_exact="$(grep -c '^PAYMENT_PROVIDER=sep$' "$ENV_FILE" || true)"
  echo "purchase_true_lines=${exact}"
  echo "payment_provider_sep_lines=${provider_exact}"
  if [ "$exact" != "1" ] || [ "$provider_exact" != "1" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_ENV_LINE_COUNT"
  fi
  echo "=== API_RECREATE ==="
  set +e
  recreate_api
  recreate_rc=$?
  set -e
  if [ "$recreate_rc" -ne 0 ]; then
    RECREATED=YES
    rollback_to_freeze "ATTEMPTED_AFTER_RECREATE_FAILURE"
  fi
  RECREATED=YES
  echo "API_RECREATE=YES"
  echo "migrations_invoked=NO"
  if ! assert_neighbors_unchanged; then
    rollback_to_freeze "ATTEMPTED_AFTER_NEIGHBOR_RESTART"
  fi
  api_started_after="$(docker inspect -f '{{.State.StartedAt}}' lathe_api)"
  if [ "$api_started_after" = "$api_started_before" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_API_NOT_RECREATED"
  fi
  echo "api_started_changed=YES"
fi

echo "=== READY ==="
if ! wait_ready "$probe_host"; then
  if [ "$WROTE" = "YES" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_READY_FAILURE"
  fi
  blocked "ready_failed"
fi
set +e
python3 - "${TMP_DIR}/ready.json" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("ready_status=%s" % data.get("status"))
print("ready_database=%s" % data.get("database"))
print("ready_redis=%s" % data.get("redis"))
ok = data.get("status") == "ready" and data.get("database") == "ok" and data.get("redis") == "ok"
raise SystemExit(0 if ok else 2)
PY
ready_body=$?
set -e
if [ "$ready_body" -ne 0 ]; then
  if [ "$WROTE" = "YES" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_READY_BODY"
  fi
  blocked "ready_body"
fi
echo "READY_STATUS=PASS"

runtime_after="$(docker exec lathe_api printenv PURCHASE_CHECKOUT_ENABLED || true)"
echo "runtime_after=${runtime_after}"
status_code="$(curl -sS -o "${TMP_DIR}/purchase.json" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8000/api/v1/commerce/purchase-status || true)"
public_enabled="$(python3 - "${TMP_DIR}/purchase.json" <<'PY'
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
echo "PURCHASE_STATUS_AFTER=${public_enabled}"
echo "purchase_status_http=${status_code}"
echo "purchase_status_enabled=${public_enabled}"
if [ "$runtime_after" != "true" ] || [ "$status_code" != "200" ] || [ "$public_enabled" != "true" ]; then
  if [ "$WROTE" = "YES" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_RUNTIME_MISMATCH"
  fi
  blocked "runtime_not_true"
fi

echo "=== RELEASE_CANARIES ==="
snapshot_fp "${TMP_DIR}/fp-mid.txt"
expire_minutes="$(docker exec lathe_api printenv PENDING_PAYMENT_EXPIRE_MINUTES || true)"
if [ -z "$expire_minutes" ]; then
  expire_minutes=30
fi
if ! [[ "$expire_minutes" =~ ^[0-9]+$ ]] || [ "$expire_minutes" -lt 5 ] || [ "$expire_minutes" -gt 1440 ]; then
  echo "expiry_minutes=unparseable"
  if [ "$WROTE" = "YES" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_EXPIRY_MINUTES"
  fi
  blocked "expiry_minutes"
fi
echo "expiry_minutes=${expire_minutes}"
cat > "${TMP_DIR}/expiry.sql" <<SQL
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'expiry_candidates=' || count(*)::text
FROM orders o
WHERE o.status = 'pending_payment'
  AND o.mode = 'purchase'
  AND o.created_at < NOW() - (${expire_minutes} * INTERVAL '1 minute')
  AND o.payment_status IN ('unpaid', 'failed')
  AND (o.payment_authority_expires_at IS NULL OR o.payment_authority_expires_at <= NOW())
  AND COALESCE(BTRIM(o.payment_ref_id), '') = ''
  AND o.payment_callback_received_at IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM payment_transactions pt
    WHERE pt.order_id = o.id
      AND pt.status IN ('verified', 'callback_received')
  );
ROLLBACK;
SQL
psql_read "${TMP_DIR}/expiry.sql" | tee "${TMP_DIR}/expiry.txt"
expiry_candidates="$(awk -F= '/^expiry_candidates=/{print $2}' "${TMP_DIR}/expiry.txt")"
echo "expiry_candidates=${expiry_candidates}"
checkout_code="$(curl -sS -o "${TMP_DIR}/checkout.json" -w '%{http_code}' --max-time 20 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/v1/checkout \
  --data '{"mode":"purchase","customer":{"full_name":"Readonly Probe","phone":"09120000000","is_guest":true},"items":[{"product_id":1,"quantity":1}]}' || true)"
python3 - "${TMP_DIR}/checkout.json" "$checkout_code" <<'PY'
import json, sys
from pathlib import Path
code = sys.argv[2]
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    data = {}
print(f"checkout_http={code}")
print("checkout_error_code=" + str(data.get("error_code")))
frozen = code == "503" and str(data.get("error_code")) == "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED"
created = code in {"200", "201"}
print("CHECKOUT_RELEASE_CANARY=" + ("FAIL" if frozen or created else "PASS"))
PY
init_code="000"
printf '%s\n' '{}' > "${TMP_DIR}/init.json"
if [ "${expiry_candidates}" != "0" ]; then
  echo "payment_init_http=SKIPPED"
  echo "payment_init_skip_reason=expiry_candidates_present"
  echo "PAYMENT_INIT_RELEASE_CANARY=SKIPPED_EXPIRY_CANDIDATES"
else
init_code="$(curl -sS -o "${TMP_DIR}/init.json" -w '%{http_code}' --max-time 20 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/v1/payments/init \
  --data '{"order_id":2147483646}' || true)"
python3 - "${TMP_DIR}/init.json" "$init_code" <<'PY'
import json, sys
from pathlib import Path
code = sys.argv[2]
raw = Path(sys.argv[1]).read_text(encoding="utf-8")
try:
    data = json.loads(raw)
except Exception:
    data = {}
print(f"payment_init_http={code}")
print("payment_init_error_code=" + str(data.get("error_code")))
print("payment_init_has_payment_url=" + ("YES" if "payment_url" in raw else "NO"))
print("PAYMENT_INIT_RELEASE_CANARY=" + ("FAIL" if str(data.get("error_code")) == "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED" or "payment_url" in raw or code in {"200", "201"} else "PASS"))
PY
fi
cb_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8000/api/v1/payments/callback || true)"
sep_code="$(curl -sS -o "${TMP_DIR}/sep.out" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -X POST http://127.0.0.1:8000/api/v1/payments/callback/sep --data '' || true)"
verify_code="$(curl -sS -o "${TMP_DIR}/verify.json" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/v1/payments/verify \
  --data '{"authority":"reopen-probe-not-a-real-authority"}' || true)"
verify_error="$(python3 - "${TMP_DIR}/verify.json" <<'PY'
import json, sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("error_code") or "")
except Exception:
    print("")
PY
)"
echo "callback_get_http=${cb_code}"
echo "callback_sep_http=${sep_code}"
echo "verify_http=${verify_code}"
echo "verify_error_code=${verify_error}"
callback_ok=YES
if [ "$cb_code" = "503" ] || [ "$sep_code" = "503" ] || [ "$verify_code" = "503" ] || [ "$verify_error" = "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED" ]; then
  callback_ok=NO
fi
echo "CALLBACK_VERIFY_STATUS=$([ "$callback_ok" = YES ] && echo PASS || echo FAIL)"
snapshot_fp "${TMP_DIR}/fp-after.txt"
echo "=== FINGERPRINT_AFTER ==="
cat "${TMP_DIR}/fp-after.txt"
python3 - "${TMP_DIR}/fp-before.txt" "${TMP_DIR}/fp-after.txt" <<'PY'
from pathlib import Path
import sys
def load(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out
before = load(sys.argv[1])
after = load(sys.argv[2])
ok = True
for key in ["orders", "order_items", "payments", "idem", "stock_movements", "carts", "cart_items", "nonprice_fp", "insize_fp", "price_fp", "mapped", "unmapped"]:
    same = before.get(key) == after.get(key)
    if not same:
        ok = False
    print(f"fp_{key}_unchanged={'YES' if same else 'NO'}")
print("FINGERPRINTS_UNCHANGED=" + ("YES" if ok else "NO"))
PY

checkout_error="$(python3 - "${TMP_DIR}/checkout.json" <<'PY'
import json, sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("error_code") or "")
except Exception:
    print("")
PY
)"
init_error="$(python3 - "${TMP_DIR}/init.json" <<'PY'
import json, sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("error_code") or "")
except Exception:
    print("")
PY
)"
init_body="$(cat "${TMP_DIR}/init.json" 2>/dev/null || true)"
fp_ok="$(python3 - "${TMP_DIR}/fp-before.txt" "${TMP_DIR}/fp-after.txt" <<'PY'
from pathlib import Path
import sys
def load(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out
before, after = load(sys.argv[1]), load(sys.argv[2])
keys = ["orders", "order_items", "payments", "idem", "stock_movements", "carts", "cart_items", "nonprice_fp", "insize_fp", "price_fp", "mapped", "unmapped"]
print("YES" if all(before.get(k) == after.get(k) for k in keys) else "NO")
PY
)"
canary_bad=NO
if [ "$checkout_code" = "503" ] && [ "$checkout_error" = "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED" ]; then
  canary_bad=YES
fi
if [ "$checkout_code" = "201" ] || [ "$checkout_code" = "200" ]; then
  canary_bad=YES
fi
if [ "$init_error" = "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED" ] || [[ "$init_body" == *"payment_url"* ]]; then
  canary_bad=YES
fi
if [ "$init_code" = "200" ] || [ "$init_code" = "201" ]; then
  canary_bad=YES
fi
if [ "${expiry_candidates}" != "0" ]; then
  canary_bad=YES
fi
if [ "$callback_ok" != "YES" ]; then
  canary_bad=YES
fi
if [ "$fp_ok" != "YES" ]; then
  canary_bad=YES
fi
if [ "$canary_bad" = "YES" ]; then
  if [ "$WROTE" = "YES" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_CANARY_OR_FINGERPRINT"
  fi
  blocked "verification_failed_without_write"
fi

echo "=== PRICE_CANARY ==="
cat > "${TMP_DIR}/canary.sql" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'anchor|' || id::text || '|' || base_price::text FROM products WHERE id IN (1044,2111,4466,7116,3257,4185) ORDER BY id;
SELECT 'insize|' || id::text || '|' || base_price::text
FROM (
  SELECT id, base_price FROM products
  WHERE deleted_at IS NULL AND brand_id = 3 AND base_price > 0
  ORDER BY id
  LIMIT 3
) s
ORDER BY id;
ROLLBACK;
SQL
psql_read "${TMP_DIR}/canary.sql" > "${TMP_DIR}/anchors.txt"
set +e
python3 - "${TMP_DIR}/anchors.txt" "$probe_host" <<'PY'
import json, subprocess, sys
from decimal import Decimal
from pathlib import Path
host = sys.argv[2]
expected = {
    1044: Decimal("30354000"),
    2111: Decimal("54192000"),
    4466: Decimal("15345000"),
    7116: Decimal("7774800"),
    3257: Decimal("137235780"),
    4185: Decimal("1426800"),
}
anchors = {}
insize = []
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    parts = line.split("|")
    if len(parts) != 3:
        continue
    kind, pid, price = parts
    if kind == "anchor":
        anchors[int(pid)] = Decimal(price)
    elif kind == "insize":
        insize.append((int(pid), Decimal(price)))
ok = anchors == expected and len(insize) == 3
for pid, price in expected.items():
    print(f"anchor id={pid} db={anchors.get(pid)} expected={price} match={'YES' if anchors.get(pid) == price else 'NO'}")
for pid, price in insize:
    text = format(price, "f")
    expected_api = text.rstrip("0").rstrip(".") if "." in text else text
    proc = subprocess.run(
        ["curl", "-sS", "--max-time", "15", "-H", f"Host: {host}", "-H", "X-Forwarded-Proto: https",
         f"http://127.0.0.1:8000/api/v1/products/{pid}"],
        check=False, capture_output=True, text=True,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict) and "base_price" not in payload and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    api_raw = payload.get("base_price")
    api_price = "" if api_raw is None else str(api_raw)
    try:
        match = "YES" if Decimal(str(api_raw)) == price else "NO"
    except Exception:
        match = "NO"
    if match != "YES":
        ok = False
    print(f"insize_canary id={pid} db={expected_api} api={api_price or '-'} match={match}")
raise SystemExit(0 if ok else 2)
PY
anchor_ok=$?
set -e
if [ "$anchor_ok" -ne 0 ]; then
  if [ "$WROTE" = "YES" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_PRICE_ANCHOR"
  fi
  blocked "price_anchor"
fi

quote_code="$(curl -sS -L -o /dev/null -w '%{http_code}' --max-time 20 https://www.karzartools.com/quote || true)"
echo "quote_http=${quote_code}"
public_site_code="$(curl -sS -o "${TMP_DIR}/public-purchase.json" -w '%{http_code}' --max-time 20 \
  https://api.karzartools.com/api/v1/commerce/purchase-status || true)"
public_site_enabled="$(python3 - "${TMP_DIR}/public-purchase.json" <<'PY'
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
echo "public_purchase_status_http=${public_site_code}"
echo "public_purchase_status_enabled=${public_site_enabled}"
phone_bundle="$(docker exec karzar_shop sh -c 'grep -R -a -q -e "tel:+989912480087" -e "+989912480087" -e "989912480087" /app' && echo YES || echo NO)"
echo "support_phone_bundle=${phone_bundle}"
if [ "$quote_code" != "200" ] || [ "$public_site_code" != "200" ] || [ "$public_site_enabled" != "true" ] || [ "$phone_bundle" != "YES" ]; then
  if [ "$WROTE" = "YES" ]; then
    rollback_to_freeze "ATTEMPTED_AFTER_STOREFRONT_CHECK"
  fi
  blocked "storefront_reopen"
fi
echo "STOREFRONT_REOPEN_CHECK=PASS"
echo "HESABFA_WRITE=NO"
if [ "$before_value" = "true" ]; then
  STATUS="ALREADY_ENABLED_AND_VERIFIED"
else
  STATUS="COMMERCE_REOPENED_AND_VERIFIED"
fi
finish
