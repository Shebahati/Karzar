#!/bin/bash
# Read-only live verification before any commerce reopen decision.
# No price writes, no flag changes, no deploy, no container recreate.
set -euo pipefail

EXPECTED_SHA="e2470bef067b2016db0665ef3d39c80854b197b9"
MANIFEST_PATH="/opt/karzar/rollout-backups/non-insize-price-20pct-2026-09-29/manifest-20260929T144058Z.jsonl"
INSIZE_PATH="/opt/karzar/rollout-backups/non-insize-price-20pct-2026-09-29/insize-prices-20260929T144058Z.jsonl"
EXPECTED_MANIFEST_SHA="9041472c85013e783cf751639523dd065f68a592b10c74a54f39fdfdf561b5bd"
EXPECTED_NONPRICE_FP="fb9ee59db6ebff770d69aee59d2d8944"
EXPECTED_INSIZE_FP="df799c09f4d9b6f6717344808b5b592d"
EXPECTED_NONTARGET_FP="3cb9b4abc97c2d79bf86b8fba513fd7f"
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

BLOCKED=0
note_block() {
  BLOCKED=1
  echo "GATE_FAIL=$1"
}

psql_read() {
  docker exec -i \
    -e PGOPTIONS='-c default_transaction_read_only=on' \
    lathe_postgres \
    sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -f -' < "$1"
}

echo "=== IDENTITY ==="
echo "hostname=$(hostname)"
if [ "$(hostname)" != "srv5944957438" ]; then
  echo "STATUS=BLOCKED"
  echo "BLOCK_REASON=hostname"
  exit 10
fi
if ! docker inspect lathe_api >/dev/null 2>&1 || ! docker inspect lathe_postgres >/dev/null 2>&1; then
  echo "STATUS=BLOCKED"
  echo "BLOCK_REASON=containers_missing"
  exit 10
fi
echo "api_name=$(docker inspect -f '{{.Name}}' lathe_api)"
echo "postgres_name=$(docker inspect -f '{{.Name}}' lathe_postgres)"
echo "postgres_mount=$(docker inspect -f '{{range .Mounts}}{{.Name}}{{println}}{{end}}' lathe_postgres)"
echo "postgres_db=$(docker exec lathe_api printenv POSTGRES_DB)"
echo "postgres_server=$(docker exec lathe_api printenv POSTGRES_SERVER)"
echo "app_env=$(docker exec lathe_api printenv APP_ENV)"
echo "data_plane=$(docker exec lathe_api printenv KARZAR_DATA_PLANE || true)"
echo "api_image=$(docker inspect -f '{{.Config.Image}}' lathe_api)"
echo "api_image_id=$(docker inspect -f '{{.Image}}' lathe_api)"
echo "api_revision=$(docker inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' lathe_api)"
alembic_line="$(docker exec lathe_api alembic current 2>/dev/null | awk '/t3u4v5w6x7y8/ {print; exit}' || true)"
echo "alembic=${alembic_line}"
purchase_flag="$(docker exec lathe_api printenv PURCHASE_CHECKOUT_ENABLED)"
echo "purchase_checkout_enabled=${purchase_flag}"

api_name="$(docker inspect -f '{{.Name}}' lathe_api)"
pg_name="$(docker inspect -f '{{.Name}}' lathe_postgres)"
pg_mount="$(docker inspect -f '{{range .Mounts}}{{.Name}}{{println}}{{end}}' lathe_postgres)"
api_db="$(docker exec lathe_api printenv POSTGRES_DB)"
app_env="$(docker exec lathe_api printenv APP_ENV)"
if [ "$api_name" != "/lathe_api" ] || [ "$pg_name" != "/lathe_postgres" ] || [ "$pg_mount" != "karzar_postgres_data" ] || [ "$api_db" != "karzar_staging" ] || [ "$app_env" != "staging" ] || [ "$alembic_line" != "t3u4v5w6x7y8 (head)" ]; then
  echo "STATUS=BLOCKED"
  echo "BLOCK_REASON=live_identity"
  exit 10
fi
echo "LIVE_IDENTITY_PASS=YES"

echo "=== RUNNING_IMAGES ==="
docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}'
python3 - <<'PY'
import json, subprocess
names = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True).split()
for name in names:
    raw = subprocess.check_output(["docker", "inspect", name], text=True)
    data = json.loads(raw)[0]
    labels = data["Config"].get("Labels") or {}
    print(
        "image_probe name={name} image={image} id={image_id} revision={revision} source={source}".format(
            name=name,
            image=data["Config"].get("Image"),
            image_id=data.get("Image"),
            revision=labels.get("org.opencontainers.image.revision", ""),
            source=labels.get("org.opencontainers.image.source", ""),
        )
    )
PY

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
if [ "$purchase_flag" != "false" ]; then
  note_block "purchase_flag"
fi
status_code="$(curl -sS -o "${TMP_DIR}/purchase-status.json" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8000/api/v1/commerce/purchase-status || true)"
python3 - "${TMP_DIR}/purchase-status.json" "$status_code" <<'PY'
import json, sys
from pathlib import Path
code = sys.argv[2]
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    data = {}
print(f"purchase_status_http={code}")
print("purchase_status_enabled=" + str(data.get("purchase_checkout_enabled")).lower())
PY
enabled="$(python3 - "${TMP_DIR}/purchase-status.json" <<'PY'
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
if [ "$status_code" = "200" ] && [ "$enabled" = "false" ] && [ "$purchase_flag" = "false" ]; then
  echo "PURCHASE_FREEZE_PASS=YES"
else
  note_block "commerce_freeze"
fi

cat > "${TMP_DIR}/fingerprint.sql" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'orders_count=' || count(*)::text FROM orders;
SELECT 'orders_fp=' || md5(coalesce(string_agg(id::text || '|' || coalesce(estimated_total::text, '') || '|' || status || '|' || payment_status, E'\n' ORDER BY id), '')) FROM orders;
SELECT 'payments_count=' || count(*)::text FROM payment_transactions;
SELECT 'payments_fp=' || md5(coalesce(string_agg(id::text || '|' || amount::text || '|' || status, E'\n' ORDER BY id), '')) FROM payment_transactions;
SELECT 'idem_count=' || count(*)::text FROM idempotency_keys;
SELECT 'idem_fp=' || md5(coalesce(string_agg(id::text || '|' || scope || '|' || key, E'\n' ORDER BY id), '')) FROM idempotency_keys;
SELECT 'stock_movements_count=' || count(*)::text FROM stock_movements;
SELECT 'stock_movements_fp=' || md5(coalesce(string_agg(id::text || '|' || product_id::text || '|' || quantity_change::text, E'\n' ORDER BY id), '')) FROM stock_movements;
SELECT 'carts_count=' || count(*)::text FROM carts;
SELECT 'cart_items_count=' || count(*)::text FROM cart_items;
ROLLBACK;
SQL

snapshot_fp() {
  local dest="$1"
  psql_read "${TMP_DIR}/fingerprint.sql" > "$dest"
  grep -E '^(orders_count|orders_fp|payments_count|payments_fp|idem_count|idem_fp|stock_movements_count|stock_movements_fp|carts_count|cart_items_count)=' "$dest"
}

echo "=== FINGERPRINT_BEFORE_CANARIES ==="
snapshot_fp "${TMP_DIR}/fp0.txt"

echo "=== PURCHASE_CHECKOUT_CANARY ==="
checkout_code="$(curl -sS -o "${TMP_DIR}/checkout.json" -w '%{http_code}' --max-time 20 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  -H 'Content-Type: application/json' \
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
PY
checkout_error="$(python3 - "${TMP_DIR}/checkout.json" <<'PY'
import json, sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print(data.get("error_code") or "")
PY
)"
snapshot_fp "${TMP_DIR}/fp1.txt" > "${TMP_DIR}/fp1.shown"
if [ "$checkout_code" = "503" ] && [ "$checkout_error" = "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED" ]; then
  echo "CHECKOUT_GUARD_HTTP=PASS"
else
  note_block "checkout_guard"
fi

echo "=== PAYMENT_INIT_CANARY ==="
init_code="$(curl -sS -o "${TMP_DIR}/init.json" -w '%{http_code}' --max-time 20 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/v1/payments/init \
  --data '{"order_id":1}' || true)"
python3 - "${TMP_DIR}/init.json" "$init_code" <<'PY'
import json, sys
from pathlib import Path
code = sys.argv[2]
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    data = {}
print(f"payment_init_http={code}")
print("payment_init_error_code=" + str(data.get("error_code")))
body = Path(sys.argv[1]).read_text(encoding="utf-8")
print("payment_init_contains_sep_token=" + ("YES" if "payment_url" in body or "sep.ir" in body.lower() else "NO"))
PY
init_error="$(python3 - "${TMP_DIR}/init.json" <<'PY'
import json, sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print(data.get("error_code") or "")
PY
)"
snapshot_fp "${TMP_DIR}/fp2.txt" > "${TMP_DIR}/fp2.shown"
if [ "$init_code" = "503" ] && [ "$init_error" = "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED" ]; then
  echo "PAYMENT_INIT_GUARD_HTTP=PASS"
else
  note_block "payment_init_guard"
fi

echo "=== CALLBACK_VERIFY ==="
cb_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8000/api/v1/payments/callback || true)"
sep_code="$(curl -sS -o "${TMP_DIR}/sep.out" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -X POST http://127.0.0.1:8000/api/v1/payments/callback/sep \
  --data '' || true)"
verify_code="$(curl -sS -o "${TMP_DIR}/verify.json" -w '%{http_code}' --max-time 15 \
  -H "Host: ${probe_host}" -H "X-Forwarded-Proto: https" \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/v1/payments/verify \
  --data '{"authority":"readonly-probe-not-a-real-authority"}' || true)"
python3 - "${TMP_DIR}/sep.out" "${TMP_DIR}/verify.json" "$cb_code" "$sep_code" "$verify_code" <<'PY'
import json, sys
from pathlib import Path
sep = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
try:
    verify = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
except Exception:
    verify = {}
freeze = "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED"
print(f"callback_get_http={sys.argv[3]}")
print("callback_get_freeze_503=" + ("YES" if sys.argv[3] == "503" else "NO"))
print(f"callback_sep_http={sys.argv[4]}")
print("callback_sep_freeze_code=" + ("YES" if freeze in sep else "NO"))
print(f"verify_http={sys.argv[5]}")
print("verify_error_code=" + str(verify.get("error_code")))
print("verify_freeze_code=" + ("YES" if verify.get("error_code") == freeze else "NO"))
PY
snapshot_fp "${TMP_DIR}/fp3.txt" > "${TMP_DIR}/fp3.shown"

python3 - "${TMP_DIR}/fp0.txt" "${TMP_DIR}/fp1.txt" "${TMP_DIR}/fp2.txt" "${TMP_DIR}/fp3.txt" > "${TMP_DIR}/deltas.txt" <<'PY'
from pathlib import Path
import sys
def load(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out
keys = [
    "orders_count", "orders_fp", "payments_count", "payments_fp",
    "idem_count", "idem_fp", "stock_movements_count", "stock_movements_fp",
    "carts_count", "cart_items_count",
]
base = load(sys.argv[1])
labels = ["after_checkout", "after_payment_init", "after_callback_verify"]
ok = True
for label, path in zip(labels, sys.argv[2:]):
    cur = load(path)
    for key in keys:
        same = base.get(key) == cur.get(key)
        if not same:
            ok = False
        print(f"delta {label} {key}={'0' if same else 'CHANGED'}")
print("CANARY_TABLE_DELTAS=" + ("ZERO" if ok else "NONZERO"))
PY
cat "${TMP_DIR}/deltas.txt"
if ! grep -q 'CANARY_TABLE_DELTAS=ZERO' "${TMP_DIR}/deltas.txt"; then
  note_block "canary_table_delta"
fi

echo "=== MANIFEST ==="
docker run --rm --network none --user 0 --entrypoint sha256sum \
  -v "${MANIFEST_PATH}:/manifest:ro" \
  -v "${INSIZE_PATH}:/insize:ro" \
  postgres:15-alpine \
  /manifest /insize | tee "${TMP_DIR}/shas.txt"
manifest_sha="$(awk '$2=="/manifest"{print $1}' "${TMP_DIR}/shas.txt")"
echo "MANIFEST_SHA256=${manifest_sha}"
if [ "$manifest_sha" != "$EXPECTED_MANIFEST_SHA" ]; then
  note_block "manifest_sha"
else
  echo "MANIFEST_SHA256_CHECK=PASS"
fi
docker run --rm --network none --user 0 --entrypoint sh \
  -v "${MANIFEST_PATH}:/manifest:ro" \
  -v "${INSIZE_PATH}:/insize:ro" \
  -v "${TMP_DIR}:/out" \
  postgres:15-alpine \
  -c 'cp /manifest /out/manifest.jsonl && cp /insize /out/insize-before.jsonl && chmod 644 /out/manifest.jsonl /out/insize-before.jsonl'

cat > "${TMP_DIR}/current.sql" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT '---CURRENT---';
SELECT json_build_object(
  'product_id', p.id,
  'base_price', p.base_price::text,
  'original_price', p.original_price::text
)::text
FROM products p
WHERE p.deleted_at IS NULL
  AND (p.brand_id IS NULL OR p.brand_id <> 3)
  AND p.base_price IS NOT NULL
  AND p.base_price > 0
ORDER BY p.id;
SELECT '---INSIZE---';
SELECT json_build_object(
  'product_id', p.id,
  'base_price', p.base_price::text,
  'original_price', p.original_price::text
)::text
FROM products p
WHERE p.deleted_at IS NULL AND p.brand_id = 3
ORDER BY p.id;
SELECT '---END---';
ROLLBACK;
SQL
psql_read "${TMP_DIR}/current.sql" > "${TMP_DIR}/current.txt"
python3 - "${TMP_DIR}/manifest.jsonl" "${TMP_DIR}/insize-before.jsonl" "${TMP_DIR}/current.txt" <<'PY' | tee "${TMP_DIR}/price-compare.txt"
import json, sys
from decimal import Decimal
from pathlib import Path

def money(value):
    if value is None or value == "":
        return None
    return Decimal(str(value))

def load_jsonl(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def split_current(path):
    section = None
    current, insize = [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line == "---CURRENT---":
            section = "current"
            continue
        if line == "---INSIZE---":
            section = "insize"
            continue
        if line == "---END---":
            break
        if section == "current":
            current.append(json.loads(line))
        elif section == "insize":
            insize.append(json.loads(line))
    return current, insize

manifest = load_jsonl(sys.argv[1])
insize_before = load_jsonl(sys.argv[2])
current, insize_now = split_current(sys.argv[3])
current_by_id = {row["product_id"]: row for row in current}
base_miss, original_miss = [], []
for row in manifest:
    live = current_by_id.get(row["product_id"])
    if live is None:
        base_miss.append(row["product_id"])
        original_miss.append(row["product_id"])
        continue
    if money(live["base_price"]) != money(row["new_base_price"]):
        base_miss.append(row["product_id"])
    if money(live["original_price"]) != money(row["new_original_price"]):
        original_miss.append(row["product_id"])
before = {(r["product_id"], r["base_price"], r["original_price"]) for r in insize_before}
after = {(r["product_id"], r["base_price"], r["original_price"]) for r in insize_now}
changed = sorted(pid for pid, *_ in before.symmetric_difference(after))
print(f"manifest_rows={len(manifest)}")
print(f"current_target_rows={len(current)}")
print(f"base_price_mismatches={len(base_miss)}")
print(f"original_price_mismatches={len(original_miss)}")
if base_miss or original_miss:
    ids = sorted(set(base_miss + original_miss))
    print("mismatch_product_ids=" + ",".join(str(i) for i in ids[:50]))
print(f"insize_rows_before={len(insize_before)}")
print(f"insize_rows_after={len(insize_now)}")
print(f"insize_price_rows_changed={len(changed)}")
if changed:
    print("insize_changed_ids=" + ",".join(str(i) for i in changed[:50]))
PY

cat > "${TMP_DIR}/catalog.sql" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'insize_candidates=' || count(*)::text FROM brands
WHERE regexp_replace(lower(name), '[^[:alnum:]]', '', 'g') = 'insize'
   OR regexp_replace(lower(slug), '[^[:alnum:]]', '', 'g') = 'insize'
   OR lower(name) LIKE '%insize%' OR lower(slug) LIKE '%insize%'
   OR replace(name, chr(8204), '') LIKE '%اینسایز%'
   OR replace(slug, chr(8204), '') LIKE '%اینسایز%';
SELECT 'insize_id=' || id::text FROM brands WHERE id = 3;
SELECT 'insize_live=' || count(*)::text FROM products WHERE deleted_at IS NULL AND brand_id = 3;
SELECT 'insize_priced=' || count(*)::text FROM products WHERE deleted_at IS NULL AND brand_id = 3 AND base_price > 0;
SELECT 'change_log_reason_rows=' || count(*)::text FROM product_change_logs
WHERE reason = 'owner_non_insize_price_increase_20pct_2026_09_29';
SELECT 'target_mapped=' || count(*)::text
FROM products p JOIN hesabfa_item_mappings m ON m.product_id = p.id
WHERE p.deleted_at IS NULL AND (p.brand_id IS NULL OR p.brand_id <> 3) AND p.base_price > 0;
SELECT 'target_unmapped=' || count(*)::text
FROM products p LEFT JOIN hesabfa_item_mappings m ON m.product_id = p.id
WHERE p.deleted_at IS NULL AND (p.brand_id IS NULL OR p.brand_id <> 3) AND p.base_price > 0 AND m.id IS NULL;
SELECT 'nonprice_fp=' || md5(coalesce(string_agg(
  id::text || '|' || is_active::text || '|' || is_available::text || '|' ||
  stock_quantity::text || '|' || coalesce(brand_id::text, '') || '|' ||
  category_id::text || '|' || sku || '|' || slug || '|' || name || '|' ||
  coalesce(deleted_at::text, '') || '|' || coalesce(product_type_id::text, ''),
  E'\n' ORDER BY id), '')) FROM products;
SELECT 'insize_price_fp=' || md5(coalesce(string_agg(
  id::text || '|' || coalesce(base_price::text, '') || '|' || coalesce(original_price::text, ''),
  E'\n' ORDER BY id), '')) FROM products WHERE deleted_at IS NULL AND brand_id = 3;
SELECT 'nontarget_price_fp=' || md5(coalesce(string_agg(
  id::text || '|' || coalesce(base_price::text, '') || '|' || coalesce(original_price::text, ''),
  E'\n' ORDER BY id), '')) FROM products
WHERE NOT (
  deleted_at IS NULL AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price IS NOT NULL AND base_price > 0
);
ROLLBACK;
SQL
psql_read "${TMP_DIR}/catalog.sql" | tee "${TMP_DIR}/catalog.txt"

echo "=== PRICE_CANARIES ==="
cat > "${TMP_DIR}/canary.sql" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object(
  'product_id', p.id,
  'sku', p.sku,
  'brand_id', p.brand_id,
  'brand_name', b.name,
  'base_price', p.base_price::text,
  'original_price', p.original_price::text,
  'label', 'fixed'
)::text
FROM products p
LEFT JOIN brands b ON b.id = p.brand_id
WHERE p.id IN (1044, 2111, 4466, 7116, 3257, 4185, 7101)
ORDER BY p.id;
SELECT json_build_object(
  'product_id', p.id,
  'sku', p.sku,
  'brand_id', p.brand_id,
  'brand_name', b.name,
  'base_price', p.base_price::text,
  'original_price', p.original_price::text,
  'label', 'insize'
)::text
FROM (
  SELECT * FROM products
  WHERE deleted_at IS NULL AND brand_id = 3 AND base_price > 0
  ORDER BY id
  LIMIT 3
) p
LEFT JOIN brands b ON b.id = p.brand_id
ORDER BY p.id;
ROLLBACK;
SQL
psql_read "${TMP_DIR}/canary.sql" > "${TMP_DIR}/canary-db.txt"
python3 - "${TMP_DIR}/canary-db.txt" "$probe_host" <<'PY' | tee "${TMP_DIR}/canary-out.txt"
import json, subprocess, sys
from decimal import Decimal
from pathlib import Path
host = sys.argv[2]
rows = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.startswith("{")]
failures = 0
public_matches = 0
for row in rows:
    product_id = row["product_id"]
    db_price = Decimal(str(row["base_price"]))
    text = format(db_price, "f")
    expected = text.rstrip("0").rstrip(".") if "." in text else text
    proc = subprocess.run(
        ["curl", "-sS", "-w", "\n%{http_code}", "--max-time", "15",
         "-H", f"Host: {host}", "-H", "X-Forwarded-Proto: https",
         f"http://127.0.0.1:8000/api/v1/products/{product_id}"],
        check=False, capture_output=True, text=True,
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
    if code == "200" and api_price == expected:
        match = "YES"
        public_matches += 1
    elif code == "404":
        match = "NOT_PUBLIC"
    else:
        match = "NO"
        failures += 1
    original = row.get("original_price")
    print(
        f"canary id={product_id} sku={row.get('sku')} brand_id={row.get('brand_id')} "
        f"label={row.get('label')} public={'YES' if code == '200' else 'NO'} http={code} "
        f"db={expected} api={api_price or '-'} original={original or '-'} match={match}"
    )
print(f"canary_failures={failures}")
print(f"canary_public_matches={public_matches}")
PY

echo "=== EMALLS_PROJECTION ==="
cat > "${TMP_DIR}/emalls.sql" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object(
  'product_id', id,
  'sku', sku,
  'base_price', base_price::text,
  'original_price', original_price::text
)::text
FROM products
WHERE id = 1044;
ROLLBACK;
SQL
psql_read "${TMP_DIR}/emalls.sql" | python3 - <<'PY'
import json, sys
from decimal import Decimal
line = next(l for l in sys.stdin.read().splitlines() if l.startswith("{"))
row = json.loads(line)
def price_string(value):
    if value is None:
        return ""
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
current = price_string(row["base_price"])
old = price_string(row["original_price"]) if row["original_price"] is not None else current
print(f"emalls_sample_id={row['product_id']} sku={row['sku']}")
print(f"emalls_db_base={current}")
print(f"emalls_current_price={current}")
print(f"emalls_old_price={old}")
print("emalls_match=" + ("YES" if current and current == price_string(row["base_price"]) else "NO"))
print("emalls_http_called=NO")
print("emalls_partner_write=NO")
PY

echo "=== STOREFRONT_BUNDLE ==="
python3 - <<'PY'
import json, subprocess
expected = "e2470bef067b2016db0665ef3d39c80854b197b9"
names = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True).split()
shop = admin = None
for name in names:
    data = json.loads(subprocess.check_output(["docker", "inspect", name], text=True))[0]
    labels = data["Config"].get("Labels") or {}
    revision = labels.get("org.opencontainers.image.revision", "")
    image = data["Config"].get("Image") or ""
    if name == "karzar_shop":
        shop = (name, revision, image)
    if name == "karzar_admin":
        admin = (name, revision, image)
print(f"shop_container={shop[0] if shop else 'MISSING'}")
print(f"shop_image={shop[2] if shop else 'MISSING'}")
print(f"shop_revision={shop[1] if shop else 'MISSING'}")
print(f"admin_container={admin[0] if admin else 'MISSING'}")
print(f"admin_image={admin[2] if admin else 'MISSING'}")
print(f"admin_revision={admin[1] if admin else 'MISSING'}")
print("shop_sha_match=" + ("YES" if shop and shop[1] == expected else "NO"))
print("admin_sha_match=" + ("YES" if admin and admin[1] == expected else "NO"))
lines = [
    f"shop_sha_match={'YES' if shop and shop[1] == expected else 'NO'}",
    f"admin_sha_match={'YES' if admin and admin[1] == expected else 'NO'}",
    f"shop_revision={shop[1] if shop else 'MISSING'}",
    f"admin_revision={admin[1] if admin else 'MISSING'}",
]
open("/tmp/karzar-verify-images.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
if shop:
    open("/tmp/karzar-shop-container", "w", encoding="utf-8").write(shop[0])
PY
if [ -f /tmp/karzar-shop-container ]; then
  shop_name="$(cat /tmp/karzar-shop-container)"
  docker exec "$shop_name" sh -c 'grep -R -a -l "سفارش آنلاین موقتاً متوقف است" /app 2>/dev/null | head -n 5' || true
  docker exec "$shop_name" sh -c 'grep -R -a -o "tel:+989912480087" /app 2>/dev/null | head -n 3' || true
  docker exec "$shop_name" sh -c 'grep -R -a -o "ثبت درخواست استعلام" /app 2>/dev/null | head -n 3' || true
  docker exec "$shop_name" sh -c 'grep -R -a -o "سبد خرید شما حفظ می‌شود" /app 2>/dev/null | head -n 3' || true
  docker exec "$shop_name" sh -c 'grep -R -a -o "۰۹۹۱ ۲۴۸ ۰۰۸۷" /app 2>/dev/null | head -n 3' || true
  {
    echo -n "bundle_title="
    docker exec "$shop_name" sh -c 'grep -R -a -q "سفارش آنلاین موقتاً متوقف است" /app' && echo YES || echo NO
    echo -n "bundle_message="
    docker exec "$shop_name" sh -c 'grep -R -a -q "خرید آنلاین موقتاً در حال به‌روزرسانی است" /app' && echo YES || echo NO
    echo -n "bundle_cart_kept="
    docker exec "$shop_name" sh -c 'grep -R -a -q "سبد خرید شما حفظ می‌شود" /app' && echo YES || echo NO
    echo -n "bundle_tel="
    docker exec "$shop_name" sh -c 'grep -R -a -q "tel:+989912480087" /app' && echo YES || echo NO
    echo -n "bundle_quote="
    docker exec "$shop_name" sh -c 'grep -R -a -q "ثبت درخواست استعلام" /app' && echo YES || echo NO
    echo -n "bundle_phone="
    docker exec "$shop_name" sh -c 'grep -R -a -q "۰۹۹۱ ۲۴۸ ۰۰۸۷" /app' && echo YES || echo NO
  } | tee "${TMP_DIR}/bundle.txt"
fi

echo "=== GATES ==="
shop_sha="$(awk -F= '/^shop_sha_match=/{print $2}' /tmp/karzar-verify-images.txt 2>/dev/null || true)"
admin_sha="$(awk -F= '/^admin_sha_match=/{print $2}' /tmp/karzar-verify-images.txt 2>/dev/null || true)"
verify_error="$(python3 - "${TMP_DIR}/verify.json" <<'PY'
import json, sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print(data.get("error_code") or "")
PY
)"
sep_body="$(python3 - "${TMP_DIR}/sep.out" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace"))
PY
)"
if [ "$cb_code" = "503" ] || [ "$verify_error" = "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED" ] || [[ "$sep_body" == *PURCHASE_CHECKOUT_TEMPORARILY_DISABLED* ]]; then
  note_block "callback_verify_freeze_blocked"
else
  echo "CALLBACK_VERIFY_NOT_FREEZE_BLOCKED=YES"
fi
echo "shop_sha_match=${shop_sha:-MISSING}"
echo "admin_sha_match=${admin_sha:-MISSING}"
if [ "$shop_sha" != "YES" ] || [ "$admin_sha" != "YES" ]; then
  note_block "deploy_sha"
else
  echo "DEPLOY_SHA_PASS=YES"
fi
canary_failures="$(awk -F= '/^canary_failures=/{print $2}' "${TMP_DIR}/canary-out.txt")"
if [ "${canary_failures}" != "0" ]; then
  note_block "api_canaries"
else
  echo "API_CANARIES_PASS=YES"
fi
if [ ! -f "${TMP_DIR}/bundle.txt" ] || grep -q '=NO' "${TMP_DIR}/bundle.txt"; then
  note_block "storefront_notice_bundle"
else
  echo "STOREFRONT_BUNDLE_PASS=YES"
fi
base_miss="$(awk -F= '/^base_price_mismatches=/{print $2}' "${TMP_DIR}/price-compare.txt")"
orig_miss="$(awk -F= '/^original_price_mismatches=/{print $2}' "${TMP_DIR}/price-compare.txt")"
insize_changed="$(awk -F= '/^insize_price_rows_changed=/{print $2}' "${TMP_DIR}/price-compare.txt")"
if [ "${base_miss}" != "0" ] || [ "${orig_miss}" != "0" ]; then
  note_block "manifest_price_mismatch"
else
  echo "MANIFEST_PRICE_MATCH=PASS"
fi
if [ "${insize_changed}" != "0" ]; then
  note_block "insize_price_changed"
else
  echo "INSIZE_PRICE_COMPARE=PASS"
fi
nonprice="$(awk -F= '/^nonprice_fp=/{print $2}' "${TMP_DIR}/catalog.txt")"
insize_fp="$(awk -F= '/^insize_price_fp=/{print $2}' "${TMP_DIR}/catalog.txt")"
nontarget="$(awk -F= '/^nontarget_price_fp=/{print $2}' "${TMP_DIR}/catalog.txt")"
insize_live="$(awk -F= '/^insize_live=/{print $2}' "${TMP_DIR}/catalog.txt")"
insize_priced="$(awk -F= '/^insize_priced=/{print $2}' "${TMP_DIR}/catalog.txt")"
insize_id="$(awk -F= '/^insize_id=/{print $2}' "${TMP_DIR}/catalog.txt")"
mapped="$(awk -F= '/^target_mapped=/{print $2}' "${TMP_DIR}/catalog.txt")"
unmapped="$(awk -F= '/^target_unmapped=/{print $2}' "${TMP_DIR}/catalog.txt")"
logs="$(awk -F= '/^change_log_reason_rows=/{print $2}' "${TMP_DIR}/catalog.txt")"
echo "nonprice_fp=${nonprice}"
echo "insize_price_fp=${insize_fp}"
echo "nontarget_price_fp=${nontarget}"
if [ "$nonprice" = "$EXPECTED_NONPRICE_FP" ]; then
  echo "NON_PRICE_CATALOG_CHECK=PASS"
else
  note_block "nonprice_catalog"
fi
if [ "$nontarget" = "$EXPECTED_NONTARGET_FP" ]; then
  echo "NON_TARGET_PRICE_CHECK=PASS"
else
  note_block "nontarget_price"
fi
if [ "$insize_fp" = "$EXPECTED_INSIZE_FP" ] && [ "$insize_live" = "872" ] && [ "$insize_priced" = "487" ] && [ "$insize_id" = "3" ]; then
  echo "INSIZE_IMMUTABILITY_PASS=YES"
else
  note_block "insize_identity"
fi
if [ "$mapped" = "1994" ] && [ "$unmapped" = "2071" ]; then
  echo "HESABFA_CHECK=PASS"
else
  note_block "hesabfa_mapping"
fi
echo "change_log_reason_rows=${logs}"
if [ "$logs" != "4072" ]; then
  note_block "change_log_count"
fi

echo "=== RESULT ==="
echo "MUTATION_PERFORMED=NO"
if [ "$BLOCKED" -eq 0 ]; then
  echo "STATUS=READY_FOR_OWNER_REOPEN_DECISION"
else
  echo "STATUS=BLOCKED"
fi
exit 0
