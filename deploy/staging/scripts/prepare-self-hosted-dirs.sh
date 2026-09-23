#!/usr/bin/env bash
# Phase 1 host prep: deploy workspace dirs for self-hosted package (no live mutate).
# Idempotent. Requires root/sudo once to chown /opt/karzar/incoming from root.
# Does not touch /opt/karzar/Karzar live tree, docker, or alembic.
set -euo pipefail

KARZAR_ROOT="${KARZAR_ROOT:-/opt/karzar}"
RUNNER_USER="${KARZAR_RUNNER_USER:-github-runner}"
RUNNER_GROUP="${KARZAR_RUNNER_GROUP:-github-runner}"

DIRS=(
  "${KARZAR_ROOT}/incoming"
  "${KARZAR_ROOT}/workspace"
  "${KARZAR_ROOT}/mirror"
  "${KARZAR_ROOT}/logs"
  "${KARZAR_ROOT}/logs/deploy"
)

echo "=== BEFORE ==="
for d in "${DIRS[@]}"; do
  if [[ -e "$d" ]]; then
    stat -c '%U:%G %a %n' "$d"
  else
    echo "MISSING $d"
  fi
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "prepare-self-hosted-dirs.sh must run as root (sudo) for chown" >&2
  exit 1
fi

getent passwd "$RUNNER_USER" >/dev/null
getent group "$RUNNER_GROUP" >/dev/null

for d in "${DIRS[@]}"; do
  mkdir -p "$d"
done

# incoming: setgid so new handoff dirs inherit runner group
chown "${RUNNER_USER}:${RUNNER_GROUP}" \
  "${KARZAR_ROOT}/incoming" \
  "${KARZAR_ROOT}/workspace" \
  "${KARZAR_ROOT}/mirror" \
  "${KARZAR_ROOT}/logs" \
  "${KARZAR_ROOT}/logs/deploy"
chmod 2775 "${KARZAR_ROOT}/incoming"
chmod 0755 \
  "${KARZAR_ROOT}/workspace" \
  "${KARZAR_ROOT}/mirror" \
  "${KARZAR_ROOT}/logs" \
  "${KARZAR_ROOT}/logs/deploy"

# Refuse world-writable
for d in "${DIRS[@]}"; do
  mode="$(stat -c '%a' "$d")"
  if [[ "$mode" =~ [2367]$ ]]; then
    echo "REFUSE world-writable mode=${mode} path=${d}" >&2
    exit 1
  fi
done

echo "=== AFTER ==="
for d in "${DIRS[@]}"; do
  stat -c '%U:%G %a %n' "$d"
done
echo "PREPARE_DIRS_OK"
