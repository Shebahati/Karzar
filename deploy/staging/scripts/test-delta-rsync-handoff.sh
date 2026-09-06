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

hex40() {
  printf '%040x' "$1"
}

# Self-hosted consume path: no EXPECTED_MANIFEST_SHA, no GITHUB_OUTPUT.
consume_verify() {
  local incoming="$1" sha="$2"
  env -u EXPECTED_MANIFEST_SHA -u GITHUB_OUTPUT \
    HANDOFF_VERIFY_MODE=consume \
    GITHUB_SHA="$sha" EXPECTED_SHA="$sha" \
    INCOMING_DIR="$incoming" \
    STAGED_DIR="${incoming}/tree" \
    bash "${SCRIPT_DIR}/verify-incoming-source.sh"
}

sync_live_after_verify() {
  local incoming="$1" live="$2" sha="$3"
  if ! consume_verify "$incoming" "$sha"; then
    echo "SYNC_TO_LIVE=SKIPPED"
    return 1
  fi
  mkdir -p "$live"
  rsync -a --delete "${incoming}/tree"/ "$live"/
}

write_marker() {
  local incoming="$1" sha="$2" manifest_sha="$3"
  local extra="${4:-}"
  local files bytes
  files="$(karzar_tree_file_count "$incoming/tree")"
  bytes="$(karzar_tree_total_bytes "$incoming/tree")"
  cat > "$incoming/${KARZAR_HANDOFF_MARKER}" <<EOF
sha=${sha}
transport=rsync-delta
files=${files}
bytes=${bytes}
manifest=${manifest_sha}
${extra}
EOF
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
karzar_write_handoff_complete "$TMP/a-in" "$(hex40 10)" "$KARZAR_MANIFEST_SHA"
consume_verify "$TMP/a-in" "$(hex40 10)" >/dev/null
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
karzar_write_handoff_complete "$TMP/b-in" "$(hex40 11)" "$KARZAR_MANIFEST_SHA"
consume_verify "$TMP/b-in" "$(hex40 11)" >/dev/null
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
karzar_write_handoff_complete "$TMP/c-in" "$(hex40 12)" "$KARZAR_MANIFEST_SHA"
consume_verify "$TMP/c-in" "$(hex40 12)" >/dev/null
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
karzar_write_handoff_complete "$TMP/d-in" "$(hex40 13)" "$KARZAR_MANIFEST_SHA"
consume_verify "$TMP/d-in" "$(hex40 13)" >/dev/null
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
E_OUT="$(set +e; sync_live_after_verify "$E_INCOMING" "$E_LIVE" "$(hex40 14)" 2>&1; echo EXIT:$?)"
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
karzar_write_handoff_complete "$F_INCOMING" "$(hex40 15)" "$KARZAR_MANIFEST_SHA"
echo 'tampered' > "$F_INCOMING/tree/app/main.py"
echo 'live-original' > "$F_LIVE/keep.txt"
F_LIVE_HASH="$(sha256sum "$F_LIVE/keep.txt")"
F_OUT="$(set +e; sync_live_after_verify "$F_INCOMING" "$F_LIVE" "$(hex40 15)" 2>&1; echo EXIT:$?)"
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
write_marker "$H_IN" "$(hex40 16)" "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
if consume_verify "$H_IN" "$(hex40 16)"; then
  fail "marker manifest vs file hash mismatch should fail"
fi
pass "MANIFEST_MISMATCH"

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

make_completed_incoming() {
  local incoming="$1" sha="$2"
  mkdir -p "$incoming/tree"
  make_min_tree "$incoming/tree"
  karzar_write_deploy_manifest "$incoming/tree" "$incoming/${KARZAR_MANIFEST_NAME}"
  karzar_write_handoff_complete "$incoming" "$sha" "$KARZAR_MANIFEST_SHA"
}

# --- incident: local marker is authority; no cross-job output ---
K_SHA="$(hex40 21)"
K_IN="$TMP/k-in"
make_completed_incoming "$K_IN" "$K_SHA"
consume_verify "$K_IN" "$K_SHA" >/dev/null
pass "VALID_HANDOFF"

L_SHA="$(hex40 22)"
L_IN="$TMP/l-in"
make_completed_incoming "$L_IN" "$L_SHA"
# Critical regression: consume succeeds with EXPECTED_MANIFEST_SHA unset.
if ! env -u EXPECTED_MANIFEST_SHA -u GITHUB_OUTPUT \
    HANDOFF_VERIFY_MODE=consume \
    GITHUB_SHA="$L_SHA" EXPECTED_SHA="$L_SHA" \
    INCOMING_DIR="$L_IN" \
    bash "${SCRIPT_DIR}/verify-incoming-source.sh" >/dev/null; then
  fail "NO_JOB_OUTPUT: consume verify required EXPECTED_MANIFEST_SHA"
fi
pass "NO_JOB_OUTPUT"

M_SHA="$(hex40 23)"
M_IN="$TMP/m-in"
make_completed_incoming "$M_IN" "$M_SHA"
write_marker "$M_IN" "$M_SHA" ""
if consume_verify "$M_IN" "$M_SHA"; then
  fail "empty marker manifest should fail"
fi
pass "EMPTY_MANIFEST"

N_SHA="$(hex40 24)"
N_IN="$TMP/n-in"
make_completed_incoming "$N_IN" "$N_SHA"
malformed_ok=1
for bad in abc ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ \
           aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
           aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; do
  write_marker "$N_IN" "$N_SHA" "$bad"
  if consume_verify "$N_IN" "$N_SHA"; then
    echo "malformed manifest accepted: $bad" >&2
    malformed_ok=0
  fi
done
[[ "$malformed_ok" -eq 1 ]] || fail "MALFORMED_MANIFEST"
pass "MALFORMED_MANIFEST"

# MANIFEST_MISMATCH already covered above
pass "MANIFEST_MISMATCH_NAMED"

# corrupted tree: already CORRUPTION_TEST
pass "CORRUPTED_TREE"

O_SHA="$(hex40 25)"
O_WRONG="$(hex40 26)"
O_IN="$TMP/o-in"
make_completed_incoming "$O_IN" "$O_SHA"
if consume_verify "$O_IN" "$O_WRONG"; then
  fail "wrong marker SHA should fail"
fi
pass "WRONG_SHA"

P_SHA="$(hex40 27)"
P_IN="$TMP/p-in"
make_completed_incoming "$P_IN" "$P_SHA"
{
  echo "sha=${P_SHA}"
  echo "transport=scp-tarball"
  echo "files=1"
  echo "bytes=1"
  echo "manifest=${KARZAR_MANIFEST_SHA}"
} > "$P_IN/${KARZAR_HANDOFF_MARKER}"
if consume_verify "$P_IN" "$P_SHA"; then
  fail "wrong transport should fail"
fi
pass "WRONG_TRANSPORT"

Q_SHA="$(hex40 28)"
Q_IN="$TMP/q-in"
make_completed_incoming "$Q_IN" "$Q_SHA"
rm -f "$Q_IN/${KARZAR_HANDOFF_MARKER}"
if consume_verify "$Q_IN" "$Q_SHA"; then
  fail "missing marker should fail"
fi
pass "MISSING_MARKER"

# FAILED_TRANSFER_TEST already proves no live mutation
pass "NO_LIVE_MUTATION"

R_SHA="$(hex40 29)"
R_IN="$TMP/r-in"
make_completed_incoming "$R_IN" "$R_SHA"
# Architectural: marker data is local; GITHUB_OUTPUT is unused even if present.
if ! env -u EXPECTED_MANIFEST_SHA \
    GITHUB_OUTPUT="$TMP/r-github-output" \
    HANDOFF_VERIFY_MODE=consume \
    GITHUB_SHA="$R_SHA" EXPECTED_SHA="$R_SHA" \
    INCOMING_DIR="$R_IN" \
    bash "${SCRIPT_DIR}/verify-incoming-source.sh" >/dev/null; then
  fail "secret-like path: consume verify failed without job output"
fi
if [[ -e "$TMP/r-github-output" ]]; then
  fail "consume verify wrote GITHUB_OUTPUT"
fi
pass "SECRET_LIKE_NO_JOB_OUTPUT"

WF="$(cd "${SCRIPT_DIR}/../../.." && pwd)/.github/workflows/deploy-staging.yml"
if grep -q 'needs.package.outputs.manifest_sha' "$WF"; then
  fail "workflow still references needs.package.outputs.manifest_sha"
fi
if grep -q 'steps.push.outputs.manifest_sha' "$WF"; then
  fail "workflow still references steps.push.outputs.manifest_sha"
fi
if grep -qE '^[[:space:]]+outputs:' "$WF"; then
  fail "package job still declares cross-job outputs"
fi
pass "WORKFLOW_NO_CROSS_JOB_MANIFEST"

# Marker files/bytes must match the staged tree, not only be numeric.
S_SHA="$(hex40 30)"
S_IN="$TMP/s-in"
make_completed_incoming "$S_IN" "$S_SHA"
S_MANIFEST="$(awk -F= '/^manifest=/{print $2; exit}' "$S_IN/HANDOFF_COMPLETE")"
S_FILES="$(karzar_tree_file_count "$S_IN/tree")"
S_BYTES="$(karzar_tree_total_bytes "$S_IN/tree")"
{
  echo "sha=${S_SHA}"
  echo "transport=rsync-delta"
  echo "files=$((S_FILES + 1))"
  echo "bytes=${S_BYTES}"
  echo "manifest=${S_MANIFEST}"
} > "$S_IN/HANDOFF_COMPLETE"
if consume_verify "$S_IN" "$S_SHA"; then
  fail "marker files mismatch should fail"
fi
pass "MARKER_FILES_MISMATCH"

T_SHA="$(hex40 31)"
T_IN="$TMP/t-in"
make_completed_incoming "$T_IN" "$T_SHA"
T_MANIFEST="$(awk -F= '/^manifest=/{print $2; exit}' "$T_IN/HANDOFF_COMPLETE")"
T_FILES="$(karzar_tree_file_count "$T_IN/tree")"
T_BYTES="$(karzar_tree_total_bytes "$T_IN/tree")"
{
  echo "sha=${T_SHA}"
  echo "transport=rsync-delta"
  echo "files=${T_FILES}"
  echo "bytes=$((T_BYTES + 1))"
  echo "manifest=${T_MANIFEST}"
} > "$T_IN/HANDOFF_COMPLETE"
if consume_verify "$T_IN" "$T_SHA"; then
  fail "marker bytes mismatch should fail"
fi
pass "MARKER_BYTES_MISMATCH"

file_mode() {
  stat -c '%a' "$1"
}

has_other_write() {
  find -P "$1" \( -type f -o -type d \) -perm -0002 -print
}

# --- incoming readability / permission normalization ---
U_SHA="$(hex40 40)"
U_IN="$TMP/u-in"
make_completed_incoming "$U_IN" "$U_SHA"
chmod 0755 "$U_IN"
chmod 0644 "$U_IN/${KARZAR_MANIFEST_NAME}" "$U_IN/${KARZAR_HANDOFF_MARKER}"
chmod -R a+rX "$U_IN/tree"
consume_verify "$U_IN" "$U_SHA" >/dev/null
pass "READABLE_HANDOFF"

V_SHA="$(hex40 41)"
V_IN="$TMP/v-in"
make_completed_incoming "$V_IN" "$V_SHA"
chmod 0755 "$V_IN/tree/deploy/staging/scripts/deploy-frontend.sh"
chmod 0600 "$V_IN/${KARZAR_MANIFEST_NAME}" "$V_IN/${KARZAR_HANDOFF_MARKER}"
chmod 0700 "$V_IN" "$V_IN/tree"
find -P "$V_IN/tree" -type d -exec chmod 0700 {} +
find -P "$V_IN/tree" -type f -exec chmod 0600 {} +
chmod 0755 "$V_IN/tree/deploy/staging/scripts/deploy-frontend.sh"
[[ "$(file_mode "$V_IN/${KARZAR_MANIFEST_NAME}")" == "600" ]] \
  || fail "restrictive fixture: expected manifest 600"
karzar_normalize_incoming_permissions "$V_IN"
[[ "$(file_mode "$V_IN")" == "755" ]] || fail "normalize: incoming dir not 755"
[[ "$(file_mode "$V_IN/${KARZAR_MANIFEST_NAME}")" == "644" ]] \
  || fail "normalize: manifest not 644"
[[ "$(file_mode "$V_IN/${KARZAR_HANDOFF_MARKER}")" == "644" ]] \
  || fail "normalize: marker not 644"
[[ "$(file_mode "$V_IN/tree/app/main.py")" == "644" ]] \
  || fail "normalize: tree file not readable"
[[ "$(file_mode "$V_IN/tree/deploy/staging/scripts/deploy-frontend.sh")" == "755" ]] \
  || fail "normalize: executable bit stripped"
if [[ -n "$(has_other_write "$V_IN")" ]]; then
  fail "normalize: world-writable path created"
fi
consume_verify "$V_IN" "$V_SHA" >/dev/null
pass "RESTRICTIVE_MANIFEST_NORMALIZED"
pass "EXEC_BIT_PRESERVED"
pass "NO_WORLD_WRITE"

W_LIVE_BE="$TMP/w-live-be"
W_LIVE_FE="$TMP/w-live-fe"
W_SECRETS="$TMP/w-secrets"
W_IN="$TMP/w-in"
W_SHA="$(hex40 42)"
make_min_tree "$W_LIVE_BE"
mkdir -p "$W_LIVE_FE/Storefront" "$W_SECRETS"
echo 'be-secret' > "$W_LIVE_BE/.env"
echo 'fe-keep' > "$W_LIVE_FE/Storefront/keep.bin"
echo 'deploy-secret' > "$W_SECRETS/.deploy-secrets"
chmod 0600 "$W_LIVE_BE/.env" "$W_SECRETS/.deploy-secrets"
chmod 0700 "$W_SECRETS"
W_BE_MODE="$(file_mode "$W_LIVE_BE/.env")"
W_SEC_MODE="$(file_mode "$W_SECRETS/.deploy-secrets")"
W_SEC_DIR="$(file_mode "$W_SECRETS")"
W_BE_HASH="$(sha256sum "$W_LIVE_BE/.env" "$W_LIVE_BE/app/main.py")"
W_FE_HASH="$(sha256sum "$W_LIVE_FE/Storefront/keep.bin")"
W_SEC_HASH="$(sha256sum "$W_SECRETS/.deploy-secrets")"
make_completed_incoming "$W_IN" "$W_SHA"
chmod 0600 "$W_IN/${KARZAR_MANIFEST_NAME}"
karzar_normalize_incoming_permissions "$W_IN"
[[ "$(file_mode "$W_LIVE_BE/.env")" == "$W_BE_MODE" ]] || fail "outside: backend .env mode changed"
[[ "$(file_mode "$W_SECRETS/.deploy-secrets")" == "$W_SEC_MODE" ]] || fail "outside: secrets mode changed"
[[ "$(file_mode "$W_SECRETS")" == "$W_SEC_DIR" ]] || fail "outside: secrets dir mode changed"
[[ "$(sha256sum "$W_LIVE_BE/.env" "$W_LIVE_BE/app/main.py")" == "$W_BE_HASH" ]] \
  || fail "outside: backend content changed"
[[ "$(sha256sum "$W_LIVE_FE/Storefront/keep.bin")" == "$W_FE_HASH" ]] \
  || fail "outside: frontend content changed"
[[ "$(sha256sum "$W_SECRETS/.deploy-secrets")" == "$W_SEC_HASH" ]] \
  || fail "outside: secrets content changed"
pass "OUTSIDE_TREE_UNCHANGED"

X_SHA="$(hex40 43)"
X_IN="$TMP/x-in"
make_completed_incoming "$X_IN" "$X_SHA"
chmod 0600 "$X_IN/${KARZAR_MANIFEST_NAME}" "$X_IN/${KARZAR_HANDOFF_MARKER}"
karzar_normalize_incoming_permissions "$X_IN"
consume_verify "$X_IN" "$X_SHA" >/dev/null
pass "VERIFY_AFTER_NORMALIZATION"

Y_SHA="$(hex40 44)"
Y_IN="$TMP/y-in"
make_completed_incoming "$Y_IN" "$Y_SHA"
karzar_normalize_incoming_permissions "$Y_IN"
echo 'tampered-after-normalize' > "$Y_IN/tree/app/main.py"
if consume_verify "$Y_IN" "$Y_SHA"; then
  fail "corruption after normalize should fail"
fi
pass "CORRUPTION_STILL_FAILS"

# Remote payload must set the same vars as push-incoming-source.sh
Z_SHA="$(hex40 45)"
Z_IN="$TMP/z-in"
make_completed_incoming "$Z_IN" "$Z_SHA"
chmod 0600 "$Z_IN/${KARZAR_MANIFEST_NAME}"
{
  declare -f karzar_normalize_incoming_permissions
  printf 'set -euo pipefail\n'
  printf 'KARZAR_MANIFEST_NAME=%q\n' "$KARZAR_MANIFEST_NAME"
  printf 'KARZAR_HANDOFF_MARKER=%q\n' "$KARZAR_HANDOFF_MARKER"
  printf 'karzar_normalize_incoming_permissions %q\n' "$Z_IN"
} | env -i PATH="$PATH" bash -s
[[ "$(file_mode "$Z_IN/${KARZAR_MANIFEST_NAME}")" == "644" ]] \
  || fail "clean-shell normalize: manifest not 644"
pass "NORMALIZE_CLEAN_SHELL"

echo "ALL_HANDOFF_SELFTESTS_OK count=${PASS}"
