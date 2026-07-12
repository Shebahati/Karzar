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

## Uploads

Product image uploads persist in volume `karzar_uploads` (`/app/data/uploads`). Include this volume in backup policy if uploads are not on CDN.
