# Catalog staging isolation

Status: **isolated Compose project + fail-closed data-plane guards** (provision on a non-live host / additive stack only).  
Related: `CR-011` (current live topology), ADR-012 (ingestion boundary), `docs/OPERATIONS.md`.

## CRITICAL NAMING WARNING (CR-011)

The existing **CR-011 live** environment historically uses:

```text
APP_ENV=staging
database=karzar_staging
container=lathe_postgres
volume=karzar_postgres_data (Compose) / karzar_karzar_uploads
public API=api.karzartools.com
```

**These names DO NOT make it a staging environment.**

```text
ENVIRONMENT_ROLE = PRODUCTION
LEGACY_LABEL = staging
```

Treat CR-011 live as Production for all catalog safety decisions. Never use it as a rehearsal target for ZCC APPLY.

## CURRENT UNSAFE STATE

The process label `APP_ENV=staging` does **not** isolate data.

```text
Internet
   ↓
Nginx (api.karzartools.com / www.karzartools.com)
   ↓
Compose project (docker-compose.yml + docker-compose.staging.yml)
   ├── lathe_api          APP_ENV=staging  (label only)
   ├── lathe_postgres     volume: postgres_data
   │                      DB name: karzar_staging  ← LIVE catalog
   ├── lathe_redis
   └── volumes
        ├── postgres_data     ← LIVE
        ├── karzar_uploads    ← LIVE media
        └── karzar_logs
```

| What the repo calls it | What it actually is |
| ---------------------- | ------------------- |
| “staging” compose      | Live public VPS runtime |
| `APP_ENV=staging`      | Gunicorn/HTTPS/OTP hardening label |
| `POSTGRES_DB=karzar_staging` | **Live** catalog database (historic name) |

Shared today: production VPS, PostgreSQL volume/DB, uploads volume, API serving `api.karzartools.com`.

## TARGET ARCHITECTURE

Two distinct data planes:

| Plane | Purpose | Compose | DB name (default) | Uploads volume |
| ----- | ------- | ------- | ----------------- | -------------- |
| `live` | Public storefront / Category B | `docker-compose.yml` + `docker-compose.staging.yml` | `karzar_staging` (historic) | `karzar_uploads` |
| `catalog_staging` | Catalog rehearsal only | `docker-compose.catalog-staging.yml` | `karzar_catalog_staging` | `catalog_staging_uploads` |
| `development` | Local Category A | `docker-compose.yml` + `docker-compose.dev.yml` | local | local bind/volume |

### Database design (selected)

**Separate Compose-managed PostgreSQL service + volume** for catalog staging (not a second database on the live Postgres data directory).

Tradeoffs:

- Stronger isolation (independent storage, credentials, network, container identity).
- Slightly more disk/ops than `CREATE DATABASE` on live Postgres.
- Avoids accidental `DROP`/`TRUNCATE` on a shared cluster and volume-name collisions.

### Media

Dedicated volume `karzar_catalog_staging_uploads`. Staging must never mount `karzar_uploads`.

### API runtime

Independently addressable on loopback by default (`127.0.0.1:8010`). Hostname/`TRUSTED_HOSTS`/`PUBLIC_ASSET_BASE` are configurable — this PR does **not** register DNS.

### Migrations / catalog writers

Both resolve destination via Settings / env. Guards require `KARZAR_DATA_PLANE=catalog_staging` ⇒ `POSTGRES_DB=karzar_catalog_staging` and refuse live denylist names (includes `karzar_staging`).

## RESOURCE ISOLATION

| Resource | Live | Catalog staging |
| -------- | ---- | --------------- |
| Compose project | default / historic | `name: karzar_catalog_staging` |
| API container | `lathe_api` | `karzar_catalog_staging_api` |
| DB container | `lathe_postgres` | `karzar_catalog_staging_db` |
| Network | `karzar` | `karzar_catalog_staging_net` |
| Postgres volume | `postgres_data` | `karzar_catalog_staging_postgres_data` |
| Uploads volume | `karzar_uploads` | `karzar_catalog_staging_uploads` |
| Loopback API port | `127.0.0.1:8000` | `127.0.0.1:8010` |
| Loopback DB port | `127.0.0.1:5435` | `127.0.0.1:5436` |

## WRITE GUARDS

Identity is **`KARZAR_DATA_PLANE`**, not `APP_ENV`.

| Setting | Production / live source | Catalog staging source | Isolated? | Risk if ignored |
| ------- | ------------------------ | ---------------------- | --------- | --------------- |
| `APP_ENV` | `staging` or `production` | `staging` | No (label) | False sense of safety |
| `KARZAR_DATA_PLANE` | `live` (default when unset + non-dev) | `catalog_staging` | Yes | Mis-aimed APPLY |
| `POSTGRES_DB` | `karzar_staging` | `karzar_catalog_staging` | Yes | Live catalog mutation |
| Uploads volume | `karzar_uploads` | `catalog_staging_uploads` | Yes | Live media overwrite |
| API host | `api.karzartools.com` | configurable / `:8010` | Yes | ADR-012 + plane guard |
| ADR-012 Category B | required for prod host | **forbidden** when plane=`catalog_staging` | Yes | Cross-plane API write |

Threat case (must fail):

```text
APP_ENV=staging
KARZAR_DATA_PLANE=catalog_staging
POSTGRES_DB=karzar_staging   # live name
→ API/Settings/Alembic/assert refuse to start
```

Implementation:

- `app/core/data_plane.py` — pure validation
- `app/core/config.py` — Settings fail-closed on boot
- `alembic/env.py` — prints non-secret identity before migrate
- `scripts/ingestion_boundary.py` — plane-aware API destination + helpers
- `scripts/assert_catalog_data_plane.py` / `print_catalog_env_identity.py`

### Catalog writer matrix (current)

| Writer class | Environment guard | DB identity guard | Dry-run | Risk |
| ------------ | ----------------- | ----------------- | ------- | ---- |
| Scripts using `resolve_api_base()` | ADR-012 + catalog_staging≠prod host | When `KARZAR_DATA_PLANE` / `POSTGRES_DB` set | Varies by script | Medium→low for API path |
| Direct `DATABASE_URL` / `POSTGRES_*` APPLY | Historically weak | Call `assert_catalog_mutate_destination()` (follow-up wire-up) | Often `--dry-run` | **High** until wired |
| Hesabfa sync | Feature flags | Live plane | N/A | Keep disabled on catalog staging |
| Category B APPLY | ADR-012 dual flag | Live only by design | Policy | Owner-gated |

Follow-up (out of scope if too broad): call `assert_catalog_mutate_destination()` at the top of every direct-DB APPLY entrypoint. Prefer API writers pointed at `:8010` for rehearsals.

## DATA SEEDING POLICY

Full DB dumps include users, orders, payments, OTP/session artifacts — **do not** blindly restore into catalog staging.

Recommended catalog-only path (design only — not executed here):

1. **SOURCE** — live read replica or one-off `pg_dump` with table allowlist (Owner-authorized).
2. **EXPORT** — products, product images metadata, brands, categories, and other catalog taxonomy tables required for PLP/PDP validation. Exclude `users`, `orders`, `payments`, refresh/OTP tables, admin audit secrets.
3. **SANITIZATION** — strip PII; replace admin credentials with staging-only bootstrap; disable payment/Hesabfa/Postex secrets.
4. **RESTORE** — into `karzar_catalog_staging` only after `assert_catalog_data_plane.py --expect catalog_staging`.
5. **VALIDATION** — row counts for catalog tables; zero rows in customer/order tables (or empty stubs); identity report shows catalog_staging.

If a full snapshot is unavoidable, sanitize before any network exposure and rotate all secrets afterward.

## MEDIA POLICY

Options:

| Option | Use |
| ------ | --- |
| Isolated copy of selected product media | Preferred for visual QA |
| Empty uploads + regenerate via materialize scripts against staging API | Fine for schema/APPLY drills |
| Read-only bind of live uploads | **Forbidden** (delete/overwrite risk) |

Staging must never delete or overwrite production uploads. Do not mount `karzar_uploads` into the catalog-staging API container.

## DEPLOYMENT PROCEDURE (document only — do not execute)

1. **Provision** isolated host resources (or clearly separated Compose project on a non-conflicting host). Prefer not sharing the live Docker volume namespace without Owner review.
2. **Configure secrets** from `.env.catalog-staging.example` → host-only `.env.catalog-staging` (never commit).
3. **Start staging DB/storage** — `docker compose -f docker-compose.catalog-staging.yml --env-file .env.catalog-staging up -d db redis`.
4. **Run staging migrations** — start `app` (entrypoint runs Alembic) or `alembic upgrade head` with catalog-staging env; confirm printed identity.
5. **Seed** sanitized/catalog-only data (policy above).
6. **Start staging API** — full compose up; smoke `GET /ready` on `:8010`.
7. **Prove isolation** — see Validation.
8. **Read-only verification** — catalog GETs only.
9. **Catalog rehearsal** — Category A against staging API only; no live Category B.

### Rollback

| Step | Rollback |
| ---- | -------- |
| Compose up | `docker compose -f docker-compose.catalog-staging.yml down` (does not touch live project) |
| Volume wipe | Only remove `karzar_catalog_staging_*` volumes — never `postgres_data` / `karzar_uploads` |
| Bad seed | Drop/recreate **catalog staging** DB only |
| Accidental live touch | Stop; restore from live backup; treat as incident |

## VALIDATION

Operator identity (no secrets):

```bash
python scripts/print_catalog_env_identity.py
# APP ENV / DB ENV / DB NAME / MEDIA ENV / WRITE POLICY
```

Assert plane:

```bash
python scripts/assert_catalog_data_plane.py --expect catalog_staging
python scripts/assert_catalog_data_plane.py --expect catalog_staging --allow-mutate
```

Isolation proofs:

```text
staging DB name != karzar_staging
staging volume != postgres_data / karzar_uploads
staging API port/container != lathe_api / :8000 public path
docker volume ls | grep catalog_staging
docker ps --filter name=karzar_catalog_staging
```

## How to start / stop (local / authorized host)

```bash
cp .env.catalog-staging.example .env.catalog-staging   # fill secrets
docker compose -f docker-compose.catalog-staging.yml --env-file .env.catalog-staging up -d --build
docker compose -f docker-compose.catalog-staging.yml --env-file .env.catalog-staging down
```

Do **not** run these against the live public VPS without Owner deployment authorization.

## PRODUCTION NON-REGRESSION

- Live compose files keep historic volume/container names.
- Unset `KARZAR_DATA_PLANE` with `APP_ENV=staging` still infers `live` (CR-011 compatible).
- No production secrets in git; examples use placeholders only.
- Storefront code paths unchanged; catalog data untouched by this PR.

## Environment identity sentinel

Alembic revision `l5m6n7o8p9q0` adds table `environment_identity` (singleton row `id=1`).

| Plane value | Meaning |
| ----------- | ------- |
| `live` | Default after migration / CR-011 live |
| `catalog_staging` | Set only by `scripts/bootstrap_catalog_staging_identity.sh` on the isolated DB |
| `development` | Local optional |

Catalog writers that declare `KARZAR_DATA_PLANE=catalog_staging` must also see `environment_identity.plane=catalog_staging` (`assert_db_sentinel_matches_plane`).

## Catalog-only seed (no PII)

Allowlist tables:

```text
brands
categories
product_types
products
product_images
```

Excluded: users, orders, payments, OTP/refresh tokens, shipments, carts, admin audit, Hesabfa mappings, etc.

```bash
# 1) read-only export from live (hashes under /tmp — do not commit)
bash scripts/catalog_staging_export_live_catalog_readonly.sh /tmp/catalog-seed-$TS

# 2) restore into isolated catalog-staging only
export KARZAR_DATA_PLANE=catalog_staging
# POSTGRES_* must target 127.0.0.1:5436 / karzar_catalog_staging
bash scripts/catalog_staging_seed_restore.sh /tmp/catalog-seed-$TS/catalog_only.dump
```

## Catalog rehearsal prohibition

Do **not** run ZCC Production APPLY against CR-011 live until Owner authorization **and** isolated staging rehearsal succeeds. The Production create preflight manifest is plan-only.
