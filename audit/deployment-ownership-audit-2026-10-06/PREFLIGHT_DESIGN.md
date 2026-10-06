# Deployment ownership preflight (design only)

Insert **before** `Sync backend → /opt/karzar/Karzar` in `deploy-staging.yml`.

## Behavior

Run as `github-runner`, read-only (no chown/chmod):

1. Assert `id -un` == `github-runner`.
2. For required writable roots:
   - `/opt/karzar/Karzar`
   - `/opt/karzar/frontend`
   - `/opt/karzar/incoming`
   Fail if not traversable or not writable by the runner.
3. Scan deploy-managed paths for unexpected `uid=0` files/dirs **that are not allowlisted**:
   - allowlist: none under `deploy/`, `services/`, `app/`, `aods/`, `scripts/`, `audit/` (tracked)
   - ignore/exclude: `.env`, `backups/`, `data/uploads/`, `logs/`, `.deploy-secrets`
4. Detect untracked orphan dirs under `audit/` that are root-owned or not writable (would break `--delete`).
5. Print a concise diagnostic table: path, owner, group, mode, problem class.
6. Exit non-zero **before** rsync if any `UNEXPECTED_OWNERSHIP_DRIFT` found.

## Sample check (illustrative)

```bash
bad=$(find /opt/karzar/Karzar/deploy /opt/karzar/Karzar/services /opt/karzar/Karzar/app \
  -user root -print)
if [[ -n "$bad" ]]; then
  echo "DEPLOY_OWNERSHIP_PREFLIGHT_FAIL root-owned deploy-managed paths:" >&2
  echo "$bad" >&2
  exit 1
fi
test -w /opt/karzar/Karzar && test -w /opt/karzar/frontend
```

No automatic chown in CI without a separate Owner-authorized remediation job.
