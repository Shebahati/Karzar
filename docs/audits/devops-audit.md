# Phase 7 — DevOps, Infrastructure & Operations Audit

**Date:** 2026-07-25 · **Auditors:** DevOps Engineer, Site Reliability Engineer, Security Engineer
**Scope:** Dockerfile, 4 compose files, 3 GitHub Actions workflows, `deploy/staging/*` scripts, backup strategy, observability, runner topology.

---

## 1. What is genuinely good (verified)

1. **Container hygiene:** multi-stage build, non-root `appuser`, slim base,
   `HEALTHCHECK` against `/ready` (which truly checks DB+Redis), migrations
   applied by entrypoint before serving.
2. **Network exposure is disciplined:** staging compose overrides all ports to
   `127.0.0.1` binds — Postgres and Redis are **not** publicly reachable; only
   nginx fronts traffic.
3. **Self-hosted runner threat model is understood:** deploy workflow refuses
   fork PRs explicitly ("never trust fork workflows on self-hosted"),
   checkout happens on GitHub-hosted runners with artifact handoff to the VPS
   runner (also a clever workaround for VPS→GitHub 504s), concurrency group
   prevents overlapping deploys.
4. **Operations are scripted, not tribal:** `bootstrap-vps.sh`,
   `deploy-backend.sh`, `smoke-staging.sh`, `restore-db-staging.sh`,
   `enable-hsts.sh`, `install-backup-cron.sh` (daily DB 03:15 + uploads 03:30
   UTC), documented in `docs/OPERATIONS.md` and `STAGING_DEPLOY.md`.
5. **CI is a real gate for the backend:** ruff + mypy + pytest with
   `--cov-fail-under=62` enforced, path-filtered to avoid wasted runs.

## 2. Findings

### OPS-01 — "Staging" is production
- **Severity:** High · **Category:** Environment topology · **Location:** `deploy-staging.yml` header: *"Staging = live VPS serving karzartools.com (single host until prod is split)"*
- **Evidence:** The workflow named *staging* deploys the live customer-facing site on push to `main`. There is no pre-production environment; `deploy-production.yml` exists but targets the same reality.
- **Why problematic:** Every merged PR goes straight to customers with no human-visible staging soak. This week's admin typecheck failure and availability regression reached the live site because there is nowhere else for them to go. The naming also creates decision errors ("it's only staging").
- **Root cause:** Single-VPS budget; honest comment, misleading name.
- **Recommendation:** Near-term: rename workflow/host references to `deploy-live` so intent is explicit, and add a required smoke-test job (`smoke-staging.sh` already exists — wire it as a post-deploy gate with rollback on failure). Mid-term: a second cheap VPS or docker-compose "staging" stack on a different port with its own DB for pre-live verification.
- **Effort:** S (rename+smoke gate) / M (real staging) · **Priority:** P1

### OPS-02 — Backups live on the same disk they protect
- **Severity:** High · **Category:** Disaster recovery · **Location:** `install-backup-cron.sh` (`BACKUP_DIR="$ROOT_DIR/backups"`)
- **Evidence:** Daily `pg_dump` and uploads archives are written to the VPS's own filesystem. No offsite copy, no retention policy visible, no restore drill cadence.
- **Why problematic:** Disk failure, ransomware, or `rm -rf` mistakes destroy the data *and* every backup simultaneously. This is the single largest business-continuity risk in the platform.
- **Recommendation:** Sync `backups/` nightly to object storage (Arvan/S3-compatible in-country, or even a second VPS via restic/rclone with encryption); add retention (7 daily / 4 weekly); document and *rehearse* restore using the existing `restore-db-staging.sh`.
- **Effort:** S · **Priority:** P0

### OPS-03 — Runner is a single point of deploy failure with no health alerting
- **Severity:** Medium · **Category:** CI/CD reliability · **Evidence:** The `karzar-vps` self-hosted runner went offline this week and silently queued deploys for hours; discovery was manual.
- **Recommendation:** systemd unit with `Restart=always` for the runner (verify), plus a cron heartbeat that alerts (Telegram/SMS) when `Runners` API reports offline; document the manual deploy fallback path (`deploy-backend.sh` run directly on VPS).
- **Effort:** S · **Priority:** P1

### OPS-04 — No frontend gate in PR CI
- **Severity:** Medium · **Category:** CI · **Location:** `.github/workflows/backend-ci.yml` (backend-only jobs; frontend-only changes skip through by design)
- **Evidence:** Frontend `tsc --noEmit`/`next build` runs only at deploy time; a type error merged to `main` blocks *deployment* instead of the *PR* — exactly what happened with PR #50's aftermath.
- **Recommendation:** Add a `frontend-ci` workflow: typecheck + lint + (once they exist) tests for both apps, path-filtered. Keep job names stable for branch protection.
- **Effort:** S · **Priority:** P1

### OPS-05 — No dependency/vulnerability scanning anywhere
- **Severity:** Medium · **Category:** Supply chain (OWASP A06) · **Evidence:** No `pip-audit`, `npm audit`, Dependabot config, or image scanning in the repo.
- **Recommendation:** Enable Dependabot (pip + npm + actions ecosystems, weekly), add `pip-audit` as a non-blocking CI step first, blocking after triage.
- **Effort:** S · **Priority:** P2

### OPS-06 — Production image contains dev/test dependencies
- **Severity:** Low · **Category:** Image hygiene · **Location:** `Dockerfile` builder stage: `pip install -r requirements.txt -r requirements-dev.txt`
- **Evidence:** pytest, mypy, ruff etc. ship in the runtime image (bigger surface, slower pulls). `COPY . .` also brings docs/scripts/tests into the image.
- **Recommendation:** Install only `requirements.txt` in the runtime path (dev deps in a separate CI target); add `.dockerignore` entries for tests/docs/scripts if not present.
- **Effort:** S · **Priority:** P3

### OPS-07 — Observability is logs-on-disk only
- **Severity:** Medium · **Category:** Observability · **Evidence:** Structured logging with request IDs exists; `ENABLE_METRICS` gate exists but no Prometheus/Grafana/alert stack is deployed; no uptime monitoring configured in-repo; no error tracker (Sentry).
- **Why problematic:** The order-expiry worker, Hesabfa pushes, and payment failures can only be discovered by reading files on the VPS.
- **Recommendation:** Cheapest effective stack: external uptime monitor on `/ready` (UptimeRobot-class), Sentry (or GlitchTip self-hosted) for backend+frontends, enable the existing Prometheus instrumentation + a single Grafana Cloud free-tier dashboard. Alert on: 5xx rate, `/ready` failures, payment verify failures, worker heartbeat.
- **Effort:** M · **Priority:** P1

### OPS-08 — Migrations run on every container start
- **Severity:** Low · **Category:** Deploy correctness · **Location:** `docker-entrypoint.sh` (alembic upgrade at boot)
- **Evidence:** Fine for a single API container; if API replicas are ever scaled, concurrent `alembic upgrade` races (Postgres transactional DDL mitigates but doesn't guarantee for all operations).
- **Recommendation:** Note the constraint in OPERATIONS.md; when scaling, move migrations to a one-shot deploy job.
- **Effort:** S · **Priority:** P4

## 3. Self-challenge

- Verified DB/Redis really are localhost-bound in the staging override (not just the base file).
- Verified the fork-PR guard exists on the packaging job (the one feeding the self-hosted runner).
- Could not verify from the repo: nginx `client_max_body_size` (cross-ref SEC-02), HSTS actually enabled (script exists; execution state unknown), runner systemd persistence, whether backup cron is actually installed on the VPS today. These four need a 30-minute VPS session to confirm.

## 4. Scores

| Category | Score | Justification |
|---|---|---|
| Containerization | **8/10** | Multi-stage, non-root, real healthchecks; dev deps in prod image. |
| CI/CD | **6.5/10** | Real backend gates and a smart artifact pattern; no frontend PR gate, fragile single runner. |
| Environment topology | **4/10** | No true staging; live site deploys on every merge. |
| Backup/DR | **4/10** | Automated daily backups exist (better than most at this stage) but same-disk = not disaster recovery. |
| Observability | **4.5/10** | Good logs, zero alerting/aggregation/uptime monitoring. |
| DevOps overall | **5.5/10** | Scripted and thoughtful, but the platform is one disk failure away from total loss and one merge away from breaking production. |
