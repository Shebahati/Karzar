# Operations

Runbook for environments, backup, deploy, and incidents. Commerce/payment policy: [`COMMERCE.md`](COMMERCE.md). Hesabfa: [`HESABFA.md`](HESABFA.md). SEP: [`SEP_PAYMENT_GATEWAY.md`](SEP_PAYMENT_GATEWAY.md).

## Environments

| Env | `APP_ENV` | Compose | Notes |
|-----|-----------|---------|-------|
| Development | `development` | `docker-compose.yml` + `docker-compose.dev.yml` | Bind-mount; OTP echo OK when `DEBUG=true` |
| Staging (label) | `staging` | `docker-compose.yml` + `docker-compose.staging.yml` | No bind-mount; `DEBUG=false`; HTTPS |
| Production | `production` | `docker-compose.yml` + secrets | Redis required; **mock payment forbidden** |
| Catalog staging (isolated) | `staging` + `KARZAR_DATA_PLANE=catalog_staging` | `docker-compose.catalog-staging.yml` | Separate DB + uploads; see [`CATALOG_STAGING_ISOLATION.md`](CATALOG_STAGING_ISOLATION.md) |

Templates: `.env.example`, `.env.staging.example`, `.env.catalog-staging.example`. Never commit real secrets.

**Topology:** the historic “staging” deploy targets the **same VPS** as public traffic (`karzartools.com`). That stack is the **live** data plane (`CR-011`): `APP_ENV=staging` is a process label; default `KARZAR_DATA_PLANE` is `live`. It is **not** safe for catalog APPLY rehearsal. Use the isolated catalog-staging Compose project for that work.

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
./scripts/backup_uploads.sh                     # → backups/karzar_uploads_YYYYMMDD_HHMMSS.tar.gz
./scripts/restore_uploads.sh backups/karzar_uploads_….tar.gz
./scripts/backup_offsite_sync.sh                # requires BACKUP_OFFSITE_URI (host secrets)
./scripts/backup_offsite_sync.sh --preflight    # non-mutating S3 head-bucket / rsync tooling check
./scripts/check_backup_health.sh                # read-only local + offsite evidence
```

### Readiness tiers (do not collapse these)

| Tier | Meaning | Current truth |
|------|---------|---------------|
| `LOCAL_BACKUP_READY` | Daily on-host DB + uploads dumps exist and can be restored onto scratch | **Proven** — DB restore drill `restore-drill-db-2026-09-22-9126775872ce` (2026-09-22) |
| `OFFSITE_SYNC_CONFIGURED` | Cron schedules offsite sync; `BACKUP_OFFSITE_URI` in host secrets | **Design in repo** — URI still operator-owned; not claimed live-configured by docs alone |
| `OFFSITE_SYNC_PROVEN` | A real offsite sync has succeeded (success marker + destination evidence) | **Not yet proven** |
| `OFFSITE_RECOVERY_PROVEN` | Restore from an offsite artifact onto scratch succeeded | **Not yet proven** |

Issue [#247](https://github.com/Shebahati/Karzar/issues/247) is **CLOSED on GitHub** while offsite sync/recovery criteria remain incomplete. Do **not** treat #247 as fully satisfied. A future Owner decision may reopen it or open a follow-up ops issue. `EXTERNAL_ALERTING` (backup failure → external monitor) is **NOT IMPLEMENTED**; `check_backup_health.sh` is the local hook an uptime/cron monitor can call later.

### Scheduled pipeline (UTC)

Installed by `deploy/staging/scripts/install-backup-cron.sh` into `/etc/cron.d/karzar-backup`:

| Time (UTC) | Job |
|------------|-----|
| 03:15 | DB dump (`backup_db.sh`) |
| 03:30 | uploads archive (`backup_uploads.sh`) |
| 03:45 | offsite sync (`backup_offsite_sync.sh`) |

Jobs are separate cron entries: offsite failure does **not** stop DB/uploads. Offsite refuses (exit non-zero) when `BACKUP_OFFSITE_URI` is unset — fail closed.

### Secrets

- Never commit `BACKUP_OFFSITE_URI`, AWS keys, SSH passwords, or tokens.
- Never put them in `/etc/cron.d/karzar-backup`.
- Cron loads env in order: repository `./.env` (if present), then `/opt/karzar/.deploy-secrets` (if present; overrides). Missing `.deploy-secrets` does not fail cron install; offsite sync fails at runtime until the URI is set.

#### S3 / S3-compatible host-secret contract (placeholders only)

```bash
# Required for any offsite destination:
BACKUP_OFFSITE_URI=s3://<bucket>/<prefix>   # or rsync://… / user@host:/path/

# S3-compatible providers (Backblaze B2, Cloudflare R2, Wasabi, etc.):
# endpoint is normally REQUIRED. Native AWS S3: endpoint optional (omit for default).
BACKUP_S3_ENDPOINT_URL=https://<provider-endpoint>
BACKUP_S3_REGION=<region>

# Standard AWS CLI credentials (never commit; never put in cron):
AWS_ACCESS_KEY_ID=<secret>
AWS_SECRET_ACCESS_KEY=<secret>
# optional:
# AWS_SESSION_TOKEN=<secret>
```

- `BACKUP_OFFSITE_URI` and `BACKUP_S3_ENDPOINT_URL` must **never** contain credentials, tokens, query secrets, or fragments (`@`, `?`, `#` are refused for S3 URI/endpoint). Do not silently rewrite; the sync fails closed.
- Credentials belong **only** in standard AWS CLI credential mechanisms (env vars, shared credentials file, or profile) — never on the `aws` process argv via URI/endpoint fields.
- `BACKUP_S3_ENDPOINT_URL` must be `https://` (http refused).
- `--preflight` is **read-only**: no success/failure markers, no lock file, no local retention, no `aws s3 sync`, no upload/delete. For S3 it may run `aws s3api head-bucket` only; for rsync it checks local tooling only.
- aws CLI is a **VPS host prerequisite** for S3 destinations (not an application Python dependency). Install only under Owner-authorized ops.

**Non-binding recommendation:** evaluate Backblaze B2 S3-compatible storage first (lifecycle, server-side encryption, Object Lock/retention). Provider setup remains Owner-side; this repo has no provider-specific SDK or account automation.


### Retention and encryption

- **Local retention:** `BACKUP_RETENTION_DAYS` (default 14) applies only under `./backups/`.
- **Remote retention:** destination-side. `BACKUP_RETENTION_DAYS` does **not** enforce remote retention. Before production activation the Owner must prove remote retention/lifecycle, at-rest encryption, and immutability/Object Lock (or equivalent) read-only — this sync script never mutates bucket lifecycle/Object Lock.
- **rsync `--delete`:** remote tree mirrors the currently retained local set; remote history beyond local retention is removed by that mirror. `--delete` runs before the script’s local retention deletion, so a file removed locally in that same run may remain remotely until the next successful sync.
- **Encryption:** transport and at-rest encryption depend on the destination/configuration (TLS/SSH, bucket SSE, disk encryption). This pipeline does **not** claim encryption-at-rest is solved.

### Media coverage

Offsite source is `<repo>/backups`, which holds both filename families from `backup_db.sh` and `backup_uploads.sh`. Future offsite recovery drills must cover DB **and** media.

On-host `./backups/` alone is **not** disaster recovery. Suggested local keep: 7 daily + 4 weekly. Tiered on-host retention and BuildKit cache hygiene: [`operations/STORAGE_HOUSEKEEPING.md`](operations/STORAGE_HOUSEKEEPING.md) (`scripts/ops/vps_storage_housekeeping.sh`, default dry-run). Cron invokes scripts via `/bin/bash` because artifact download may strip +x.

Restore onto a scratch/staging target first. Suggested RPO ≤ 24h, RTO ≤ 2h.

## Migrations

```bash
docker compose exec app alembic upgrade head
docker compose exec app alembic current
docker compose exec app alembic downgrade -1   # non-prod first
```

Never downgrade production past a column-drop without a backup. Prefer forward-fix migrations.

**Live deploy ↔ migration coupling (current architecture):** the API container
entrypoint (`docker-entrypoint.sh`) always runs `alembic upgrade head` before
starting the server. On the CR-011 live VPS compose stack this means a normal
**live deploy currently cannot be authorized independently of pending schema
migrations**: shipping a new image/tree that includes new Alembic revisions will
apply those revisions on container start. Do not assume “code-only” live deploy
is available without changing that entrypoint (out of scope unless Owner orders
a deliberate split). Review pending revisions before authorizing Deploy Staging.

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
5. Compose on the VPS: `docker compose -f docker-compose.yml -f docker-compose.staging.yml`. Entrypoint runs `alembic upgrade head` (see **Live deploy ↔ migration coupling** above — live deploy applies pending migrations).
6. Smoke: `deploy/staging/scripts/smoke-staging.sh` (`GET /ready`, admin session, checkout against the **configured** provider). Do **not** switch production/staging-live to mock to smoke.
7. Restore `KARZAR_DEPLOY_FREEZE=true` immediately.
8. Watch error rate and `/metrics` for 15 minutes.

### Staging source handoff

**Current (GitHub-hosted SSH delta-rsync — unreliable):** GitHub-hosted checkout is pinned to `github.sha`. That runner builds an isolated deploy tree (tracked files; no `.git` / `.github` / caches / uploads / `.env`), writes `deploy-manifest.sha256`, seeds `/opt/karzar/incoming/<sha>/tree` from the current live trees (`/opt/karzar/Karzar` and `/opt/karzar/frontend`) without mutating them, then delta-rsyncs over IPv4 SSH (`--checksum --delete`, host key pinned in `deploy/staging/ssh/known_hosts`).

`HANDOFF_COMPLETE` is written only after the GitHub-hosted session verifies the staged tree (`sha256sum -c` plus extra/missing/structural checks). GitHub Actions job outputs are NOT used to carry the manifest SHA between the GitHub-hosted handoff job and the self-hosted deploy job (run `34039051081`: Actions suppressed `manifest_sha` as a possible secret). The self-hosted runner reads `HANDOFF_COMPLETE` on the VPS, recomputes `sha256sum` of `deploy-manifest.sha256`, compares that to the marker, then re-runs `sha256sum -c`. It does not pull `github.com`, the GitHub API, `raw.githubusercontent.com`, Actions artifacts, or Azure Blob.

After prepare-mode verify writes `HANDOFF_COMPLETE`, the GitHub-hosted session normalizes read/traverse modes **only** under `/opt/karzar/incoming/<sha>` (`0755` on that directory, `a+rX` on tree directories, `a+r` on tree files, `0644` on the marker and `deploy-manifest.sha256`). It does not chmod live `/opt/karzar/Karzar`, `/opt/karzar/frontend`, or secrets. The private-key `umask 077` applies only to the local SSH keyfile so the manifest is not created as `0600` (run `34040385983`: handoff succeeded, self-hosted consume failed immediately).

Handoff failure (timeout, rsync error, missing marker, manifest mismatch, extra/missing/corrupt file) skips live rsync, rebuild, and container restart. Incoming dirs without `HANDOFF_COMPLETE` are leftover debug state, not a completed handoff.

Incoming handoff is produced and cleaned by `SSH_USER` over IPv4 SSH. The self-hosted runner is read-only with respect to incoming handoff ownership. Cleanup is a GitHub-hosted job that runs only after successful self-hosted verify, live sync, rebuild, and smoke. Failed deploys retain `/opt/karzar/incoming/<sha>` for diagnosis (run `34041875626`: deploy/rebuild/smoke passed, self-hosted `rm -rf` of incoming failed and reddened the workflow).

Scripts: [`deploy/staging/scripts/push-incoming-source.sh`](../deploy/staging/scripts/push-incoming-source.sh), [`deploy/staging/scripts/verify-incoming-source.sh`](../deploy/staging/scripts/verify-incoming-source.sh), [`deploy/staging/scripts/deploy-tree-lib.sh`](../deploy/staging/scripts/deploy-tree-lib.sh), [`deploy/staging/scripts/cleanup-incoming-source.sh`](../deploy/staging/scripts/cleanup-incoming-source.sh). Local selftest: `bash deploy/staging/scripts/test-delta-rsync-handoff.sh` and `bash deploy/staging/scripts/cleanup-incoming-source.sh --selftest`. Historical collaborator copy: [`archive/docs/COLLABORATOR_DEPLOY.md`](archive/docs/COLLABORATOR_DEPLOY.md).

**Phase 1 (self-hosted local package — prep + dry-run only; does not cut over Deploy Staging):** Package preparation can run on the `[self-hosted, karzar-vps]` runner without GitHub→VPS SSH. Host dirs `/opt/karzar/{incoming,workspace,mirror,logs/deploy}` are owned by `github-runner:github-runner` (one-time `prepare-self-hosted-dirs.sh` as root). A bare mirror at `/opt/karzar/mirror/Karzar.git` (public HTTPS fetch; no deploy key) is SHA-addressable. `package-incoming-local.sh` checks out the target SHA into workspace, copies tracked files, writes `deploy-manifest.sha256` + `HANDOFF_COMPLETE` with `transport=local-package`, and stages `/opt/karzar/incoming/<sha>`. Dry-run (`KARZAR_PACKAGE_DRY_RUN=1`) skips docker/frontend image build and never touches live trees, compose, or alembic. Workflow: **Deploy Staging Self-Hosted Package Dry-Run** (`.github/workflows/deploy-staging-self-hosted-package-dry-run.yml`). Local selftest: `bash deploy/staging/scripts/test-package-incoming-local.sh`. Scripts: [`prepare-self-hosted-dirs.sh`](../deploy/staging/scripts/prepare-self-hosted-dirs.sh), [`ensure-git-mirror.sh`](../deploy/staging/scripts/ensure-git-mirror.sh), [`package-incoming-local.sh`](../deploy/staging/scripts/package-incoming-local.sh), [`dry-run-self-hosted-package.sh`](../deploy/staging/scripts/dry-run-self-hosted-package.sh).

Production image rollback: revert the container image / previous env. **Never** set `PAYMENT_PROVIDER=mock` on production (boot validators reject it).

`KARZAR_DEPLOY_FREEZE=true` also blocks `apply` mode on live taxonomy workflows; dry-runs remain available.

## Incidents

| Severity | Examples | Actions |
|----------|----------|---------|
| SEV1 | API down, payment verify failing | Roll back image; restore DB only if schema is broken; notify gateway |
| SEV2 | Elevated 5xx, Redis down | Check `/ready`; degrade throttles if needed |
| SEV3 | Single endpoint | Env flag / hotfix / forward migration |

Capture `request-id` from headers/logs. Roll back image before rolling back the database.
