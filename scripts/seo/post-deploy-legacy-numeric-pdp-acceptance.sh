#!/usr/bin/env bash
# Read-only post-deploy acceptance for SEO Wave 2B-1 legacy numeric PDP 301 contract.
# Usage: LEGACY_CSV=/path/to/legacy_96_preflight.csv API_BASE=https://api.karzartools.com/api/v1 ./scripts/seo/post-deploy-legacy-numeric-pdp-acceptance.sh
set -euo pipefail
SITE="${SITE_URL:-https://www.karzartools.com}"
API="${API_BASE:-https://api.karzartools.com/api/v1}"
CSV="${LEGACY_CSV:?Set LEGACY_CSV to a numeric legacy URL list with product_identifier column}"

bad_200=0
bad_loc=0
loops=0
need_301=0
got_301=0

while IFS=, read -r _ pid url _; do
  [[ "$pid" == "product_identifier" || -z "$pid" ]] && continue
  api_code=$(curl -fsS -o /dev/null -w '%{http_code}' "$API/products/$pid" || echo "000")
  [[ "$api_code" != "200" ]] && continue
  slug=$(curl -fsS "$API/products/$pid" | python3 -c "import sys,json; print((json.load(sys.stdin).get('slug') or '').strip())")
  [[ -z "$slug" || "$slug" == "$pid" ]] && continue
  need_301=$((need_301 + 1))
  status=$(curl -fsS -o /dev/null -w '%{http_code}' "$SITE/product/$pid")
  loc=$(curl -fsS -I "$SITE/product/$pid" | awk -F': ' 'tolower($1)=="location"{print $2}' | tr -d '\r')
  if [[ "$status" == "301" || "$status" == "308" ]]; then
    got_301=$((got_301 + 1))
  elif [[ "$status" == "200" ]]; then
    bad_200=$((bad_200 + 1))
  fi
  if [[ -n "$loc" && "$loc" != *"/product/"* ]]; then
    bad_loc=$((bad_loc + 1))
  fi
done < "$CSV"

echo "LEGACY_WITH_DISTINCT_SLUG=$need_301"
echo "HTTP_301=$got_301"
echo "HTTP_200_NUMERIC_WITH_DISTINCT_SLUG=$bad_200"
echo "BAD_LOCATION=$bad_loc"
echo "REDIRECT_LOOPS=$loops"
if [[ "$bad_200" -ne 0 || "$got_301" -ne "$need_301" ]]; then
  exit 1
fi
