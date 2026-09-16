#!/usr/bin/env bash
# Ops regression tests for prebuilt staging frontend image handoff.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WF="${ROOT}/.github/workflows/deploy-staging.yml"
PROD_WF="${ROOT}/.github/workflows/deploy-production.yml"
PREFLIGHT_WF="${ROOT}/.github/workflows/staging-frontend-image-preflight.yml"
FAIL=0

pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*" >&2; FAIL=1; }

# shellcheck source=frontend-image-lib.sh
source "${SCRIPT_DIR}/frontend-image-lib.sh"

SHA="$(printf '%040x' 99)"
SHOP_TAG="$(karzar_frontend_shop_image_tag "$SHA")"
ADMIN_TAG="$(karzar_frontend_admin_image_tag "$SHA")"

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

if ! grep -q 'staging-frontend-image-preflight.yml' "$PREFLIGHT_WF" 2>/dev/null || [[ ! -f "$PREFLIGHT_WF" ]]; then
  fail "staging frontend image preflight workflow missing"
else
  pass "PREFLIGHT_WORKFLOW_PRESENT"
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

if ! grep -q 'prepare-frontend-build-source.sh' "${SCRIPT_DIR}/build-staging-frontend-images.sh"; then
  fail "hosted build must prepare source before docker"
else
  pass "PREPARE_BEFORE_HOSTED_BUILD"
fi

if ! grep -q 'prepare-frontend-build-source.sh' "${SCRIPT_DIR}/deploy-frontend-build-local.sh"; then
  fail "local build must prepare source before docker"
else
  pass "PREPARE_BEFORE_LOCAL_BUILD"
fi

if grep -vE '^\s*#' "${SCRIPT_DIR}/deploy-frontend.sh" | grep -qE 'picsum|USE_MOCK|remotePatterns'; then
  fail "deploy-frontend.sh must not apply build-time source patches"
else
  pass "NO_RUNTIME_SOURCE_PATCHES"
fi

FRONTEND_ROOT="${ROOT}/frontend" bash "${SCRIPT_DIR}/prepare-frontend-build-source.sh" >/dev/null \
  && pass "PREPARE_SOURCE_VALIDATES_TREE" \
  || fail "prepare-frontend-build-source.sh failed on current tree"

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

if grep -q 'deploy-frontend-build-local.sh' "$PROD_WF"; then
  pass "PRODUCTION_USES_LOCAL_BUILD_SCRIPT"
else
  fail "production must call deploy-frontend-build-local.sh"
fi

if grep -q 'FRONTEND_IMAGES_HANDOFF_COMPLETE' "$PROD_WF" \
  || grep -q 'load-incoming-frontend-images' "$PROD_WF"; then
  fail "production must not require staging frontend image handoff"
else
  pass "PRODUCTION_NO_IMAGE_HANDOFF"
fi

if ! grep -q 'registry.npmmirror.com' "${SCRIPT_DIR}/deploy-frontend-build-local.sh"; then
  fail "local build must default NPM_REGISTRY to npmmirror"
else
  pass "PRODUCTION_LOCAL_NPMMIRROR_DEFAULT"
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
karzar_write_frontend_images_handoff_marker "$IN" "$SHA" "0000000000000000000000000000000000000000000000000000000000000000" "$SHOP_TAG" "$ADMIN_TAG"

if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted missing checksum"
else
  pass "REJECT_MISSING_CHECKSUM"
fi

echo '0000000000000000000000000000000000000000000000000000000000000000  frontend-images.tar' > "${IN}/${KARZAR_FRONTEND_CHECKSUM_NAME}"
if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted checksum mismatch with bundle"
else
  pass "REJECT_CHECKSUM_MISMATCH"
fi

BUNDLE_SHA="$(sha256sum "${IN}/${KARZAR_FRONTEND_BUNDLE_NAME}" | awk '{print $1}')"
echo "${BUNDLE_SHA}  ${KARZAR_FRONTEND_BUNDLE_NAME}" > "${IN}/${KARZAR_FRONTEND_CHECKSUM_NAME}"
karzar_write_frontend_images_handoff_marker "$IN" "$SHA" "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" "$SHOP_TAG" "$ADMIN_TAG"
if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted marker bundle_sha mismatch"
else
  pass "REJECT_MARKER_BUNDLE_SHA_MISMATCH"
fi

karzar_write_frontend_images_handoff_marker "$IN" "$SHA" "$BUNDLE_SHA" "$SHOP_TAG" "$ADMIN_TAG"
echo "not-a-hex  ${KARZAR_FRONTEND_BUNDLE_NAME}" > "${IN}/${KARZAR_FRONTEND_CHECKSUM_NAME}"
if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted malformed checksum digest"
else
  pass "REJECT_MALFORMED_CHECKSUM"
fi

echo "${BUNDLE_SHA}  wrong-filename.tar" > "${IN}/${KARZAR_FRONTEND_CHECKSUM_NAME}"
karzar_write_frontend_images_handoff_marker "$IN" "$SHA" "$BUNDLE_SHA" "$SHOP_TAG" "$ADMIN_TAG"
if GITHUB_SHA="$SHA" bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" 2>/dev/null; then
  fail "loader accepted wrong checksum filename"
else
  pass "REJECT_WRONG_CHECKSUM_FILENAME"
fi

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

if GITHUB_SHA="$SHA" KARZAR_FE_VERIFY_ONLY=1 bash "${SCRIPT_DIR}/load-incoming-frontend-images.sh" >/dev/null; then
  pass "VERIFY_ONLY_BUNDLE_INTEGRITY"
else
  fail "verify-only mode failed on valid bundle"
fi

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

echo "ALL_PREBUILT_FRONTEND_SELFTESTS_OK"
exit "$FAIL"
