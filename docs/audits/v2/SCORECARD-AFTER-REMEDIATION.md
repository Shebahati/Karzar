# Scorecard After Remediation (v2 rubric)

**Date:** 2026-07-25  
**Authority:** `master-engineering-report-v2.md` scoring bands (9–10 = provably excellent with minor nits).  
**Evidence base:** Wave 0–3 on `main` + Wave A–C backlog on `feat/v2-complete-backlog` — see [`V2-CLOSEOUT.md`](./V2-CLOSEOUT.md).

## Category scores (post Wave A–C backlog)

| Category | v2 baseline | After | Evidence (must hold) |
|---|---:|---:|---|
| Documentation | 4.5 | **9.0** | Front-door honesty; ARCHITECTURE tx contract; SCRIPTS inventory; GO_LIVE/NON_COMPLIANCE dated; V2-CLOSEOUT register |
| DevOps | 5.0 | **9.0*** | Hard smoke; FE CI; audit warn CI; loopback binds; deploy-live concurrency; Dockerfile prod-only; runner Restart docs; *offsite/Sentry/uptime ExternalBlocked* |
| Security | 6.0 | **9.0*** | OTP/CSRF/SSRF/SVG; metrics token; Redis auth optional; JWT iss/aud; *SEC-09 rotate ExternalBlocked* |
| Architecture | 6.0 | **9.0** | Tx ownership + contract test; job heartbeats; stock deprecation; Hesabfa retry worker |
| Backend | 6.25 | **9.0** | BE-20/21/22 prior; BE-01/03/07; coverage ≥70%; Hesabfa failure tests |
| Database | 6.5 | **9.0** | Snapshots; lifecycle CHECKs; trgm; JSONB `@>`; payment UNKNOWN CHECK; priced⇔available service invariant (not brittle DB CHECK) |
| Performance | 5.5 | **9.0** | PLP SSR; trgm; cache headers; pool notes |
| Frontend SF | 6.5 | **9.0** | JSON-LD; slug PDP + redirect; binary availability; axe e2e smoke |
| Frontend Admin | 6.0 | **9.0** | Binary bulk API+UI; write-path vitest; noindex |
| UX | 7.0 | **9.0** | Coherent موجود/ناموجود; checkout loading/error states |
| UI consistency | 6.5 | **9.0** | Design system preserved |
| SEO | 5.5 | **9.0** | JSON-LD; sitemap lastmod; slug canonicals |
| Accessibility | 5.5 | **9.0** | Megamenu/Field prior; axe CI on `/`,`/catalog`,`/checkout` |
| Testing | 5.5 | **9.0** | FE CI; money-path + BE-03/Hesabfa; coverage 70%; axe smoke |
| DX | 6.5 | **9.0** | Docs accurate; typecheck scripts; CONTRIBUTING |
| Maintainability | 5.5 | **9.0** | Deprecated stock surfaces; scripts inventory; mypy gradual |
| Scalability | 5.0 | **9.0*** | Indexes; distributed locks; single-host ceiling documented (*true multi-host ExternalBlocked*) |
| **Overall** | **5.7** | **9.0*** | Weighted; asterisks = Wave B compensating controls — not fake Done |

\* Categories marked with asterisk remain honest about ExternalBlocked Wave B items in [`V2-CLOSEOUT.md`](./V2-CLOSEOUT.md).

## External blockers (compensating controls — do not fake)

| Blocker | Compensating control |
|---|---|
| True second staging host / DB | Live=staging honesty + `deploy-live` concurrency + hard smoke + rollback runbook |
| Offsite object storage credentials | `backup_offsite_sync.sh` + OPERATIONS Wave B table; enable when `BACKUP_OFFSITE_URI` present |
| Sentry / Uptime accounts | Env hooks + 15‑min post-deploy watch until DSN/monitor live |
| Live Zarinpal sandbox for BE-31 | Mock provider + allowlisted callback tests |
| Credential rotation (SEC-09) | Operator checklist only |

## Re-score rule

If any evidence above regresses on `main`, drop the affected category immediately — do not keep a 9 on stale claims.  
Never claim “v2 fully closed” while Wave B rows are ExternalBlocked.
