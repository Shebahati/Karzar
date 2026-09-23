#!/usr/bin/env bash
# Self-hosted local package → /opt/karzar/incoming/<sha> (no GitHub SSH).
#
# Default DRY_RUN=1 skips docker/frontend image build and never touches live trees.
# Set KARZAR_PACKAGE_DRY_RUN=0 only when a later phase authorizes FE image build
# (still does not rsync live / compose up — that remains deploy job).
#
# Does not: docker compose up, alembic, live rsync, Wave ops.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-tree-lib.sh
source "${SCRIPT_DIR}/deploy-tree-lib.sh"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "refuse to run package-incoming-local.sh as root" >&2
  exit 1
fi

# Avoid find/cwd failures when invoked under sudo -u from an inaccessible directory (e.g. /root).
cd "${HOME:-/tmp}" || cd /tmp

: "${GITHUB_SHA:?GITHUB_SHA is required}"
if ! karzar_is_git_sha "$GITHUB_SHA"; then
  echo "GITHUB_SHA must be 40 lowercase hex" >&2
  exit 1
fi

KARZAR_ROOT="${KARZAR_ROOT:-/opt/karzar}"
MIRROR="${KARZAR_MIRROR:-${KARZAR_ROOT}/mirror/Karzar.git}"
WORKSPACE_ROOT="${KARZAR_WORKSPACE:-${KARZAR_ROOT}/workspace}"
INCOMING_BASE="${KARZAR_INCOMING_BASE:-${KARZAR_ROOT}/incoming}"
LOG_DIR="${KARZAR_DEPLOY_LOG_DIR:-${KARZAR_ROOT}/logs/deploy}"
DRY_RUN="${KARZAR_PACKAGE_DRY_RUN:-1}"
FORCE_REPACKAGE="${FORCE_REPACKAGE:-0}"
CLEANUP_AFTER="${KARZAR_PACKAGE_CLEANUP_AFTER:-0}"

WORKDIR="${WORKSPACE_ROOT}/deploy-${GITHUB_SHA}"
INCOMING="${INCOMING_BASE}/${GITHUB_SHA}"
STAGING="${WORKDIR}/package-tree"
LOG_FILE="${LOG_DIR}/package-${GITHUB_SHA}-$(date -u +%Y%m%dT%H%M%SZ).log"

mkdir -p "$WORKSPACE_ROOT" "$LOG_DIR" "$INCOMING_BASE"

exec > >(tee -a "$LOG_FILE") 2>&1
echo "PACKAGE_START sha=${GITHUB_SHA} dry_run=${DRY_RUN} log=${LOG_FILE}"

for path in "$INCOMING_BASE" "$WORKSPACE_ROOT" "$MIRROR"; do
  if [[ ! -d "$path" ]]; then
    echo "missing required dir: $path (run prepare-self-hosted-dirs + ensure-git-mirror)" >&2
    exit 1
  fi
  owner="$(stat -c '%U' "$path")"
  if [[ "$owner" == "root" && "$path" == "$INCOMING_BASE" ]]; then
    echo "incoming still root-owned; run prepare-self-hosted-dirs.sh as root first" >&2
    exit 1
  fi
done

if [[ -f "${INCOMING}/${KARZAR_HANDOFF_MARKER}" && "$FORCE_REPACKAGE" != "1" ]]; then
  echo "incoming/${GITHUB_SHA} already has HANDOFF_COMPLETE; set FORCE_REPACKAGE=1 to replace" >&2
  exit 1
fi

# Fresh workspace worktree from bare mirror
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
echo "Creating worktree at ${WORKDIR}"
git -C "$MIRROR" worktree prune || true
# Prefer worktree add; fall back to clone --shared if worktree busy
if ! git -C "$MIRROR" worktree add --detach "$WORKDIR" "$GITHUB_SHA" 2>/tmp/karzar-wt.err; then
  echo "worktree add failed; falling back to local clone --shared" >&2
  cat /tmp/karzar-wt.err >&2 || true
  rm -rf "$WORKDIR"
  git clone --shared "$MIRROR" "$WORKDIR"
  git -C "$WORKDIR" checkout --detach "$GITHUB_SHA"
fi

HEAD="$(git -C "$WORKDIR" rev-parse HEAD)"
if [[ "$HEAD" != "$GITHUB_SHA" ]]; then
  echo "HEAD ${HEAD} != GITHUB_SHA ${GITHUB_SHA}" >&2
  exit 1
fi
echo "CHECKOUT_OK sha=${HEAD}"

rm -rf "$STAGING"
karzar_copy_tracked_deploy_tree "$WORKDIR" "$STAGING"
# Ensure frontend sources from the same SHA are present under tree/frontend
# (tracked copy already includes frontend/ from monorepo).
test -d "$STAGING/frontend/Storefront"
test -d "$STAGING/frontend/admin-panel"

MANIFEST="${WORKDIR}/${KARZAR_MANIFEST_NAME}"
karzar_write_deploy_manifest "$STAGING" "$MANIFEST"
echo "MANIFEST_OK sha256=${KARZAR_MANIFEST_SHA} files=${KARZAR_FILE_COUNT} bytes=${KARZAR_TOTAL_BYTES}"

# Stage into incoming atomically-ish: build in .partial then move
PARTIAL="${INCOMING_BASE}/.partial-${GITHUB_SHA}"
rm -rf "$PARTIAL"
mkdir -p "$PARTIAL/tree"
rsync -a --delete "$STAGING"/ "$PARTIAL/tree"/
cp -f "$MANIFEST" "$PARTIAL/${KARZAR_MANIFEST_NAME}"

if [[ "$DRY_RUN" == "1" ]]; then
  mkdir -p "$PARTIAL/frontend-images"
  cat > "$PARTIAL/frontend-images/DRY_RUN_SKIPPED" <<EOF
frontend_images=skipped
reason=KARZAR_PACKAGE_DRY_RUN=1
sha=${GITHUB_SHA}
EOF
  echo "FRONTEND_IMAGES=SKIPPED (dry-run; no docker)"
else
  echo "FRONTEND image build not implemented in Phase 1 dry-run path" >&2
  echo "Set KARZAR_PACKAGE_DRY_RUN=1 for Phase 1/2" >&2
  exit 1
fi

EXPECTED_MANIFEST_SHA="$KARZAR_MANIFEST_SHA"
# Write marker with local-package transport
files="$(karzar_tree_file_count "$PARTIAL/tree")"
bytes="$(karzar_tree_total_bytes "$PARTIAL/tree")"
cat > "$PARTIAL/${KARZAR_HANDOFF_MARKER}" <<EOF
sha=${GITHUB_SHA}
transport=local-package
files=${files}
bytes=${bytes}
manifest=${EXPECTED_MANIFEST_SHA}
EOF

# Replace destination
rm -rf "$INCOMING"
mv "$PARTIAL" "$INCOMING"

# Ownership check (must not be root)
owner="$(stat -c '%U:%G' "$INCOMING")"
echo "INCOMING_OWNER=${owner}"
if [[ "$owner" == root:* || "$owner" == *:root ]]; then
  echo "incoming owned by root; refuse" >&2
  exit 1
fi

# Verify consume-compatible (transport local-package now allowed)
HANDOFF_VERIFY_MODE=consume \
  GITHUB_SHA="$GITHUB_SHA" \
  EXPECTED_SHA="$GITHUB_SHA" \
  INCOMING_DIR="$INCOMING" \
  bash "${SCRIPT_DIR}/verify-incoming-source.sh"

echo "PACKAGE_OK sha=${GITHUB_SHA} incoming=${INCOMING} dry_run=${DRY_RUN}"

if [[ "$CLEANUP_AFTER" == "1" ]]; then
  echo "CLEANUP_AFTER=1 removing incoming and workspace"
  # Do not source cleanup-incoming-source.sh (it executes on source).
  env -u SSH_HOST \
    GITHUB_SHA="$GITHUB_SHA" \
    KARZAR_INCOMING_BASE="$INCOMING_BASE" \
    bash "${SCRIPT_DIR}/cleanup-incoming-source.sh"
  git -C "$MIRROR" worktree remove --force "$WORKDIR" 2>/dev/null || rm -rf "$WORKDIR"
  echo "CLEANUP_SIM_OK"
fi

echo "PACKAGE_DONE"
