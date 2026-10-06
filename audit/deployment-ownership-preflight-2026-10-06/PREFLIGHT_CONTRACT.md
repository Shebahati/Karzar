# Preflight contract

## Runner identity

```text
expected user = github-runner
effective UID/GID must match that account
root execution → FAIL (unless --allow-root-runner, unused in Deploy Staging)
```

## Managed paths (writability + traversal)

| Path | Ownership policy | Writability | Rsync |
|------|------------------|-------------|--------|
| `/opt/karzar/incoming` | github-runner | required | package handoff |
| `/opt/karzar/Karzar` | github-runner | required | backend `--delete` |
| `/opt/karzar/frontend` | github-runner | required | frontend `--delete` |
| incoming `<sha>/tree` | github-runner | required | rsync source |

Managed descendants under live checkout (examples): `app/`, `deploy/`,
`services/`, `audit/`, `aods/`, `scripts/`, `alembic/`, top-level tracked files.

## Root-only exclusions (not required to be runner-owned)

```text
.env
.deploy-secrets
.env.staging.generated
backups/
rollout-backups/
data/uploads/
logs/
actions-runner/
```

Host paths outside the checkout (not scanned): `/etc/nginx`, Let's Encrypt certs,
`/opt/karzar/.deploy-secrets`, `/etc/karzar/gsc-mcp.env`.

Preflight surfaces ownership/mode metadata only — never secret file contents.

## Detection

1. Unexpected `uid=0` inside managed, non-excluded tree → FAIL
2. Foreign non-writable ownership → FAIL
3. `rsync --dry-run --itemize-changes --delete` plan:
   - destination-only paths the runner cannot unlink → FAIL (`undeletable`)
   - transfer targets the runner cannot replace/create (mkstemp class) → FAIL
4. No auto-chown; optional exact-path remediation suggestions printed only

## Exit codes

```text
0 = PASS
2 = FAIL
```

## Workflow ordering

```text
deploy-freeze (ubuntu; KARZAR_DEPLOY_FREEZE)
  → package (incoming)
  → verify incoming
  → Ownership preflight
  → Sync backend rsync   # only if preflight PASS
  → Sync frontend
  → rebuild / smoke
```

Preflight does not mutate `KARZAR_DEPLOY_FREEZE`. On FAIL: no rsync, no
container rebuild, freeze variable unchanged (Owner restores `true` as usual).
