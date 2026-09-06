#!/usr/bin/env bash
# Shared deploy-tree helpers for the GitHub-hosted → incoming delta rsync handoff.
# Sourced by push/verify/selftest. Safe to execute: $0 rsync-delta <src> <dest>
# Does not log secrets. Does not write live /opt/karzar/{Karzar,frontend}.

if [[ -n "${KARZAR_DEPLOY_TREE_LIB_LOADED:-}" ]]; then
  return 0 2>/dev/null || exit 0
fi
KARZAR_DEPLOY_TREE_LIB_LOADED=1

KARZAR_MANIFEST_NAME="${KARZAR_MANIFEST_NAME:-deploy-manifest.sha256}"
KARZAR_HANDOFF_MARKER="${KARZAR_HANDOFF_MARKER:-HANDOFF_COMPLETE}"
KARZAR_PARTIAL_DIR="${KARZAR_PARTIAL_DIR:-.rsync-partial}"
KARZAR_RSYNC_IO_TIMEOUT="${KARZAR_RSYNC_IO_TIMEOUT:-60}"

# Excludes for seeding /opt/karzar/Karzar → incoming/<sha>/tree/
# Must stay aligned with the live backend rsync in deploy-staging.yml.
karzar_backend_rsync_excludes() {
  printf '%s\0' \
    --exclude=.git/ \
    --exclude=.github/ \
    --exclude=frontend/ \
    --exclude=.venv/ \
    --exclude=venv/ \
    --exclude=__pycache__/ \
    --exclude=.pytest_cache/ \
    --exclude=.env \
    --exclude=.deploy-secrets \
    --exclude=.env.staging.generated \
    --exclude=backups/ \
    --exclude=data/uploads/ \
    --exclude=logs/ \
    --exclude='*.pyc' \
    --exclude=.mypy_cache/ \
    --exclude=.ruff_cache/ \
    --exclude=.coverage \
    --exclude=actions-runner/ \
    --exclude="${KARZAR_PARTIAL_DIR}/"
}

# Excludes for seeding /opt/karzar/frontend → incoming/<sha>/tree/frontend/
# Must stay aligned with the live frontend rsync in deploy-staging.yml.
karzar_frontend_rsync_excludes() {
  printf '%s\0' \
    --exclude=node_modules/ \
    --exclude=.next/ \
    --exclude=out/ \
    --exclude=.git/ \
    --exclude=.env \
    --exclude='.env*.local' \
    --exclude="${KARZAR_PARTIAL_DIR}/"
}

karzar_read_null_args() {
  local -n _karzar_out=$1
  _karzar_out=()
  local item
  while IFS= read -r -d '' item; do
    _karzar_out+=("$item")
  done
}

karzar_tracked_path_allowed() {
  local p="$1"
  case "$p" in
    .github|.github/*) return 1 ;;
    .env|.deploy-secrets|.env.staging.generated) return 1 ;;
    */.env|*/.deploy-secrets|*/.env.staging.generated) return 1 ;;
    .coverage|*/.coverage) return 1 ;;
    data/uploads|data/uploads/*) return 1 ;;
  esac
  if [[ "$p" =~ (^|/)(node_modules|\.next|out|\.venv|venv|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|backups|logs|actions-runner)(/|$) ]]; then
    return 1
  fi
  return 0
}

# Copy tracked files from a git checkout into an isolated deploy tree.
# Does not mutate src. Excludes .github and runtime/cache paths.
karzar_copy_tracked_deploy_tree() {
  local src="$1" dest="$2"
  test -d "$src/.git" || test -f "$src/.git"
  mkdir -p "$dest"
  local list
  list="$(mktemp)"
  local f
  while IFS= read -r -d '' f; do
    if karzar_tracked_path_allowed "$f"; then
      printf '%s\0' "$f"
    fi
  done < <(git -C "$src" ls-files -z) > "$list"
  rsync -a --files-from="$list" --from0 "$src"/ "$dest"/
  rm -f "$list"
}

karzar_tree_find_files() {
  local tree="$1"
  (
    cd "$tree"
    find . -type f ! -path "./${KARZAR_PARTIAL_DIR}/*" -printf '%P\n' | LC_ALL=C sort
  )
}

karzar_tree_file_count() {
  local tree="$1"
  find "$tree" -type f ! -path "*/${KARZAR_PARTIAL_DIR}/*" | wc -l | tr -d ' '
}

karzar_tree_total_bytes() {
  local tree="$1"
  find "$tree" -type f ! -path "*/${KARZAR_PARTIAL_DIR}/*" -printf '%s\n' | awk '{s+=$1} END {print s+0}'
}

# Write SHA256  relative/path for every regular file. Deterministic order.
# Sets KARZAR_FILE_COUNT, KARZAR_TOTAL_BYTES, KARZAR_MANIFEST_SHA.
karzar_write_deploy_manifest() {
  local tree="$1" manifest="$2"
  test -d "$tree"
  mkdir -p "$(dirname "$manifest")"
  (
    cd "$tree"
    find . -type f ! -path "./${KARZAR_PARTIAL_DIR}/*" -printf '%P\0' \
      | LC_ALL=C sort -z \
      | xargs -0 -r sha256sum
  ) > "$manifest"
  KARZAR_FILE_COUNT="$(karzar_tree_file_count "$tree")"
  KARZAR_TOTAL_BYTES="$(karzar_tree_total_bytes "$tree")"
  KARZAR_MANIFEST_SHA="$(sha256sum "$manifest" | awk '{print $1}')"
}

karzar_manifest_paths() {
  local manifest="$1"
  # sha256sum text mode: "<64 hex><two spaces><path>"
  sed -n 's/^[0-9a-f]\{64\}  //p' "$manifest" | LC_ALL=C sort
}

# Seed a non-live incoming tree from current live source. Never writes the live dirs.
karzar_seed_incoming_tree() {
  local backend_live="$1" frontend_live="$2" dest_tree="$3"
  mkdir -p "$dest_tree"
  local -a ex=()
  if [[ -d "$backend_live" ]]; then
    karzar_read_null_args ex < <(karzar_backend_rsync_excludes)
    rsync -a --delete "${ex[@]}" "$backend_live"/ "$dest_tree"/
  fi
  if [[ -d "$frontend_live" ]]; then
    mkdir -p "$dest_tree/frontend"
    karzar_read_null_args ex < <(karzar_frontend_rsync_excludes)
    rsync -a --delete "${ex[@]}" "$frontend_live"/ "$dest_tree/frontend/"
  fi
}

karzar_prepare_incoming_dest() {
  local dest="$1"
  rm -rf "$dest"
  mkdir -p "$dest/tree"
}

karzar_rsync_delta_flags() {
  printf '%s\0' \
    -a \
    -4 \
    --delete \
    --checksum \
    --partial \
    --partial-dir="${KARZAR_PARTIAL_DIR}" \
    --timeout="${KARZAR_RSYNC_IO_TIMEOUT}" \
    --info=stats2 \
    --no-owner \
    --no-group \
    --exclude="${KARZAR_PARTIAL_DIR}/"
}

# Exact source sync. Dest may be local or user@host:path when KARZAR_RSYNC_RSH is set.
karzar_rsync_delta() {
  local src="$1" dest="$2"
  test -d "$src"
  local -a flags=()
  karzar_read_null_args flags < <(karzar_rsync_delta_flags)
  local -a cmd=(rsync "${flags[@]}")
  if [[ -n "${KARZAR_RSYNC_RSH:-}" ]]; then
    cmd+=(-e "$KARZAR_RSYNC_RSH")
  fi
  cmd+=("$src"/ "$dest"/)
  "${cmd[@]}"
}

karzar_cleanup_partial() {
  local tree="$1"
  rm -rf "${tree}/${KARZAR_PARTIAL_DIR}"
}

karzar_assert_structural_files() {
  local tree="$1"
  test -f "$tree/deploy/staging/scripts/deploy-frontend.sh"
  test -f "$tree/deploy/staging/scripts/deploy-backend.sh"
  test -d "$tree/frontend/Storefront"
  test -d "$tree/frontend/admin-panel"
  test -d "$tree/app"
}

karzar_write_handoff_complete() {
  local incoming="$1" sha="$2" manifest_sha="$3"
  local tree="$incoming/tree"
  local count bytes
  count="$(karzar_tree_file_count "$tree")"
  bytes="$(karzar_tree_total_bytes "$tree")"
  umask 022
  cat > "$incoming/${KARZAR_HANDOFF_MARKER}" <<EOF
sha=${sha}
transport=rsync-delta
files=${count}
bytes=${bytes}
manifest=${manifest_sha}
EOF
}

karzar_require_handoff_complete() {
  local incoming="$1" expected_sha="$2"
  local marker="$incoming/${KARZAR_HANDOFF_MARKER}"
  if [[ ! -f "$marker" ]]; then
    echo "HANDOFF_COMPLETE absent — transfer incomplete; live sync skipped" >&2
    return 1
  fi
  local marked
  marked="$(awk -F= '/^sha=/{print $2; exit}' "$marker")"
  if [[ "$marked" != "$expected_sha" ]]; then
    echo "HANDOFF_COMPLETE sha=${marked} does not match EXPECTED_SHA=${expected_sha}" >&2
    return 1
  fi
}

# Verify incoming/<sha> against the GitHub-generated manifest. No live writes.
karzar_verify_incoming_tree() {
  local incoming="$1" expected_sha="$2" expected_manifest_sha="$3"
  local tree="$incoming/tree"
  local manifest="$incoming/${KARZAR_MANIFEST_NAME}"

  test -d "$incoming"
  test -d "$tree"
  test -f "$manifest"

  local actual_manifest_sha
  actual_manifest_sha="$(sha256sum "$manifest" | awk '{print $1}')"
  echo "EXPECTED_MANIFEST_SHA=${expected_manifest_sha}"
  echo "ACTUAL_MANIFEST_SHA=${actual_manifest_sha}"
  if [[ "$actual_manifest_sha" != "$expected_manifest_sha" ]]; then
    echo "VERIFY=FAIL manifest SHA mismatch" >&2
    return 1
  fi

  karzar_cleanup_partial "$tree"

  if ! (cd "$tree" && sha256sum -c --quiet "$manifest"); then
    echo "VERIFY=FAIL sha256sum -c ${KARZAR_MANIFEST_NAME}" >&2
    return 1
  fi

  local expected_paths actual_paths
  expected_paths="$(karzar_manifest_paths "$manifest")"
  actual_paths="$(karzar_tree_find_files "$tree")"
  if [[ "$expected_paths" != "$actual_paths" ]]; then
    echo "VERIFY=FAIL extra or missing files relative to GitHub manifest" >&2
    comm -3 <(printf '%s\n' "$expected_paths") <(printf '%s\n' "$actual_paths") >&2 || true
    return 1
  fi

  karzar_assert_structural_files "$tree"

  local files bytes
  files="$(karzar_tree_file_count "$tree")"
  bytes="$(karzar_tree_total_bytes "$tree")"
  echo "HANDOFF_OK sha=${expected_sha} transport=rsync-delta files=${files} bytes=${bytes} manifest=${actual_manifest_sha}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -euo pipefail
  cmd="${1:-}"
  shift || true
  case "$cmd" in
    rsync-delta)
      karzar_rsync_delta "$@"
      ;;
    write-manifest)
      karzar_write_deploy_manifest "$@"
      echo "files=${KARZAR_FILE_COUNT} bytes=${KARZAR_TOTAL_BYTES} manifest=${KARZAR_MANIFEST_SHA}"
      ;;
    *)
      echo "usage: $0 rsync-delta <src> <dest> | write-manifest <tree> <manifest>" >&2
      exit 2
      ;;
  esac
fi
