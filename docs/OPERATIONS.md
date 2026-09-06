# Operations

Runbook for environments, backup, deploy, and incidents. Commerce/payment policy: [`COMMERCE.md`](COMMERCE.md). Hesabfa: [`HESABFA.md`](HESABFA.md). SEP: [`SEP_PAYMENT_GATEWAY.md`](SEP_PAYMENT_GATEWAY.md).

## Environments

| Env | `APP_ENV` | Compose | Notes |
|-----|-----------|---------|-------|
| Development | `development` | `docker-compose.yml` + `docker-compose.dev.yml` | Bind-mount; OTP echo OK when `DEBUG=true` |
| Staging | `staging` | `docker-compose.yml` + `docker-compose.staging.yml` | No bind-mount; `DEBUG=false`; HTTPS |
| Production | `production` | `docker-compose.yml` + secrets | Redis required; **mock payment forbidden** |

Templates: `.env.example`, `.env.staging.example`. Never commit real secrets.

**Topology:** staging deploy targets the **same VPS** as public traffic (`karzartools.com`). There is no isolated staging host (`CR-011`).

## Networking

Compose network `karzar`: Postgres `db:5432`, Redis `redis:6379`. Host maps: API `8000`, Postgres `5435`, Redis `6379`.

## Observability

- Logs: console always; file when `LOG_TO_FILE=true` (`LOG_FILE`, default `logs/app.log`, 10×10MB). Volume `karzar_logs` → `/app/logs`.
- Metrics: `GET /metrics` when `ENABLE_METRICS=true`. Nginx must restrict to loopback.
- Health: `GET /health` (liveness), `GET /ready` (DB + Redis).
- Sentry: soft-init when `SENTRY_DSN` set and `sentry-sdk` installed. Uptime: point an external monitor at `/health` and `/ready`. Until those accounts exist, watch `/metrics` + container logs for 15 minutes after every deploy.

## Backup / restore

```bash
./scripts/backup_db.sh                          # → backups/karzar_YYYYMMDD_HHMMSS.sql.gz
./scripts/restore_db.sh backups/karzar_….sql.gz
./scripts/backup_uploads.sh                     # volume karzar_uploads → /app/data/uploads
./scripts/restore_uploads.sh backups/karzar_uploads_….tar.gz
sudo bash scripts/backup_offsite_sync.sh        # requires BACKUP_OFFSITE_URI
```

On-host `./backups/` is **not** disaster recovery. Sync off-host after each dump. Suggested: 7 daily + 4 weekly. Cron installer: `deploy/staging/scripts/install-backup-cron.sh` (invokes scripts via `/bin/bash` because artifact download may strip +x).

Restore onto a scratch/staging target first. Suggested RPO ≤ 24h, RTO ≤ 2h.

Unresolved: a recorded restore-drill result (issue [#247](https://github.com/Shebahati/Karzar/issues/247)).

## Migrations

```bash
docker compose exec app alembic upgrade head
docker compose exec app alembic current
docker compose exec app alembic downgrade -1   # non-prod first
```

Never downgrade production past a column-drop without a backup. Prefer forward-fix migrations.

## VPS bootstrap (unique host facts)

Live tree on the VPS is `/opt/karzar/Karzar`. First-time host setup:

```bash
sudo git clone https://github.com/Shebahati/Karzar.git /opt/karzar/Karzar
cd /opt/karzar/Karzar
sudo bash deploy/staging/scripts/bootstrap-vps.sh   # Docker, Nginx, Certbot, UFW 22/80/443
```

DNS A records historically used `api` / `shop` / `admin`. Public shop today is `www.karzartools.com`; API is `api.karzartools.com`. Backend env lives on the host (not in git): `TRUSTED_HOSTS`, `CORS_ORIGINS`, `SECRET_KEY`, DB password, step-up PIN. Historical step-by-step: `docs/archive/deploy/staging/STAGING_DEPLOY.md` (stale mock-payment phase — do not follow its provider advice).

## Deploy

1. CI green on `main` (lint + pytest + **coverage ≥ 68%** — `pyproject.toml`).
2. Update [`API_CHANGELOG.md`](API_CHANGELOG.md) if the contract changed.
3. Owner: set Actions variable `KARZAR_DEPLOY_FREEZE=false` only for the window needed.
4. Run **Deploy Staging** via GitHub Actions `workflow_dispatch` on `main` — **not** push-auto-deploy (`.github/workflows/deploy-staging.yml`).
5. Compose on the VPS: `docker compose -f docker-compose.yml -f docker-compose.staging.yml`. Entrypoint runs `alembic upgrade head`.
6. Smoke: `deploy/staging/scripts/smoke-staging.sh` (`GET /ready`, admin session, checkout against the **configured** provider). Do **not** switch production/staging-live to mock to smoke.
7. Restore `KARZAR_DEPLOY_FREEZE=true` immediately.
8. Watch error rate and `/metrics` for 15 minutes.

### Staging source handoff

GitHub-hosted checkout is pinned to `github.sha`. That runner builds an isolated deploy tree (tracked files; no `.git` / `.github` / caches / uploads / `.env`), writes `deploy-manifest.sha256`, seeds `/opt/karzar/incoming/<sha>/tree` from the current live trees (`/opt/karzar/Karzar` and `/opt/karzar/frontend`) without mutating them, then delta-rsyncs over IPv4 SSH (`--checksum --delete`, host key pinned in `deploy/staging/ssh/known_hosts`).

`HANDOFF_COMPLETE` is written only after the GitHub-hosted session verifies the staged tree (`sha256sum -c` plus extra/missing/structural checks). GitHub Actions job outputs are NOT used to carry the manifest SHA between the GitHub-hosted handoff job and the self-hosted deploy job (run `34039051081`: Actions suppressed `manifest_sha` as a possible secret). The self-hosted runner reads `HANDOFF_COMPLETE` on the VPS, recomputes `sha256sum` of `deploy-manifest.sha256`, compares that to the marker, then re-runs `sha256sum -c`. It does not pull `github.com`, the GitHub API, `raw.githubusercontent.com`, Actions artifacts, or Azure Blob.

After prepare-mode verify writes `HANDOFF_COMPLETE`, the GitHub-hosted session normalizes read/traverse modes **only** under `/opt/karzar/incoming/<sha>` (`0755` on that directory, `a+rX` on tree directories, `a+r` on tree files, `0644` on the marker and `deploy-manifest.sha256`). It does not chmod live `/opt/karzar/Karzar`, `/opt/karzar/frontend`, or secrets. The private-key `umask 077` applies only to the local SSH keyfile so the manifest is not created as `0600` (run `34040385983`: handoff succeeded, self-hosted consume failed immediately).

Handoff failure (timeout, rsync error, missing marker, manifest mismatch, extra/missing/corrupt file) skips live rsync, rebuild, and container restart. Incoming dirs without `HANDOFF_COMPLETE` are leftover debug state, not a completed handoff. Successful deploys remove `/opt/karzar/incoming/<sha>` and incoming dirs older than one day.

Scripts: [`deploy/staging/scripts/push-incoming-source.sh`](../deploy/staging/scripts/push-incoming-source.sh), [`deploy/staging/scripts/verify-incoming-source.sh`](../deploy/staging/scripts/verify-incoming-source.sh), [`deploy/staging/scripts/deploy-tree-lib.sh`](../deploy/staging/scripts/deploy-tree-lib.sh). Local selftest: `bash deploy/staging/scripts/test-delta-rsync-handoff.sh`. Historical collaborator copy: [`archive/docs/COLLABORATOR_DEPLOY.md`](archive/docs/COLLABORATOR_DEPLOY.md).

Production image rollback: revert the container image / previous env. **Never** set `PAYMENT_PROVIDER=mock` on production (boot validators reject it).

`KARZAR_DEPLOY_FREEZE=true` also blocks `apply` mode on live taxonomy workflows; dry-runs remain available.

## Incidents

| Severity | Examples | Actions |
|----------|----------|---------|
| SEV1 | API down, payment verify failing | Roll back image; restore DB only if schema is broken; notify gateway |
| SEV2 | Elevated 5xx, Redis down | Check `/ready`; degrade throttles if needed |
| SEV3 | Single endpoint | Env flag / hotfix / forward migration |

Capture `request-id` from headers/logs. Roll back image before rolling back the database.
