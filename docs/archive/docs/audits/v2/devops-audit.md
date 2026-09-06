# Phase — DevOps, Infrastructure & Operations Audit (v2, strict)

**Date:** 2026-07-25 · **Auditors:** DevOps / SRE / Security (hostile due-diligence)
**Baseline:** v1 `docs/audits/devops-audit.md` (overall 5.5)
**Branch:** `docs/engineering-audit-2026-07` @ `66e9ae9`
**Method:** Full read of `.github/workflows/{backend-ci,deploy-staging,deploy-production}.yml`, `.github/dependabot.yml`, `Dockerfile`, `deploy/staging/Dockerfile.staging`, `docker-compose*.yml`, `docker-entrypoint.sh`, `gunicorn_conf.py`, `deploy/staging/scripts/*`, `scripts/backup_{db,uploads}.sh`, `docs/OPERATIONS.md`, `docs/COLLABORATOR_DEPLOY.md`, nginx template, `.dockerignore`.

---

## 1. What is genuinely good (re-verified)

1. **Staging loopback binds:** `docker-compose.staging.yml` overrides API/DB/Redis to `127.0.0.1` — Postgres/Redis not publicly reachable when staging compose is used.
2. **Live image path is slimmer than root Dockerfile:** `Dockerfile.staging` installs only `requirements.txt` (not `requirements-dev.txt`); non-root `appuser`; `HEALTHCHECK` → `/ready`.
3. **Self-hosted deploy threat model understood:** fork guard (`deploy-staging.yml:36`); package on `ubuntu-latest`, deploy on `[self-hosted, karzar-vps]`; artifact handoff; concurrency group.
4. **Dependabot is configured** (v1 claimed absent — **wrong**): `.github/dependabot.yml` weekly pip + github-actions + npm Storefront + npm admin-panel.
5. **Ops scripting:** bootstrap, deploy-backend/frontend, smoke-staging, restore-db, install-backup-cron, enable-hsts; backups `scripts/backup_db.sh`, `scripts/backup_uploads.sh`. Cron installer itself warns on-host ≠ DR.
6. **Backend CI gates:** ruff + mypy + pytest `--cov-fail-under=62`; path filter with always-green skip for required check names on non-backend PRs.

---

## 2. Critique of the v1 report

| Issue | Verdict |
|---|---|
| “No Dependabot” (OPS-05) | **False.** Config exists on this branch and `origin/main` lineage. Remaining gap = no `pip-audit`/`npm audit`/image scan in CI. |
| OPS-06 “prod image has dev deps” | **Overstated for live path** — staging Dockerfile is prod-only. Root `Dockerfile` still wrong. |
| Smoke “exists” | Missed that workflows **never call** `smoke-staging.sh` and soft-fail admin curl with `\|\| true`. |
| Overall 5.5 | Still in the right band; v2 drops to **5.0** after soft smoke + deploy-time mutation + public metrics path. |

---

## 3. Findings register

### Re-verified / revised v1 findings

#### OPS-01 — “Staging” is production
- **Severity:** High · **Category:** Environment topology · **Location:** `deploy-staging.yml:3`; `deploy-production.yml:3–5`; `COLLABORATOR_DEPLOY.md:22–25`
- **Evidence:** Push to `main` (path-filtered) auto-deploys customer site. Production workflow is manual confirm only, same host/scripts.
- **Why / Impact:** Every merged PR goes straight to customers; naming creates false safety. Admin typecheck/availability regressions this week reached live because there is nowhere else for them to go.
- **Recommended:** Rename to `deploy-live`; hard smoke gate + rollback; mid-term second stack/DB. **Effort:** S / M · **Priority:** **P1**.

#### OPS-02 — Backups live on the same disk they protect
- **Severity:** High · **Category:** Disaster recovery · **Location:** `install-backup-cron.sh:6–8,17,23–24,32`; `scripts/backup_db.sh:6–10`; `scripts/backup_uploads.sh:6–10`
- **Evidence:** Cron writes DB + uploads under repo `backups/` on VPS. Script admits: *"on-host alone is not DR"* (`:32`). `OPERATIONS.md:153–155` documents off-host requirement with no automation.
- **Why / Impact:** Disk failure / ransomware / `rm -rf` destroys data **and** backups. Single largest business-continuity risk.
- **Recommended:** Nightly rclone/restic to Arvan/S3; retention 7d/4w; rehearse restore. **Effort:** S · **Priority:** **P0**.

#### OPS-03 — Runner is a single point of deploy failure with no health alerting
- **Severity:** Medium · **Category:** CI/CD reliability · **Location:** `deploy-staging.yml:63`; `COLLABORATOR_DEPLOY.md:30`
- **Evidence:** No in-repo heartbeat/alert for runner offline; deploy queues silently.
- **Recommended:** systemd `Restart=always` + Runners API heartbeat alert; document manual `deploy-backend.sh` fallback. **Effort:** S · **Priority:** **P1**.

#### OPS-04 — No frontend gate in PR CI
- **Severity:** Medium · **Category:** CI · **Location:** `.github/workflows/` — only three workflows; none run FE lint/test/typecheck
- **Evidence:** Storefront/admin have `test`/`lint`/`test:e2e` scripts but **zero** workflow invokes them. FE type errors surface at deploy `next build`. Impact higher now that Vitest/e2e **exist** but are ungated.
- **Recommended:** `frontend-ci.yml`: lint + `vitest run` + `tsc --noEmit` path-filtered for both apps. **Effort:** S · **Priority:** **P1**.

#### OPS-05 — Supply-chain scanning incomplete *(revised — Dependabot EXISTS)*
- **Severity:** Low–Medium (narrowed from Medium) · **Category:** Supply chain · **Location:** `.github/dependabot.yml:1–37`; CI has no `pip-audit`/`npm audit`/image scan
- **Evidence:** Dependabot covers pip, actions, both npm trees weekly. Remaining: no vulnerability *gate* in CI, no container scan.
- **Recommended:** Keep Dependabot; add non-blocking then blocking audits; scan staging image. **Effort:** S · **Priority:** P2.

#### OPS-06 — Root Dockerfile ships dev deps; staging Dockerfile does not *(revised)*
- **Severity:** Low · **Category:** Image hygiene · **Location:** `Dockerfile:18–20` vs `Dockerfile.staging:19–21`; `.dockerignore` excludes tests/docs but **not** `scripts/`
- **Evidence:** Live path uses staging Dockerfile (`deploy-backend.sh:41–43`). Root still installs `requirements-dev.txt`. Scripts still `COPY`’d.
- **Recommended:** Align root with staging; slim dockerignore for runtime. **Effort:** S · **Priority:** P3.

#### OPS-07 — Observability is logs + ungated metrics; no Sentry/alerting
- **Severity:** Medium · **Category:** Observability · **Location:** `main.py:102–108`; `docker-compose.staging.yml:17` `ENABLE_METRICS: "true"`; zero Sentry matches under `app/`; nginx API location proxies broadly
- **Evidence:** Structured logs + request IDs; `/metrics` can be internet-reachable when enabled; no uptime monitor / Grafana / error tracker in-repo.
- **Recommended:** Uptime on `/ready`; Sentry/GlitchTip; ACL `/metrics`; alert 5xx, ready failures, payment verify, order-expiry exceptions. **Effort:** M · **Priority:** **P1**.

#### OPS-08 — Migrations run on every container start
- **Severity:** Low · **Category:** Deploy correctness · **Location:** `docker-entrypoint.sh:4–5`
- **Evidence:** Fine for single API container; concurrent upgrades if replicas scale.
- **Recommended:** Document; move to one-shot job when scaling. **Effort:** S · **Priority:** P4.

---

### New findings (v2)

#### OPS-20 — Post-deploy smoke is incomplete and admin is soft-failed
- **Severity:** High · **Category:** Deploy correctness / release gating · **Location:** `deploy-staging.yml:137–140`; twin in `deploy-production.yml:126–129`; full script `smoke-staging.sh:30–34`
- **Evidence:** Workflow only curls `/ready` + shop `/`; admin uses `|| true` so admin 5xx/down does **not** fail the job. Full `smoke-staging.sh` (health/ready/products/shop/admin) is **never invoked**.
- **Why / Impact:** Broken admin can ship green; product API regression not checked. Negates the value of having a smoke script.
- **Recommended:** Call `smoke-staging.sh` with public bases; fail deploy on any check; remove `|| true`. **Effort:** S · **Priority:** **P0**.

#### OPS-21 — Deploy-time source mutation on frontend
- **Severity:** Medium · **Category:** Deploy integrity / reproducibility · **Location:** `deploy/staging/scripts/deploy-frontend.sh:31–66`
- **Evidence:** Patches `next.config.ts` remotePatterns; `sed` on `env.ts` USE_MOCK defaults. Live image content can diverge from git SHA.
- **Recommended:** Fix configs in-repo; delete deploy-time sed/python patches; build = pure function of commit. **Effort:** S · **Priority:** **P1**.

#### OPS-22 — Base compose publishes Postgres/Redis on all interfaces
- **Severity:** Medium · **Category:** Network exposure · **Location:** `docker-compose.yml:38–39,59–60` (no `127.0.0.1`)
- **Evidence:** Staging override fixes this; forgetting `-f docker-compose.staging.yml` exposes DB/Redis.
- **Recommended:** Bind `127.0.0.1` in base compose too. **Effort:** S · **Priority:** P2.

#### OPS-23 — Staging Dockerfile trusts third-party PyPI mirror
- **Severity:** Low–Medium · **Category:** Supply chain · **Location:** `Dockerfile.staging:4–6` Aliyun PyPI; apt via Arvan (`:10–14`)
- **Evidence:** Justified for Iran egress; mirror integrity not hash-pinned.
- **Recommended:** Document risk; prefer `--require-hashes` or vendor wheels. **Effort:** M · **Priority:** P3.

#### OPS-24 — Production + staging workflows can race the same host
- **Severity:** Medium · **Category:** Release safety · **Location:** Separate concurrency groups `deploy-staging` vs `deploy-production`; both rsync to `/opt/karzar/Karzar`
- **Evidence:** Concurrent staging push + manual production dispatch can interleave rebuilds.
- **Recommended:** Shared concurrency group `deploy-live` until hosts split. **Effort:** S · **Priority:** P2.

#### OPS-25 — No frontend workflow file at all
- **Severity:** Medium · **Category:** CI topology · **Location:** `.github/workflows/` — 3 files only
- **Evidence:** Complements OPS-04; Dependabot may open npm PRs with no test status required.
- **Recommended:** Same as OPS-04; require FE checks on Dependabot npm PRs. **Effort:** S · **Priority:** **P1**.

---

## 4. Doc-drift table

| Doc | Claim | Reality | Verdict |
|---|---|---|---|
| `COLLABORATOR_DEPLOY.md` | Staging = live VPS | Matches workflows | Accurate (honest) |
| `OPERATIONS.md` | Off-host backups required; restore drill link | Requirement stated; `docs/roadmap/` link dead | Minor drift |
| `OPERATIONS.md` | Entrypoint runs alembic | Matches `docker-entrypoint.sh` | Accurate |
| Workflow headers | Staging = live | Matches | Accurate (exemplary honesty) |
| v1 OPS-05 | No Dependabot | Dependabot exists | **v1 wrong** |

---

## 5. Scores (0–10, strict)

| Category | v1 | v2 | Delta justification |
|---|---|---|---|
| Containerization | 8.0 | **7.5** | −0.5. Staging Dockerfile good; root still ships dev deps; scripts not dockerignored. |
| CI/CD | 6.5 | **5.5** | −1.0. Backend gates solid; Dependabot helps; no FE CI; smoke soft-fail; runner SPOF. |
| Environment topology | 4.0 | **3.5** | −0.5. Staging=live; prod workflow is same-host theater; race possible. |
| Backup/DR | 4.0 | **3.5** | −0.5. Cron exists + admits on-host≠DR; still no offsite automation. |
| Observability | 4.5 | **4.0** | −0.5. Metrics on in staging, likely public; no Sentry/uptime/alerts. |
| **DevOps overall** | **5.5** | **5.0** | **−0.5**. Scripted and thoughtful, but P0 backup + soft smoke + live-on-merge dominate under acquisition bar. |

---

## 6. Self-review

- Verified Dependabot on disk and on `origin/main` lineage.
- Verified staging loopback overrides; live build uses `Dockerfile.staging`.
- Verified soft-fail admin curl and unused full smoke script — highest-signal new finding (OPS-20).
- **Unverified from repo:** runner systemd persistence, whether backup cron is installed *today*, HSTS after Certbot, whether `/metrics` is firewalled on HTTPS server.
