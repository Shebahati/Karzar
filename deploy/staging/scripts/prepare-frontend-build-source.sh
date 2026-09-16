#!/usr/bin/env bash
# Build-time source invariants before Storefront/Admin Docker builds.
# No runtime mutations — deploy-frontend.sh must not patch sources after images exist.
#
# Legacy deploy patches (classification):
#   remotePatterns wildcard (picsum → hostname "**"): REMOVE
#     Storefront uses explicit imageRemotePatterns(); Admin production build
#     (NODE_ENV=production) never includes picsum.dev hosts — API uploads via
#     api.karzartools.com/static/uploads/** remain allowed.
#   USE_MOCK default sed patch: REMOVE
#     Both apps default NEXT_PUBLIC_USE_MOCK to false in src/config/env.ts.
set -euo pipefail

: "${FRONTEND_ROOT:?Set FRONTEND_ROOT to the directory containing Storefront/ and admin-panel/}"

SHOP_DIR="${FRONTEND_ROOT}/Storefront"
ADMIN_DIR="${FRONTEND_ROOT}/admin-panel"

[[ -f "${SHOP_DIR}/next.config.ts" ]] || { echo "missing Storefront next.config.ts" >&2; exit 1; }
[[ -f "${ADMIN_DIR}/next.config.ts" ]] || { echo "missing admin next.config.ts" >&2; exit 1; }

grep -q 'imageRemotePatterns' "${SHOP_DIR}/next.config.ts" \
  || { echo "Storefront must use imageRemotePatterns()" >&2; exit 1; }

grep -q 'imageRemotePatterns' "${ADMIN_DIR}/next.config.ts" \
  || { echo "Admin must use imageRemotePatterns()" >&2; exit 1; }

grep -q 'NEXT_PUBLIC_USE_MOCK ?? "false"' "${SHOP_DIR}/src/config/env.ts" \
  || { echo "Storefront USE_MOCK must default false" >&2; exit 1; }

grep -q '(process.env.NEXT_PUBLIC_USE_MOCK ?? "false")' "${ADMIN_DIR}/src/config/env.ts" \
  || { echo "Admin USE_MOCK must default false" >&2; exit 1; }

echo "PREPARE_FRONTEND_BUILD_SOURCE_OK"
