# Operations runbook — backup, restore, environments, observability

## External blockers / compensating controls (Wave B)

Items below are **not** fully automated until external accounts or infrastructure exist. Enable each when the corresponding secret or service is available — do not invent credentials.

| Blocker | Env var(s) | Compensating control today | Enable when |
|---------|------------|---------------------------|-------------|
| Off-host backups | `BACKUP_OFFSITE_URI`, `BACKUP_LOCAL_DIR` | On-host `./backups/` only; daily cron via `install-backup-cron.sh` | S3/R2 bucket + IAM key on VPS; run `scripts/backup_offsite_sync.sh` after each dump |
| Error tracking | `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE` | Watch container logs + `/metrics` for 15 min post-deploy | Create Sentry project; `pip install sentry-sdk`; set DSN in server secrets |
| Uptime monitoring | `UPTIME_CHECK_URL` (doc only) | Manual smoke + `smoke-staging.sh` on deploy | Point UptimeRobot/Better Stack at `GET /health` and `GET /ready` on API host |
| Single-host staging | — (honesty) | Staging + production workflows target **same VPS** (`karzartools.com`); shared `deploy-live` concurrency | Split hosts before treating production as isolated |
| Live payment | `PAYMENT_PROVIDER=zarinpal`, `ZARINPAL_MERCHANT_ID` | `PAYMENT_PROVIDER=mock` on staging; Zarinpal **sandbox** for L2 QA | Merchant ID + callback URL registered; see `deploy/staging/PROVIDERS_LATER.md` |
| Metrics scrape auth | `METRICS_SCRAPE_TOKEN` | Nginx restricts `/metrics` to loopback (`127.0.0.1`) | Set token on API + pass `X-Metrics-Token` header from host-local scraper |
| Redis AUTH | `REDIS_PASSWORD` | Redis on loopback only (`127.0.0.1:6379`); no password in dev | Set password in `.env` / server secrets; compose starts `redis-server --requirepass` |

## GitHub Actions self-hosted runner (OPS-03)

Deploy workflows package on `ubuntu-latest`, then run on the VPS self-hosted runner (`karzar-vps`). If GitHub-hosted jobs fail but the server is healthy, deploy manually:

1. `git pull` (or rsync artifact) into `/opt/karzar/Karzar` and `/opt/karzar/frontend`.
2. `bash deploy/staging/scripts/deploy-backend.sh`
3. Export `FRONTEND_ROOT`, `NEXT_PUBLIC_API_BASE_URL`, `ADMIN_SESSION_SECRET`; run `deploy-frontend.sh`.
4. `bash deploy/staging/scripts/smoke-staging.sh`

**Runner service:** install the runner under `actions-runner/` with a **systemd unit** using `Restart=always` and `RestartSec=10` so transient network blips do not leave deploys blocked. After reboot, confirm `systemctl status actions.runner.*` is active before relying on CI deploy.

## Frontend build-time environment (OPS-21)

Next.js bundles are a function of **commit + build args** — never patch sources at deploy time.

| Variable | App | Required | Notes |
|----------|-----|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | Storefront, Admin | Yes | e.g. `https://api.karzartools.com/api/v1` |
| `NEXT_PUBLIC_USE_MOCK` | Storefront, Admin | No (default `false`) | `true` only for offline dev/CI e2e |
| `NEXT_PUBLIC_ASSET_BASE_URL` | Storefront | No | Optional CDN/origin; `next.config.ts` reads at build time |
| `ADMIN_SESSION_SECRET` | Admin runtime | Yes (deploy) | Min 32 chars; **not** baked into bundle — Docker `-e` at run |

`next.config.ts` derives `images.remotePatterns` from `NEXT_PUBLIC_API_BASE_URL` / `NEXT_PUBLIC_ASSET_BASE_URL` at build time.

## Environments

| Env | `APP_ENV` | Compose files | Notes |
|-----|-----------|---------------|-------|
| Development | `development` | `docker-compose.yml` + `docker-compose.dev.yml` | Bind-mount source, OTP echo OK when `DEBUG=true` |
| Staging | `staging` | `docker-compose.yml` + `docker-compose.staging.yml` | No bind mount, `DEBUG=false`, HTTPS enforced |
| Production | `production` | `docker-compose.yml` (+ secrets manager) | Redis required, mock payment forbidden |

Copy templates:
- `.env.example` — local/dev baseline
- `.env.staging.example` — staging checklist

## Networking

Compose uses a bridge network (`karzar`). Inside containers:

- Postgres host: `db:5432`
- Redis host: `redis:6379`

Host-mapped ports for local tools (bound to loopback — not exposed on LAN):

- API `127.0.0.1:8000`
- Postgres `127.0.0.1:5435`
- Redis `127.0.0.1:6379`

## Logging

- Console logs always enabled.
- File logs: `LOG_TO_FILE=true`, path `LOG_FILE` (default `logs/app.log`), rotating 10×10MB.
- Compose mounts named volume `karzar_logs` → `/app/logs`.

## Metrics

When `ENABLE_METRICS=true`, scrape:

```
GET /metrics
```

**Access control (defence in depth):**

1. Nginx staging template restricts `/metrics` to loopback (`allow 127.0.0.1; deny all`). Scrape from the host or a private agent only — never expose publicly.
2. When `METRICS_SCRAPE_TOKEN` is set, the API requires header `X-Metrics-Token` with the same value. If the token is unset, rely on the Nginx ACL as the compensating control.

Example host-local scrape:

```bash
curl -fsS -H "X-Metrics-Token: $METRICS_SCRAPE_TOKEN" http://127.0.0.1:8000/metrics
```

Health probes:

```
GET /health   # liveness
GET /ready    # DB + Redis readiness
```

## Alerting hooks (OPS-07)

Until external accounts exist, treat these as **documented compensating controls**:

| Hook | Env | Status |
|------|-----|--------|
| Sentry errors/traces | `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE` | Soft-init in `app/main.py` when DSN set and `sentry-sdk` installed (`pip install sentry-sdk`) |
| Uptime monitor | `UPTIME_CHECK_URL` (documentation only) | Point UptimeRobot/Better Stack at `GET /health` and `GET /ready` on API host |
| Deploy smoke | `deploy/staging/scripts/smoke-staging.sh` | Hard gate in staging/production deploy workflows |

Compensating until Sentry/uptime are live: watch `/metrics` + container logs for 15 minutes after every deploy; SEV1 path in the incident table below.

## Backup / restore (PostgreSQL)

### Backup

```bash
# From host (port 5435) or via compose exec
./scripts/backup_db.sh
```

Artifacts land in `./backups/` as `karzar_YYYYMMDD_HHMMSS.sql.gz`.

Retention suggestion: keep 7 daily + 4 weekly dumps off-host (S3/object storage).

### Restore

```bash
./scripts/restore_db.sh backups/karzar_YYYYMMDD_HHMMSS.sql.gz
```

Always restore onto staging first and run `pytest` / smoke checkout before production.

### Disaster recovery targets (suggested)

- RPO: ≤ 24h (daily dump)
- RTO: ≤ 2h (restore + migrate + smoke)

## Hesabfa (حسابفا)

See [HESABFA.md](./HESABFA.md) for env vars, SKU matching, site→Hesabfa item push (qty 0), and invoice-after-payment hook.

**Inventory:** warehouse counts live **only in Hesabfa**. The site stores `is_available` (موجود/ناموجود) and never pulls `GetQuantity`.

**Admin:** do not display Hesabfa-sourced metrics (`HESABFA_ADMIN_READS_ENABLED=false`). Keep invoice-after-payment + site→Hesabfa item push.

On VPS, put `HESABFA_API_KEY` / `HESABFA_LOGIN_TOKEN` only in the API container secrets — never in git.

## Migrations

```bash
docker compose exec app alembic upgrade head
```

### Rollback (one revision)

```bash
# Inspect current revision
docker compose exec app alembic current

# Downgrade one step (staging first!)
docker compose exec app alembic downgrade -1

# Re-apply after fix
docker compose exec app alembic upgrade head
```

Never downgrade production past a migration that dropped columns without a backup. Prefer forward-fix migrations.

## Deploy checklist

1. Merge to `main`; CI must pass (lint + pytest + coverage ≥ 70%).
2. Tag release in [API_CHANGELOG.md](API_CHANGELOG.md) if contract changed.
3. **Staging on VPS:** follow [deploy/staging/STAGING_DEPLOY.md](../deploy/staging/STAGING_DEPLOY.md)
   (`docker compose -f docker-compose.yml -f docker-compose.staging.yml`).
4. Run `alembic upgrade head` on staging (entrypoint does this on boot).
5. Smoke: `GET /ready`, checkout mock payment, admin login
   (`deploy/staging/scripts/smoke-staging.sh`).
6. Production: same compose profile with secrets from vault (not `.env` in repo);
   see [deploy/staging/PROVIDERS_LATER.md](../deploy/staging/PROVIDERS_LATER.md) before enabling live payment/SMS.
7. Post-deploy: watch error rate and `/metrics` for 15 minutes.

## Incident response (suggested)

| Severity | Examples | Actions |
|----------|----------|---------|
| SEV1 | API down, payment verify failing | Roll back container image; restore DB if schema broken; notify gateway |
| SEV2 | Elevated 5xx, Redis unavailable | Scale Redis; fall back to in-memory throttles (degraded); check `GET /ready` |
| SEV3 | Single endpoint regression | Feature flag via env; hotfix branch; forward migration |

1. Capture request-id from response header / logs.
2. Check `GET /health` and `GET /ready`.
3. Recent deploy? Roll back image before DB rollback.
4. DB corruption? Restore latest `backups/*.sql.gz` to staging, validate, then production.
5. Document timeline and root cause in issue tracker; update runbook if gap found.

## Uploads

Product image uploads persist in volume `karzar_uploads` (`/app/data/uploads`).

### Backup

```bash
./scripts/backup_uploads.sh
```

Artifacts land in `./backups/` as `karzar_uploads_YYYYMMDD_HHMMSS.tar.gz`.

Daily cron (with DB): `sudo bash deploy/staging/scripts/install-backup-cron.sh`

### Restore

```bash
./scripts/restore_uploads.sh backups/karzar_uploads_YYYYMMDD_HHMMSS.tar.gz
```

### Off-host requirement (OPS-02 / Phase 0)

On-host `./backups/` is **not** disaster recovery. After each dump/archive, sync to off-host storage:

```bash
# Set in server secrets (never commit):
#   BACKUP_OFFSITE_URI=s3://your-bucket/karzar/
#   BACKUP_LOCAL_DIR=/opt/karzar/backups
sudo bash scripts/backup_offsite_sync.sh
```

Wire into cron after `install-backup-cron.sh` (append the sync job). Retention suggestion: 7 daily + 4 weekly off-host.

### Restore drill checklist

Document results under `docs/roadmap/phase-0-execution-log.md` after running once on a scratch/staging target:

1. Take fresh `backup_db.sh` + `backup_uploads.sh`
2. Restore DB into scratch DB (or staging scratch)
3. Restore uploads into scratch volume/path
4. Hit `GET /ready` and spot-check one product image URL
5. Record wall-clock time, gaps, owner (`shebahati`)

## Wave B — external wiring (when secrets arrive)

Code and docs are ready; **do not claim Done** until secrets are on the VPS and a drill/alert is proven.

| ID | You provide | Wire-up steps |
|----|-------------|---------------|
| OPS-02 | `BACKUP_OFFSITE_URI` + S3/R2 keys | Set env on VPS; confirm `backup_offsite_sync.sh` exits 0; run restore drill checklist above once |
| OPS-07 Sentry | Project DSN | Set `SENTRY_DSN` (+ optional `SENTRY_TRACES_SAMPLE_RATE`); `pip`/`requirements` already soft-init; verify one test error in Sentry |
| OPS-07 Uptime | Monitor URL | Point UptimeRobot/Better Stack at `GET /health` and `GET /ready`; store URL in `UPTIME_CHECK_URL` for operators |
| OPS-01 | Second host/DB **or** written single-host acceptance | If accepted: keep `deploy-live` concurrency + honesty comments; if second host: split compose/env and rename workflows |
| SEC-09 | Rotate any chat-transited passwords/tokens | Operator-only; update password manager + VPS `.env` |
| BE-31 | Zarinpal sandbox merchant | Set `PAYMENT_PROVIDER=zarinpal`, sandbox URLs + merchant id; run live verify once |

Until then, compensating controls in this file remain the honest scorecard posture.

