#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[SEC-001] Running secret hygiene checks..."

echo "- Checking tracked key material patterns"
if rg -n --hidden --glob '!.git/**' --glob '!**/node_modules/**' --glob '!**/.next/**' --glob '!**/dist/**' \
  '(-----BEGIN (RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z\-_]{35})' \
  .; then
  echo "Found potential secret material in tracked files."
  exit 1
fi

echo "- Checking for committed non-example .env files"
if git ls-files | rg -n '(^|/)\.env(\..+)?$' | rg -v '(\.env(\.example|\.staging\.example)?$|\.env\.[^/]+\.template$)'; then
  echo "Found tracked runtime .env file(s)."
  exit 1
fi

echo "- Verifying admin noindex/X-Robots markers"
rg -n 'robots:\s*\{\s*index:\s*false' frontend/admin-panel/src/app/layout.tsx >/dev/null
rg -n 'X-Robots-Tag' frontend/admin-panel/src/lib/security-headers.ts >/dev/null
rg -n 'securityHeaders' frontend/admin-panel/next.config.ts >/dev/null

echo "[SEC-001] Security hygiene checks passed."
