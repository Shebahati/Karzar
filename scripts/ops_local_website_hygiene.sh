#!/usr/bin/env bash
# Local hygiene for /home/moahmmad/Projects/Karzar/Website (CR-017 / CR-009).
#
# Safe defaults:
#   - Archives Website/docs + .env/.deploy-secrets + backups
#   - Creates a clean clone at ~/Projects/Karzar-clean/Karzar from origin/main
#   - Does NOT delete Website/ or worktrees unless --remove-safe-worktrees
#
# Usage:
#   bash scripts/ops_local_website_hygiene.sh
#   bash scripts/ops_local_website_hygiene.sh --remove-safe-worktrees
#
set -euo pipefail

WEBSITE="${KARZAR_WEBSITE:-/home/moahmmad/Projects/Karzar/Website}"
BACKEND="${WEBSITE}/backend"
CLEAN_ROOT="${KARZAR_CLEAN_ROOT:-$HOME/Projects/Karzar-clean}"
CLEAN_CLONE="${CLEAN_ROOT}/Karzar"
ARCHIVE_ROOT="${KARZAR_ARCHIVE_ROOT:-$HOME/Archives/karzar-$(date +%F)}"
REMOTE_URL="${KARZAR_REMOTE_URL:-https://github.com/Shebahati/Karzar.git}"
REMOVE_SAFE=0

for arg in "$@"; do
  case "$arg" in
    --remove-safe-worktrees) REMOVE_SAFE=1 ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0
      ;;
  esac
done

die() { echo "FATAL: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "missing $1"; }

need git
need tar

[[ -d "$WEBSITE" ]] || die "Website path not found: $WEBSITE"
[[ -d "$BACKEND/.git" || -f "$BACKEND/.git" ]] || die "backend git missing: $BACKEND"

mkdir -p "$ARCHIVE_ROOT" "$CLEAN_ROOT"
echo "== Archive → $ARCHIVE_ROOT"

if [[ -d "$WEBSITE/docs" ]]; then
  tar -czf "$ARCHIVE_ROOT/Website-docs.tgz" -C "$WEBSITE" docs
  echo "  archived docs"
fi

for f in \
  "$BACKEND/.env" \
  "$WEBSITE/.env" \
  "$WEBSITE/.deploy-secrets" \
  "$BACKEND/.deploy-secrets"
do
  if [[ -f "$f" ]]; then
    cp -a "$f" "$ARCHIVE_ROOT/$(basename "$(dirname "$f")")-$(basename "$f")"
    echo "  archived $f"
  fi
done

if [[ -d "$BACKEND/backups" ]]; then
  tar -czf "$ARCHIVE_ROOT/backend-backups.tgz" -C "$BACKEND" backups
  echo "  archived backend/backups"
fi

# Inventory worktrees / sibling checkouts
INV="$ARCHIVE_ROOT/worktree-inventory.txt"
{
  echo "# generated $(date -Is)"
  echo "## git worktree list"
  git -C "$BACKEND" worktree list || true
  echo
  echo "## sibling dirs under Website"
  ls -1 "$WEBSITE"
  echo
  echo "## unpushed commits per worktree (origin/main..HEAD)"
  while read -r path _sha rest; do
    [[ -z "${path:-}" ]] && continue
    [[ "$path" == *"worktree list"* ]] && continue
    if [[ -d "$path" ]]; then
      ahead="$(git -C "$path" rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
      dirty="$(git -C "$path" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
      br="$(git -C "$path" branch --show-current 2>/dev/null || echo detached)"
      echo "$path | branch=$br | ahead_of_origin_main=$ahead | dirty_files=$dirty"
    fi
  done < <(git -C "$BACKEND" worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2}')
} | tee "$INV"

echo "== Clean clone → $CLEAN_CLONE"
if [[ -d "$CLEAN_CLONE/.git" ]]; then
  git -C "$CLEAN_CLONE" fetch origin
  git -C "$CLEAN_CLONE" checkout main
  git -C "$CLEAN_CLONE" pull --ff-only origin main
else
  git clone "$REMOTE_URL" "$CLEAN_CLONE"
  git -C "$CLEAN_CLONE" checkout main
fi

# Restore env into clean clone if present
for f in "$ARCHIVE_ROOT"/backend-.env "$ARCHIVE_ROOT"/.env; do
  if [[ -f "$f" ]]; then
    cp -a "$f" "$CLEAN_CLONE/.env"
    echo "  restored .env into clean clone"
    break
  fi
done

echo "== Clean clone HEAD"
git -C "$CLEAN_CLONE" log -1 --oneline
git -C "$CLEAN_CLONE" status -sb

if [[ "$REMOVE_SAFE" -eq 1 ]]; then
  echo "== Removing SAFE worktrees (ahead=0 and dirty=0, not primary backend)"
  while read -r path _rest; do
    [[ -z "${path:-}" || "$path" == "$BACKEND" ]] && continue
    ahead="$(git -C "$path" rev-list --count origin/main..HEAD 2>/dev/null || echo 1)"
    dirty="$(git -C "$path" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "$ahead" == "0" && "$dirty" == "0" ]]; then
      echo "  remove $path"
      git -C "$BACKEND" worktree remove --force "$path" 2>/dev/null \
        || rm -rf "$path"
    else
      echo "  KEEP $path (ahead=$ahead dirty=$dirty)"
    fi
  done < <(git -C "$BACKEND" worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2}')
else
  echo "== Skip worktree removal (pass --remove-safe-worktrees to prune ahead=0 dirty=0)"
fi

echo
echo "DONE."
echo "  Archive:     $ARCHIVE_ROOT"
echo "  Clean clone: $CLEAN_CLONE"
echo "  Old tree:    $WEBSITE  (kept; prune later with --remove-safe-worktrees)"
echo "Develop from:  $CLEAN_CLONE"
