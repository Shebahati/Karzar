#!/usr/bin/env bash
# Ops regression tests for prebuilt staging frontend image handoff.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WF="${ROOT}/.github/workflows/deploy-staging.yml"
PROD_WF="${ROOT}/.github/workflows/deploy-production.yml"
FAIL=0

pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*" >&2; FAIL=1; }

# shellcheck source=frontend-image-lib.sh
source "${SCRIPT_DIR}/frontend-image-lib.sh"

SHA="$(printf '%040x' 99)"
SHOP_TAG="$(karzar_frontend_shop_image_tag "$SHA")"
ADMIN_TAG="$(karzar_frontend_admin_image_tag "$SHA")"

if grep -q 'deploy-frontend-build-local' "$WF" 2>/dev/null; then
  : # production may reference build-local separately
fi

if sed -n '/name: Sync + rebuild staging/,/^  cleanup:/p' "$WF" | grep -qE 'docker build|npm (install|ci)|build-staging-frontend'; then
  fail "self-hosted deploy job must not build frontends or invoke npm on VPS"
else
  pass "NO_VPS_FRONTEND_BUILD"
fi

if ! grep -q 'build-staging-frontend-images.sh' "$WF"; then
  fail "workflow must build frontend images on GitHub-hosted runner"
else
  pass "GITHUB_HOSTED_FRONTEND_BUILD"
fi

if ! grep -q 'push-incoming-frontend-images.sh' "$WF"; then
  fail "workflow must push frontend image handoff"
else
  pass "FRONTEND_IMAGE_HANDOFF_REQUIRED"
fi

if ! grep -q 'load-incoming-frontend-images.sh' "$WF"; then
  fail "workflow must load frontend images on VPS"
else
  pass "VPS_LOAD_FRONTEND_IMAGES"
fi

if ! grep -q 'KARZAR_REQUIRE_PREBUILT_FRONTEND_IMAGES' "$WF"; then
  fail "workflow must require prebuilt frontend images on staging deploy"
else
  pass "REQUIRE_PREBUILT"
fi

if grep -q 'registry.npmmirror.com' "${ROOT}/deploy/staging/frontend/Dockerfile.storefront" \
  || grep -q 'registry.npmmirror.com' "${ROOT}/deploy/staging/frontend/Dockerfile.admin"; then
  fail "Dockerfiles must not hardcode npmmirror"
else
  pass "NO_HARDcoded_NPMMIRROR"
fi

if ! grep -q 'npm ci' "${ROOT}/deploy/staging/frontend/Dockerfile.storefront"; then
  fail "Storefront Dockerfile must use npm ci"
else
  pass "STOREFRONT_NPM_CI"
fi

if ! grep -q 'npm ci' "${ROOT}/deploy/staging/frontend/Dockerfile.admin"; then
  fail "Admin Dockerfile must use npm ci"
else
  pass "ADMIN_NPM_CI"
fi

if ! grep -q 'wait-staging-frontends' "$WF" && ! grep -q 'wait-staging-frontends' "${SCRIPT_DIR}/deploy-frontend.sh"; then
  fail "readiness gate missing"
else
  pass "READINESS_BEFORE_SMOKE_PATH"
fi

if ! grep -q 'run-smoke-staging.sh' "$WF"; then
  fail "smoke orchestration missing"
else
  pass "SMOKE_ORCHESTRATION"
fi

if grep -q 'DEPLOY_FE_SMOKE_OK' "${SCRIPT_DIR}/smoke-staging.sh" \
  || grep -q 'DEPLOY_FE_SMOKE_OK' "${SCRIPT_DIR}/run-smoke-staging.sh"; then
  pass "DEPLOY_FE_SMOKE_OK_SEMANTICS"
else
  fail "DEPLOY_FE_SMOKE_OK not found in smoke scripts"
fi

# --- loader fail-closed (mocked docker) ---
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
IN="${TMP}/incoming/${SHA}/${KARZAR_FRONTEND_IMAGES_SUBDIR}"
mkdir -p "$IN"
export GITHUB_SHA="$SHA" EXPECTED_SHA="$SHA" KARZAR_INCOMING_BASE="${TMP}/incoming"

if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted missing marker"
else
  pass "REJECT_MISSING_MARKER"
fi

echo 'deadbeef' > "${IN}/${KARZAR_FRONTEND_BUNDLE_NAME}"
echo '0000000000000000000000000000000000000000000000000000000000000000  frontend-images.tar' > "${IN}/${KARZAR_FRONTEND_CHECKSUM_NAME}"
karzar_write_frontend_images_handoff_marker "$IN" "$SHA" "0000000000000000000000000000000000000000000000000000000000000000" "$SHOP_TAG" "$ADMIN_TAG"

if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted checksum mismatch"
else
  pass "REJECT_CHECKSUM_MISMATCH"
fi

BUNDLE_SHA="$(sha256sum "${IN}/${KARZAR_FRONTEND_BUNDLE_NAME}" | awk '{print $1}')"
karzar_write_frontend_images_handoff_marker "$IN" "$SHA" "$BUNDLE_SHA" "$SHOP_TAG" "$ADMIN_TAG"
echo "${BUNDLE_SHA}  ${KARZAR_FRONTEND_BUNDLE_NAME}" > "${IN}/${KARZAR_FRONTEND_CHECKSUM_NAME}"
export KARZAR_SKIP_DOCKER_LOAD=1 KARZAR_SKIP_DOCKER_TAG=1
export KARZAR_MOCK_REVISION_MAP="karzar-shop:sha-${SHA}=wrong00000000000000000000000000000000000000
karzar-admin:sha-${SHA}=${SHA}"
if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted wrong shop revision"
else
  pass "REJECT_WRONG_REVISION"
fi

export KARZAR_MOCK_REVISION_MAP="karzar-shop:sha-${SHA}=${SHA}
karzar-admin:sha-${SHA}=wrong00000000000000000000000000000000000000"
if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted wrong admin revision"
else
  pass "REJECT_WRONG_ADMIN_REVISION"
fi

export KARZAR_MOCK_REVISION_MAP="karzar-shop:sha-${SHA}=${SHA}
karzar-admin:sha-${SHA}=${SHA}"
if ! GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" >/dev/null; then
  fail "loader rejected valid revisions"
else
  pass "ACCEPT_BOTH_REVISIONS"
fi

# deploy-frontend must not contain docker build in canonical script
if grep -vE '^\s*#' "${SCRIPT_DIR}/deploy-frontend.sh" | grep -qE 'docker build'; then
  fail "deploy-frontend.sh must not docker build"
else
  pass "DEPLOY_FRONTEND_NO_BUILD"
fi

if ! grep -qE 'docker build' "${SCRIPT_DIR}/deploy-frontend-build-local.sh"; then
  fail "deploy-frontend-build-local.sh must retain VPS build path"
else
  pass "LOCAL_BUILD_SCRIPT"
fi

# Production workflow still uses build-local path (shared Dockerfiles only)
if grep -q 'deploy-frontend-build-local.sh' "$PROD_WF"; then
  pass "PRODUCTION_USES_LOCAL_BUILD_SCRIPT"
elif grep -q 'deploy-frontend.sh' "$PROD_WF" && ! grep -q 'KARZAR_REQUIRE_PREBUILT' "$PROD_WF"; then
  fail "production must call deploy-frontend-build-local.sh after deploy-frontend refactor"
else
  pass "PRODUCTION_WORKFLOW_UNCHANGED"
fi

echo "ALL_PREBUILT_FRONTEND_SELFTESTS_OK"
exit "$FAIL"
