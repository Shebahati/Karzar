# RSYNC FAILURE RECONSTRUCTION

## Failed run

- URL: https://github.com/Shebahati/Karzar/actions/runs/37468470923
- Job: Sync + rebuild staging
- Step: Sync backend → /opt/karzar/Karzar
- headSha: `4e750eafb00f8b6e72c4dba9c539d409c0fd8a02`
- created: 2026-10-06T13:08:27Z
- conclusion: failure
- rsync exit code: **23** (partial transfer)

Preceding freeze-blocked attempt: run `37468416195` (Deployment freeze gate failure only — no rsync).

Successful recovery run: https://github.com/Shebahati/Karzar/actions/runs/37469215878

## Runner identity during deploy

- systemd unit: `actions.runner.Shebahati-Karzar.karzar-vps.service`
- User: `github-runner` (uid 1000)
- WorkingDirectory: `/opt/karzar/actions-runner`
- Workflow step `id` print confirms self-hosted job runs as github-runner (not root).

## Exact rsync command (from workflow)

Source: `/opt/karzar/incoming/${GITHUB_SHA}/tree`  
Destination: `/opt/karzar/Karzar/`  

```bash
rsync -a --delete \
  --exclude '.git/' --exclude '.github/' --exclude '/frontend/' \
  --exclude '.venv/' --exclude 'venv/' --exclude '__pycache__/' \
  --exclude '.pytest_cache/' --exclude '.env' --exclude '.deploy-secrets' \
  --exclude '.env.staging.generated' --exclude 'backups/' --exclude 'rollout-backups/' \
  --exclude 'data/uploads/' --exclude 'logs/' --exclude '*.pyc' \
  --exclude '.mypy_cache/' --exclude '.ruff_cache/' --exclude '.coverage' \
  --exclude 'actions-runner/' \
  "$SRC"/ /opt/karzar/Karzar/
```

## Error classes observed

| Class | Evidence |
| --- | --- |
| cannot delete | `delete_file: unlink(audit/insize-price-20-*/...) failed: Permission denied (13)` |
| cannot overwrite / create temp | `mkstemp ".../deploy/staging/....XXXX" failed: Permission denied (13)` for GSC templates and `services/gsc_mcp/*` |
| cannot chgrp | `chgrp "/opt/karzar/Karzar/deploy" failed: Operation not permitted (1)` (rsync `-a` includes ownership attrs) |
| cannot traverse/delete non-empty orphan dirs | `cannot delete non-empty directory: audit/insize-price-20-*` |

Not merely "permissions" generically: **destination tree contained root-owned deploy-managed paths and untracked root-owned orphan audit dirs**, so the non-root runner could neither replace nor delete them.

## Success path

1. One-time operational `chown` of `deploy/`, `services/`, and `audit/insize-price-20-*` to `github-runner` (outside this audit's mutation scope; already executed earlier).
2. Redeploy run `37469215878` succeeded; subsequent rsync `--delete` removed orphan audit dirs (confirmed absent now).
