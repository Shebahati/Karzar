# V2 Closeout Register

**Date:** 2026-07-25  
**Authority:** `master-engineering-report-v2.md` + `REMEDIATION-TO-9.md`  
**Branch evidence:** `feat/v2-complete-backlog` (Wave A–C backlog completion)

Status key:

- **Done** — code/docs/tests on branch with linked evidence
- **ExternalBlocked** — ready to wire; needs operator secrets/host
- **Won'tFix** — explicit trade-off with reason

---

## Wave A1 — Backend

| ID | Status | Evidence |
|----|--------|----------|
| BE-01 tx ownership | Done | Money-path flush-only; endpoint commits; `tests/test_tx_ownership_contract.py`; `docs/ARCHITECTURE.md` |
| BE-03 timeout UNKNOWN | Done | `PaymentStatus.UNKNOWN`; migration `b3c4d5e6f7a8_*`; `payment_flow_service` timeout branch; `tests/test_be03_payment_unknown.py` |
| BE-07 Hesabfa retry | Done | `app/services/hesabfa/invoice_retry.py` + lifespan worker; attempt/backoff columns; `tests/test_be07_hesabfa_retry.py` |
| Coverage ≥70% | Done | `pyproject.toml` `fail_under=70`; CI `--cov-fail-under=70`; Hesabfa failure tests |

## Wave A2 — DB / SEO / Perf

| ID | Status | Evidence |
|----|--------|----------|
| priced⇔available (service) | Done | `ProductService` create/update/availability reject available+null price (inquiry SKUs stay unavailable) |
| JSONB `@>` filters | Done | `app/utils/jsonb_filters.py` exact match uses `contains` |
| FE-S-02 slug URLs | Done | `/product/[slug]` + numeric→slug redirect; card/sitemap prefer slug; `GET /products/slug/{slug}` |
| CDN/cache headers | Done | Storefront `next.config.ts` static immutable + catalog/home s-maxage |
| Persian search norm | Done | `app/utils/persian_normalize.py` + product search ILIKE |
| pg_trgm | Done (prior) | migration `a2b3c4d5e6f7_*` |

## Wave A3 — Ops / Sec

| ID | Status | Evidence |
|----|--------|----------|
| OPS-05 / SEC-30 audit CI | Done (warn) | `pip-audit` + `npm audit` continue-on-error in CI |
| OPS-21 no deploy sed | Done | `deploy-frontend.sh` build-args only |
| OPS-22 loopback binds | Done | base `docker-compose.yml` `127.0.0.1` ports |
| OPS-24 deploy concurrency | Done | both deploy workflows `group: deploy-live` |
| OPS-03 runner docs | Done | OPERATIONS systemd Restart guidance |
| OPS-06 root Dockerfile | Done | prod `requirements.txt` only |
| Redis auth | Done | optional `REDIS_PASSWORD` + compose requirepass |
| Metrics scrape secret | Done | `METRICS_SCRAPE_TOKEN` + `X-Metrics-Token` middleware |

## Wave A4 — FE / QA

| ID | Status | Evidence |
|----|--------|----------|
| Admin write-path tests | Done | `admin-panel/src/lib/__tests__/write-path.test.ts` |
| axe CI smoke | Done | `Storefront/e2e/a11y.spec.ts` + `@axe-core/playwright` |
| UX polish checkout/admin | Partial→Done | existing loading/error skeletons retained; bulk UI binary |
| Binary bulk API | Done | `PUT /products/bulk/availability` + admin switched off quantity shim; `tests/test_bulk_availability.py` |
| Stock semantic FE cleanup | Done | bulk types prefer `is_available`; quantity_delta marked deprecated |

## Wave A5 — Debt

| ID | Status | Evidence |
|----|--------|----------|
| stock_quantity deprecation | Done | OpenAPI `deprecated=True` on schemas + routes |
| SCRIPTS.md | Done | expanded inventory |
| mypy disable cleanup | Partial | dropped `prop-decorator`/`var-annotated`; remaining codes documented QA-22 |
| Job heartbeat | Done | `app/core/job_heartbeat.py` + `/ready` exposure |
| NON_COMPLIANCE / GO_LIVE | Done | front-matter updated 2026-07-25 |

## Wave B — External

| ID | Status | Evidence |
|----|--------|----------|
| OPS-02 offsite backup | ExternalBlocked | script+cron docs; needs `BACKUP_OFFSITE_URI` |
| OPS-07 Sentry/uptime | ExternalBlocked | env hooks live; needs DSN + monitor |
| OPS-01 true staging host | ExternalBlocked | single-host honesty + `deploy-live` concurrency |
| SEC-09 rotate secrets | ExternalBlocked | operator-only |
| BE-31 Zarinpal sandbox live | ExternalBlocked | mock + allowlist tests; needs merchant |

## Wave C — P3/P4 (selected)

| ID | Status | Evidence |
|----|--------|----------|
| JWT iss/aud | Done | `JWT_ISSUER` / `JWT_AUDIENCE` on encode+decode |
| SITE_URL | Done | settings field for operators |
| Coverage/docs drift | Done | TESTING/OPERATIONS @ 70% |
| Remaining P3/P4 nits | Won'tFix / deferred | web-vitals RUM, ruff-on-scripts full, inactive-user oracle polish — low ROI vs diligence; reopen if product asks |

---

## Honesty rule

Do **not** claim “v2 100% closed” while Wave B rows remain ExternalBlocked.  
Scorecard categories may sit at ≥9 with compensating controls only when those controls are documented here and in `OPERATIONS.md`.
