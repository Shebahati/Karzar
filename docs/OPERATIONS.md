# Operations runbook — backup, restore, environments, observability

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

Host-mapped ports for local tools:

- API `8000`
- Postgres `5435`
- Redis `6379`

## Logging

- Console logs always enabled.
- File logs: `LOG_TO_FILE=true`, path `LOG_FILE` (default `logs/app.log`), rotating 10×10MB.
- Compose mounts named volume `karzar_logs` → `/app/logs`.

## Metrics

When `ENABLE_METRICS=true`, scrape:

```
GET /metrics
```

Health probes:

```
GET /health   # liveness
GET /ready    # DB + Redis readiness
```

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

1. Merge to `main`; CI must pass (lint + pytest + coverage ≥ 62%).
2. Tag release in [API_CHANGELOG.md](API_CHANGELOG.md) if contract changed.
3. Staging: `docker compose -f docker-compose.yml -f docker-compose.staging.yml pull && up -d`
4. Run `alembic upgrade head` on staging.
5. Smoke: `GET /ready`, checkout mock payment, admin login.
6. Production: same compose profile with secrets from vault (not `.env` in repo).
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

Product image uploads persist in volume `karzar_uploads` (`/app/data/uploads`). Include this volume in backup policy if uploads are not on CDN.
