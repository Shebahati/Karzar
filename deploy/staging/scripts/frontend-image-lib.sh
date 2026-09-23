#!/usr/bin/env bash
# Shared helpers for prebuilt staging frontend image handoff (GitHub-hosted → VPS).
# Does not log secrets. Safe to source from push/load/selftest scripts.
set -euo pipefail

if [[ -n "${KARZAR_FRONTEND_IMAGE_LIB_LOADED:-}" ]]; then
  return 0 2>/dev/null || exit 0
fi
KARZAR_FRONTEND_IMAGE_LIB_LOADED=1

KARZAR_FRONTEND_IMAGES_SUBDIR="${KARZAR_FRONTEND_IMAGES_SUBDIR:-frontend-images}"
KARZAR_FRONTEND_BUNDLE_NAME="${KARZAR_FRONTEND_BUNDLE_NAME:-frontend-images.tar}"
KARZAR_FRONTEND_CHECKSUM_NAME="${KARZAR_FRONTEND_CHECKSUM_NAME:-frontend-images.sha256}"
KARZAR_FRONTEND_IMAGES_MARKER="${KARZAR_FRONTEND_IMAGES_MARKER:-FRONTEND_IMAGES_HANDOFF_COMPLETE}"
KARZAR_IMAGE_SOURCE_DEFAULT="${KARZAR_IMAGE_SOURCE_DEFAULT:-https://github.com/Shebahati/Karzar}"
KARZAR_OCI_REVISION_LABEL="${KARZAR_OCI_REVISION_LABEL:-org.opencontainers.image.revision}"
KARZAR_OCI_SOURCE_LABEL="${KARZAR_OCI_SOURCE_LABEL:-org.opencontainers.image.source}"

# Self-hosted staging deploy / verify identity (see deploy-staging.yml diagnose step).
karzar_self_hosted_deploy_user() {
  echo "${KARZAR_SELF_HOSTED_DEPLOY_USER:-github-runner}"
}

karzar_self_hosted_deploy_group() {
  echo "${KARZAR_SELF_HOSTED_DEPLOY_GROUP:-$(karzar_self_hosted_deploy_user)}"
}

karzar_run_as_deploy_user() {
  local user
  user="$(karzar_self_hosted_deploy_user)"
  if [[ "$(id -un)" == "$user" ]]; then
    "$@"
    return
  fi
  if command -v runuser >/dev/null 2>&1; then
    runuser -u "$user" -- "$@"
    return
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo -u "$user" -- "$@"
    return
  fi
  echo "VERIFY=FAIL cannot run command as deploy user ${user}" >&2
  return 1
}

# After rsync: bundle/checksum readable by github-runner; dir traversable.
karzar_normalize_frontend_images_permissions() {
  local dir="${1:?incoming frontend-images dir required}"
  local user group bundle checksum
  user="$(karzar_self_hosted_deploy_user)"
  group="$(karzar_self_hosted_deploy_group)"
  bundle="${dir}/${KARZAR_FRONTEND_BUNDLE_NAME}"
  checksum="${dir}/${KARZAR_FRONTEND_CHECKSUM_NAME}"

  test -d "$dir"
  test -f "$bundle"
  test -f "$checksum"

  chmod 0755 "$dir"
  if [[ "${KARZAR_SKIP_FRONTEND_CHOWN:-}" != "1" ]]; then
    if ! chown "${user}:${group}" "$bundle" "$checksum"; then
      echo "VERIFY=FAIL chown ${user}:${group} on frontend image bundle" >&2
      return 1
    fi
  fi
  chmod 0640 "$bundle" "$checksum"
}

karzar_frontend_shop_image_tag() {
  local sha="${1:?sha required}"
  echo "karzar-shop:sha-${sha}"
}

karzar_frontend_admin_image_tag() {
  local sha="${1:?sha required}"
  echo "karzar-admin:sha-${sha}"
}

karzar_staging_shop_alias() {
  echo "${KARZAR_STAGING_SHOP_ALIAS:-karzar-shop:staging}"
}

karzar_staging_admin_alias() {
  echo "${KARZAR_STAGING_ADMIN_ALIAS:-karzar-admin:staging}"
}

karzar_frontend_images_incoming_dir() {
  local sha="${1:?sha required}"
  local base="${KARZAR_INCOMING_BASE:-/opt/karzar/incoming}"
  echo "${base}/${sha}/${KARZAR_FRONTEND_IMAGES_SUBDIR}"
}

karzar_docker_image_revision() {
  local ref="${1:?image ref required}"
  if [[ -n "${KARZAR_MOCK_REVISION_MAP:-}" ]]; then
    local line key val
    while IFS= read -r line; do
      key="${line%%=*}"
      val="${line#*=}"
      if [[ "$key" == "$ref" ]]; then
        echo "$val"
        return 0
      fi
    done <<< "$KARZAR_MOCK_REVISION_MAP"
    echo ""
    return 0
  fi
  docker image inspect --format "{{ index .Config.Labels \"${KARZAR_OCI_REVISION_LABEL}\" }}" "$ref" 2>/dev/null || true
}

karzar_docker_image_source() {
  local ref="${1:?image ref required}"
  if [[ -n "${KARZAR_MOCK_SOURCE_MAP:-}" ]]; then
    local line key val
    while IFS= read -r line; do
      key="${line%%=*}"
      val="${line#*=}"
      if [[ "$key" == "$ref" ]]; then
        echo "$val"
        return 0
      fi
    done <<< "$KARZAR_MOCK_SOURCE_MAP"
    echo ""
    return 0
  fi
  docker image inspect --format "{{ index .Config.Labels \"${KARZAR_OCI_SOURCE_LABEL}\" }}" "$ref" 2>/dev/null || true
}

karzar_verify_image_revision() {
  local image_ref="$1"
  local expected_sha="$2"
  local actual
  actual="$(karzar_docker_image_revision "$image_ref")"
  if [[ -z "$actual" || "$actual" == "<no value>" ]]; then
    echo "VERIFY=FAIL missing ${KARZAR_OCI_REVISION_LABEL} on ${image_ref}" >&2
    return 1
  fi
  if [[ "$actual" != "$expected_sha" ]]; then
    echo "VERIFY=FAIL ${image_ref} revision=${actual} expected=${expected_sha}" >&2
    return 1
  fi
  return 0
}

# Bundle + checksum only (no marker). Prints actual bundle sha256 on success.
karzar_verify_frontend_bundle_digest() {
  local dir="${1:?incoming frontend-images dir required}"
  local bundle="${dir}/${KARZAR_FRONTEND_BUNDLE_NAME}"
  local checksum="${dir}/${KARZAR_FRONTEND_CHECKSUM_NAME}"

  [[ -f "$bundle" ]] || { echo "VERIFY=FAIL missing bundle" >&2; return 1; }
  [[ -f "$checksum" ]] || { echo "VERIFY=FAIL missing checksum file" >&2; return 1; }

  local nonempty
  nonempty="$(grep -cve '^[[:space:]]*$' "$checksum" || true)"
  if [[ "$nonempty" != "1" ]]; then
    echo "VERIFY=FAIL checksum file must contain exactly one non-empty line" >&2
    return 1
  fi

  local file_digest file_name actual_digest
  read -r file_digest file_name < "$checksum"
  if [[ "$file_name" != "${KARZAR_FRONTEND_BUNDLE_NAME}" ]]; then
    echo "VERIFY=FAIL checksum names unexpected bundle file (${file_name:-empty})" >&2
    return 1
  fi
  if [[ ! "$file_digest" =~ ^[0-9a-f]{64}$ ]]; then
    echo "VERIFY=FAIL checksum digest must be 64 lowercase hex chars" >&2
    return 1
  fi

  actual_digest="$(sha256sum "$bundle" | awk '{print $1}')"
  if [[ "$actual_digest" != "$file_digest" ]]; then
    echo "VERIFY=FAIL bundle digest does not match checksum file" >&2
    return 1
  fi
  echo "$actual_digest"
  return 0
}

karzar_verify_frontend_bundle_readable_by_deploy_user() {
  local dir="${1:?incoming frontend-images dir required}"
  local bundle="${dir}/${KARZAR_FRONTEND_BUNDLE_NAME}"
  local checksum="${dir}/${KARZAR_FRONTEND_CHECKSUM_NAME}"

  if ! karzar_run_as_deploy_user test -r "$bundle"; then
    echo "VERIFY=FAIL deploy user cannot read ${KARZAR_FRONTEND_BUNDLE_NAME}" >&2
    return 1
  fi
  if ! karzar_run_as_deploy_user test -r "$checksum"; then
    echo "VERIFY=FAIL deploy user cannot read ${KARZAR_FRONTEND_CHECKSUM_NAME}" >&2
    return 1
  fi
  if ! karzar_run_as_deploy_user bash -c "cd $(printf '%q' "$dir") && sha256sum -c $(printf '%q' "${KARZAR_FRONTEND_CHECKSUM_NAME}")"; then
    echo "VERIFY=FAIL deploy user checksum verification failed" >&2
    return 1
  fi
  return 0
}

# rsync or local save → normalize → digest verify → deploy-user verify → marker.
karzar_finalize_frontend_images_incoming_handoff() {
  local dir="${1:?dir required}"
  local sha="${2:?sha required}"
  local expected_bundle_sha="${3:?expected bundle sha256 required}"
  local shop_tag="${4:?shop tag required}"
  local admin_tag="${5:?admin tag required}"
  local transport="${6:-rsync-ssh-ipv4}"
  local marker="${dir}/${KARZAR_FRONTEND_IMAGES_MARKER}"
  local actual_sha

  rm -f "$marker"
  karzar_normalize_frontend_images_permissions "$dir"

  actual_sha="$(karzar_verify_frontend_bundle_digest "$dir")" || return 1
  if [[ "$actual_sha" != "$expected_bundle_sha" ]]; then
    echo "VERIFY=FAIL bundle sha256 mismatch (expected ${expected_bundle_sha} got ${actual_sha})" >&2
    return 1
  fi

  karzar_verify_frontend_bundle_readable_by_deploy_user "$dir" || return 1

  karzar_write_frontend_images_handoff_marker "$dir" "$sha" "$actual_sha" "$shop_tag" "$admin_tag" "$transport"
  chmod 0644 "$marker"
}

# Require marker + bundle + checksum; actual digest == checksum file == marker bundle_sha256.
karzar_verify_frontend_bundle_integrity() {
  local dir="${1:?incoming frontend-images dir required}"
  local marker="${dir}/${KARZAR_FRONTEND_IMAGES_MARKER}"
  local actual_digest

  [[ -f "$marker" ]] || { echo "VERIFY=FAIL missing ${KARZAR_FRONTEND_IMAGES_MARKER}" >&2; return 1; }

  karzar_read_frontend_images_handoff_marker "$marker"

  actual_digest="$(karzar_verify_frontend_bundle_digest "$dir")" || return 1
  if [[ "$actual_digest" != "$KARZAR_FE_HANDOFF_BUNDLE_SHA" ]]; then
    echo "VERIFY=FAIL marker bundle_sha256 does not match bundle digest" >&2
    return 1
  fi
  if [[ ! "$KARZAR_FE_HANDOFF_BUNDLE_SHA" =~ ^[0-9a-f]{64}$ ]]; then
    echo "VERIFY=FAIL marker bundle_sha256 format" >&2
    return 1
  fi
  return 0
}

karzar_stream_frontend_handoff_shell_functions() {
  declare -f \
    karzar_self_hosted_deploy_user \
    karzar_self_hosted_deploy_group \
    karzar_run_as_deploy_user \
    karzar_normalize_frontend_images_permissions \
    karzar_verify_frontend_bundle_digest \
    karzar_verify_frontend_bundle_readable_by_deploy_user \
    karzar_write_frontend_images_handoff_marker \
    karzar_finalize_frontend_images_incoming_handoff
}

karzar_write_frontend_images_handoff_marker() {
  local dir="$1"
  local sha="$2"
  local bundle_sha="$3"
  local shop_tag="$4"
  local admin_tag="$5"
  # Optional 6th arg: transport. Default preserves legacy GitHub→VPS SSH push path.
  local transport="${6:-rsync-ssh-ipv4}"
  if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
    echo "refuse to write ${KARZAR_FRONTEND_IMAGES_MARKER}: invalid sha" >&2
    return 1
  fi
  if [[ ! "$bundle_sha" =~ ^[0-9a-f]{64}$ ]]; then
    echo "refuse to write ${KARZAR_FRONTEND_IMAGES_MARKER}: invalid bundle sha256" >&2
    return 1
  fi
  case "$transport" in
    rsync-ssh-ipv4|local-package) ;;
    *)
      echo "refuse to write ${KARZAR_FRONTEND_IMAGES_MARKER}: unsupported transport=${transport}" >&2
      return 1
      ;;
  esac
  cat > "${dir}/${KARZAR_FRONTEND_IMAGES_MARKER}" <<EOF
sha=${sha}
bundle_sha256=${bundle_sha}
shop_image=${shop_tag}
admin_image=${admin_tag}
transport=${transport}
EOF
}

karzar_read_frontend_images_handoff_marker() {
  local marker="$1"
  local line key val
  KARZAR_FE_HANDOFF_SHA=""
  KARZAR_FE_HANDOFF_BUNDLE_SHA=""
  KARZAR_FE_HANDOFF_SHOP=""
  KARZAR_FE_HANDOFF_ADMIN=""
  if [[ ! -f "$marker" ]]; then
    echo "${KARZAR_FRONTEND_IMAGES_MARKER} absent" >&2
    return 1
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    if [[ "$line" == *$'\r'* ]]; then
      echo "${KARZAR_FRONTEND_IMAGES_MARKER} contains CR" >&2
      return 1
    fi
    key="${line%%=*}"
    val="${line#*=}"
    case "$key" in
      sha) KARZAR_FE_HANDOFF_SHA="$val" ;;
      bundle_sha256) KARZAR_FE_HANDOFF_BUNDLE_SHA="$val" ;;
      shop_image) KARZAR_FE_HANDOFF_SHOP="$val" ;;
      admin_image) KARZAR_FE_HANDOFF_ADMIN="$val" ;;
      transport) ;;
      *) echo "${KARZAR_FRONTEND_IMAGES_MARKER} unknown key" >&2; return 1 ;;
    esac
  done < "$marker"
  [[ -n "$KARZAR_FE_HANDOFF_SHA" && -n "$KARZAR_FE_HANDOFF_BUNDLE_SHA" ]] || {
    echo "${KARZAR_FRONTEND_IMAGES_MARKER} incomplete" >&2
    return 1
  }
  if [[ "$KARZAR_FE_HANDOFF_SHA" != "${EXPECTED_SHA:-$GITHUB_SHA}" ]]; then
    echo "${KARZAR_FRONTEND_IMAGES_MARKER} sha mismatch" >&2
    return 1
  fi
  return 0
}

karzar_ssh_handoff_options() {
  local keyfile="$1"
  local port="$2"
  local known_hosts="$3"
  printf '%s\0' \
    ssh -4 \
    -i "$keyfile" \
    -p "$port" \
    -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -o PasswordAuthentication=no \
    -o KbdInteractiveAuthentication=no \
    -o UserKnownHostsFile="$known_hosts" \
    -o StrictHostKeyChecking=yes \
    -o BatchMode=yes \
    -o ConnectTimeout=25 \
    -o ServerAliveInterval=10 \
    -o ServerAliveCountMax=3
}

karzar_build_ssh_cmd_string() {
  local keyfile="$1"
  local port="$2"
  local known_hosts="$3"
  printf 'ssh -4 -i %q -p %s -o IdentitiesOnly=yes -o PreferredAuthentications=publickey -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o UserKnownHostsFile=%q -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=25 -o ServerAliveInterval=10 -o ServerAliveCountMax=3' \
    "$keyfile" "$port" "$known_hosts"
}
