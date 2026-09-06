#!/usr/bin/env bash
# Local selftests for the verified delta-rsync handoff. No SSH, no live VPS.
# Covers unchanged / changed / new / delete / failed transfer / corruption.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-tree-lib.sh
source "${SCRIPT_DIR}/deploy-tree-lib.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
fail() {
  echo "FAIL: $*" >&2
  exit 1
}
pass() {
  echo "PASS: $*"
  PASS=$((PASS + 1))
}

make_min_tree() {
  local root="$1"
  mkdir -p \
    "$root/app" \
    "$root/deploy/staging/scripts" \
    "$root/frontend/Storefront" \
    "$root/frontend/admin-panel"
  echo 'backend' > "$root/app/main.py"
  echo 'deploy-frontend' > "$root/deploy/staging/scripts/deploy-frontend.sh"
  echo 'deploy-backend' > "$root/deploy/staging/scripts/deploy-backend.sh"
  echo 'storefront' > "$root/frontend/Storefront/index.html"
  echo 'admin' > "$root/frontend/admin-panel/index.html"
}

sync_live_after_verify() {
  local incoming="$1" live="$2" sha="$3" manifest_sha="$4"
  if ! REQUIRE_HANDOFF_COMPLETE=1 WRITE_HANDOFF_COMPLETE=0 \
      GITHUB_SHA="$sha" EXPECTED_SHA="$sha" \
      EXPECTED_MANIFEST_SHA="$manifest_sha" \
      INCOMING_DIR="$incoming" \
      STAGED_DIR="${incoming}/tree" \
      bash "${SCRIPT_DIR}/verify-incoming-source.sh"; then
    echo "SYNC_TO_LIVE=SKIPPED"
    return 1
  fi
  mkdir -p "$live"
  rsync -a --delete "${incoming}/tree"/ "$live"/
}

rsync_stats() {
  local src="$1" dest="$2"
  mkdir -p "$dest"
  karzar_rsync_delta "$src" "$dest"
}

transferred_regular_files() {
  local stats="$1"
  printf '%s\n' "$stats" | awk -F': ' '/Number of regular files transferred/{gsub(/[^0-9]/,"",$2); print $2+0; found=1} END{if(!found) print -1}'
}

literal_data_bytes() {
  local stats="$1"
  printf '%s\n' "$stats" | awk '/Literal data:/{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+$/){print $i; exit}}'
}

# --- A. unchanged file ---
A_SRC="$TMP/a-src"
A_SEED="$TMP/a-seed"
A_IN="$TMP/a-in/tree"
make_min_tree "$A_SRC"
dd if=/dev/urandom of="$A_SRC/frontend/Storefront/hero.bin" bs=1024 count=256 status=none
cp -a "$A_SRC/." "$A_SEED/"
mkdir -p "$A_IN"
karzar_seed_incoming_tree "$A_SEED" "$A_SEED/frontend" "$A_IN"
A_STATS="$(rsync_stats "$A_SRC" "$A_IN" 2>&1)"
echo "$A_STATS"
A_XFER="$(transferred_regular_files "$A_STATS")"
A_LIT="$(literal_data_bytes "$A_STATS")"
[[ "$A_XFER" == "0" ]] || fail "unchanged: expected 0 regular files transferred, got ${A_XFER}"
[[ "${A_LIT:-1}" == "0" ]] || fail "unchanged: expected 0 literal data bytes, got ${A_LIT}"
karzar_write_deploy_manifest "$A_SRC" "$TMP/a-in/${KARZAR_MANIFEST_NAME}"
karzar_write_handoff_complete "$TMP/a-in" testhashA "$KARZAR_MANIFEST_SHA"
REQUIRE_HANDOFF_COMPLETE=1 WRITE_HANDOFF_COMPLETE=0 \
  GITHUB_SHA=testhashA EXPECTED_SHA=testhashA \
  EXPECTED_MANIFEST_SHA="$KARZAR_MANIFEST_SHA" \
  INCOMING_DIR="$TMP/a-in" \
  bash "${SCRIPT_DIR}/verify-incoming-source.sh" >/dev/null
cmp -s "$A_SRC/frontend/Storefront/hero.bin" "$A_IN/frontend/Storefront/hero.bin" \
  || fail "unchanged: staged hero.bin differs"
pass "UNCHANGED_TEST (transferred=${A_XFER} literal=${A_LIT})"

# --- B. changed file ---
B_SRC="$TMP/b-src"
B_SEED="$TMP/b-seed"
B_IN="$TMP/b-in/tree"
make_min_tree "$B_SRC"
echo 'old-hero' > "$B_SRC/frontend/Storefront/hero.bin"
cp -a "$B_SRC/." "$B_SEED/"
echo 'new-hero' > "$B_SRC/frontend/Storefront/hero.bin"
mkdir -p "$B_IN"
karzar_seed_incoming_tree "$B_SEED" "$B_SEED/frontend" "$B_IN"
echo 'old-hero' > "$TMP/b-old-expect"
cmp -s "$B_IN/frontend/Storefront/hero.bin" "$TMP/b-old-expect" \
  || fail "changed: seed did not start with old content"
B_STATS="$(rsync_stats "$B_SRC" "$B_IN" 2>&1)"
echo "$B_STATS"
B_XFER="$(transferred_regular_files "$B_STATS")"
[[ "$B_XFER" -ge 1 ]] || fail "changed: expected at least 1 file transferred, got ${B_XFER}"
[[ "$(cat "$B_IN/frontend/Storefront/hero.bin")" == "new-hero" ]] \
  || fail "changed: staged file not updated"
karzar_write_deploy_manifest "$B_SRC" "$TMP/b-in/${KARZAR_MANIFEST_NAME}"
karzar_write_handoff_complete "$TMP/b-in" testhashB "$KARZAR_MANIFEST_SHA"
REQUIRE_HANDOFF_COMPLETE=1 \
  GITHUB_SHA=testhashB EXPECTED_SHA=testhashB \
  EXPECTED_MANIFEST_SHA="$KARZAR_MANIFEST_SHA" \
  INCOMING_DIR="$TMP/b-in" \
  bash "${SCRIPT_DIR}/verify-incoming-source.sh" >/dev/null
pass "CHANGED_TEST (transferred=${B_XFER})"

# --- C. new file ---
C_SRC="$TMP/c-src"
C_SEED="$TMP/c-seed"
C_IN="$TMP/c-in/tree"
make_min_tree "$C_SRC"
cp -a "$C_SRC/." "$C_SEED/"
echo 'brand-new' > "$C_SRC/app/new_module.py"
mkdir -p "$C_IN"
karzar_seed_incoming_tree "$C_SEED" "$C_SEED/frontend" "$C_IN"
[[ ! -e "$C_IN/app/new_module.py" ]] || fail "new: seed should not already have new_module.py"
C_STATS="$(rsync_stats "$C_SRC" "$C_IN" 2>&1)"
echo "$C_STATS"
C_XFER="$(transferred_regular_files "$C_STATS")"
[[ "$C_XFER" -ge 1 ]] || fail "new: expected a transferred file, got ${C_XFER}"
[[ "$(cat "$C_IN/app/new_module.py")" == "brand-new" ]] || fail "new: file missing after rsync"
karzar_write_deploy_manifest "$C_SRC" "$TMP/c-in/${KARZAR_MANIFEST_NAME}"
karzar_write_handoff_complete "$TMP/c-in" testhashC "$KARZAR_MANIFEST_SHA"
REQUIRE_HANDOFF_COMPLETE=1 \
  GITHUB_SHA=testhashC EXPECTED_SHA=testhashC \
  EXPECTED_MANIFEST_SHA="$KARZAR_MANIFEST_SHA" \
  INCOMING_DIR="$TMP/c-in" \
  bash "${SCRIPT_DIR}/verify-incoming-source.sh" >/dev/null
pass "NEW_FILE_TEST (transferred=${C_XFER})"

# --- D. deleted file (--delete must drop seed-only paths) ---
D_SRC="$TMP/d-src"
D_SEED="$TMP/d-seed"
D_IN="$TMP/d-in/tree"
make_min_tree "$D_SRC"
cp -a "$D_SRC/." "$D_SEED/"
echo 'stale' > "$D_SEED/app/removed.py"
mkdir -p "$D_IN"
karzar_seed_incoming_tree "$D_SEED" "$D_SEED/frontend" "$D_IN"
[[ -f "$D_IN/app/removed.py" ]] || fail "delete: seed should contain removed.py"
D_STATS="$(rsync_stats "$D_SRC" "$D_IN" 2>&1)"
echo "$D_STATS"
[[ ! -e "$D_IN/app/removed.py" ]] || fail "delete: --delete did not remove seed-only file"
karzar_write_deploy_manifest "$D_SRC" "$TMP/d-in/${KARZAR_MANIFEST_NAME}"
# Manifest must not mention removed.py
if grep -q 'removed.py' "$TMP/d-in/${KARZAR_MANIFEST_NAME}"; then
  fail "delete: manifest still lists removed.py"
fi
karzar_write_handoff_complete "$TMP/d-in" testhashD "$KARZAR_MANIFEST_SHA"
REQUIRE_HANDOFF_COMPLETE=1 \
  GITHUB_SHA=testhashD EXPECTED_SHA=testhashD \
  EXPECTED_MANIFEST_SHA="$KARZAR_MANIFEST_SHA" \
  INCOMING_DIR="$TMP/d-in" \
  bash "${SCRIPT_DIR}/verify-incoming-source.sh" >/dev/null
pass "DELETE_TEST"

# --- E. interrupted / failed transfer: no HANDOFF_COMPLETE → live skip ---
E_SRC="$TMP/e-src"
E_INCOMING="$TMP/e-in"
E_LIVE="$TMP/e-live"
make_min_tree "$E_SRC"
mkdir -p "$E_INCOMING/tree" "$E_LIVE"
cp -a "$E_SRC/." "$E_INCOMING/tree/"
karzar_write_deploy_manifest "$E_SRC" "$E_INCOMING/${KARZAR_MANIFEST_NAME}"
echo 'live-original' > "$E_LIVE/keep.txt"
E_LIVE_HASH="$(sha256sum "$E_LIVE/keep.txt")"
E_OUT="$(set +e; sync_live_after_verify "$E_INCOMING" "$E_LIVE" testhashE "$KARZAR_MANIFEST_SHA" 2>&1; echo EXIT:$?)"
printf '%s\n' "$E_OUT"
printf '%s\n' "$E_OUT" | grep -q 'HANDOFF_COMPLETE absent' \
  || fail "failed-transfer: expected HANDOFF_COMPLETE absent"
printf '%s\n' "$E_OUT" | grep -q 'SYNC_TO_LIVE=SKIPPED' \
  || fail "failed-transfer: live sync was not skipped"
[[ "$(sha256sum "$E_LIVE/keep.txt")" == "$E_LIVE_HASH" ]] \
  || fail "failed-transfer: live tree was mutated"
[[ ! -f "$E_LIVE/app/main.py" ]] || fail "failed-transfer: live received staged files"
pass "FAILED_TRANSFER_TEST"

# --- F. corrupted staged file: verify FAIL, live skip ---
F_SRC="$TMP/f-src"
F_INCOMING="$TMP/f-in"
F_LIVE="$TMP/f-live"
make_min_tree "$F_SRC"
mkdir -p "$F_INCOMING/tree" "$F_LIVE"
cp -a "$F_SRC/." "$F_INCOMING/tree/"
karzar_write_deploy_manifest "$F_SRC" "$F_INCOMING/${KARZAR_MANIFEST_NAME}"
karzar_write_handoff_complete "$F_INCOMING" testhashF "$KARZAR_MANIFEST_SHA"
echo 'tampered' > "$F_INCOMING/tree/app/main.py"
echo 'live-original' > "$F_LIVE/keep.txt"
F_LIVE_HASH="$(sha256sum "$F_LIVE/keep.txt")"
F_OUT="$(set +e; sync_live_after_verify "$F_INCOMING" "$F_LIVE" testhashF "$KARZAR_MANIFEST_SHA" 2>&1; echo EXIT:$?)"
printf '%s\n' "$F_OUT"
printf '%s\n' "$F_OUT" | grep -q 'VERIFY=FAIL' \
  || fail "corruption: expected VERIFY=FAIL"
printf '%s\n' "$F_OUT" | grep -q 'SYNC_TO_LIVE=SKIPPED' \
  || fail "corruption: live sync was not skipped"
[[ "$(sha256sum "$F_LIVE/keep.txt")" == "$F_LIVE_HASH" ]] \
  || fail "corruption: live tree was mutated"
pass "CORRUPTION_TEST"

# --- extras: seed must not mutate live; manifest SHA mismatch ---
G_LIVE_BE="$TMP/g-live-be"
G_LIVE_FE="$TMP/g-live-fe"
G_IN="$TMP/g-in/tree"
make_min_tree "$G_LIVE_BE"
mkdir -p "$G_LIVE_FE/Storefront"
echo 'fe-live' > "$G_LIVE_FE/Storefront/keep.bin"
echo 'secret' > "$G_LIVE_BE/.env"
echo 'secret-fe' > "$G_LIVE_FE/.env"
mkdir -p "$G_LIVE_BE/backups" "$G_LIVE_BE/data/uploads" "$G_LIVE_FE/node_modules" "$G_LIVE_FE/.next"
echo 'bak' > "$G_LIVE_BE/backups/db.sql"
echo 'up' > "$G_LIVE_BE/data/uploads/file.bin"
echo 'nm' > "$G_LIVE_FE/node_modules/pkg.js"
echo 'next' > "$G_LIVE_FE/.next/cache"
G_BE_HASH="$(sha256sum "$G_LIVE_BE/.env" "$G_LIVE_BE/app/main.py" "$G_LIVE_BE/backups/db.sql")"
G_FE_HASH="$(sha256sum "$G_LIVE_FE/.env" "$G_LIVE_FE/Storefront/keep.bin")"
karzar_seed_incoming_tree "$G_LIVE_BE" "$G_LIVE_FE" "$G_IN"
[[ "$(sha256sum "$G_LIVE_BE/.env" "$G_LIVE_BE/app/main.py" "$G_LIVE_BE/backups/db.sql")" == "$G_BE_HASH" ]] \
  || fail "seed mutated live backend"
[[ "$(sha256sum "$G_LIVE_FE/.env" "$G_LIVE_FE/Storefront/keep.bin")" == "$G_FE_HASH" ]] \
  || fail "seed mutated live frontend"
[[ ! -e "$G_IN/.env" ]] || fail "seed copied .env"
[[ ! -e "$G_IN/backups/db.sql" ]] || fail "seed copied backups"
[[ ! -e "$G_IN/data/uploads/file.bin" ]] || fail "seed copied uploads"
[[ ! -e "$G_IN/frontend/node_modules/pkg.js" ]] || fail "seed copied node_modules"
[[ ! -e "$G_IN/frontend/.next/cache" ]] || fail "seed copied .next"
[[ -f "$G_IN/frontend/Storefront/keep.bin" ]] || fail "seed missed live frontend asset"
pass "SEED_PRESERVES_LIVE_AND_EXCLUDES"

H_SRC="$TMP/h-src"
H_IN="$TMP/h-in"
make_min_tree "$H_SRC"
mkdir -p "$H_IN/tree"
cp -a "$H_SRC/." "$H_IN/tree/"
karzar_write_deploy_manifest "$H_SRC" "$H_IN/${KARZAR_MANIFEST_NAME}"
karzar_write_handoff_complete "$H_IN" testhashH "$KARZAR_MANIFEST_SHA"
if REQUIRE_HANDOFF_COMPLETE=1 \
    GITHUB_SHA=testhashH EXPECTED_SHA=testhashH \
    EXPECTED_MANIFEST_SHA=deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef \
    INCOMING_DIR="$H_IN" \
    bash "${SCRIPT_DIR}/verify-incoming-source.sh"; then
  fail "manifest SHA mismatch should fail"
fi
pass "MANIFEST_SHA_MISMATCH"

# --- tracked-tree copy excludes .github / untracked ---
I_REPO="$TMP/i-repo"
mkdir -p "$I_REPO"
git -C "$I_REPO" init -q
git -C "$I_REPO" config user.email test@example.com
git -C "$I_REPO" config user.name testhandoff
make_min_tree "$I_REPO"
mkdir -p "$I_REPO/.github/workflows"
echo 'workflow' > "$I_REPO/.github/workflows/x.yml"
echo 'tracked' > "$I_REPO/app/tracked.py"
echo 'untracked' > "$I_REPO/app/untracked.py"
git -C "$I_REPO" add app deploy frontend .github
git -C "$I_REPO" reset -q app/untracked.py
git -C "$I_REPO" commit -q -m 'fixture'
I_TREE="$TMP/i-tree"
karzar_copy_tracked_deploy_tree "$I_REPO" "$I_TREE"
[[ -f "$I_TREE/app/tracked.py" ]] || fail "copy: missing tracked file"
[[ ! -e "$I_TREE/app/untracked.py" ]] || fail "copy: included untracked file"
[[ ! -e "$I_TREE/.github/workflows/x.yml" ]] || fail "copy: included .github"
[[ -f "$I_TREE/frontend/Storefront/index.html" ]] || fail "copy: missing public-like file"
pass "TRACKED_TREE_COPY"


# --- J. remote seed helper payload must be self-contained under set -u ---
J_BE="$TMP/j-live-be"
J_FE="$TMP/j-live-fe"
J_IN="$TMP/j-in/tree"
make_min_tree "$J_BE"
mkdir -p "$J_FE/Storefront"
echo 'remote-seed' > "$J_FE/Storefront/asset.bin"
{
  declare -f karzar_backend_rsync_excludes
  declare -f karzar_frontend_rsync_excludes
  declare -f karzar_read_null_args
  declare -f karzar_prepare_incoming_dest
  declare -f karzar_seed_incoming_tree
  printf 'set -euo pipefail\n'
  printf 'KARZAR_PARTIAL_DIR=%q\n' "$KARZAR_PARTIAL_DIR"
  printf 'karzar_prepare_incoming_dest %q\n' "$TMP/j-in"
  printf 'karzar_seed_incoming_tree %q %q %q\n' "$J_BE" "$J_FE" "$J_IN"
} | env -i PATH="$PATH" bash -s
[[ -f "$J_IN/app/main.py" ]] || fail "remote-seed: backend file missing"
[[ -f "$J_IN/frontend/Storefront/asset.bin" ]] || fail "remote-seed: frontend file missing"
pass "REMOTE_SEED_CLEAN_SHELL"

echo "ALL_HANDOFF_SELFTESTS_OK count=${PASS}"
