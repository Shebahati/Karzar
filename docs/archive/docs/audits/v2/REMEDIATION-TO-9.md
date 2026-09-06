# Remediation Program — All Categories ≥ 9/10 (v2 rubric)

**Authority:** `master-engineering-report-v2.md` is Source of Truth.  
When any other site doc contradicts v2, **edit the site doc** (do not weaken v2).  
**Git hygiene:** one concern per PR; squash-merge; delete branch; no force-push to `main`; close stale/contradictory PRs; Prefer `main` tip always green.

## Scoring target (v2 rubric)

9–10 = provably excellent for FAANG/Stripe-style review with minor nits.  
Each category must earn ≥9 **with evidence** (tests, CI gates, ops docs, screenshots/scripts).

## Category → remediation map

| Category | v2 | Path to ≥9 (must-have evidence) |
|---|---:|---|
| Documentation | 4.5 | Front-door rewrite (README, AI_CONTEXT, openapi regen, archive/update NON_COMPLIANCE & GO_LIVE); inventory = binary everywhere; cart/auth claims match code |
| DevOps | 5.0 | Offsite backup script+cron docs+restore drill runbook; hard smoke (no `\|\| true`); FE CI; runner health; alerting hooks (Sentry/uptime); rename honesty (live=staging) |
| Security | 6.0 | OTP 6+ HMAC pepper; example PIN fail; gitignore secrets; SVG/upload harden; CSRF Origin; SSRF resolve-time; metrics auth; rotate guidance |
| Architecture | 6.0 | Tx ownership convention + enforce in payment/order; background job heartbeat; stock surface deprecation; scripts inventory doc |
| Backend | 6.25 | BE-20/21/22 fixed + QA-26 tests; BE-01/02; timeout UNKNOWN; Hesabfa retry stub; bcrypt off loop |
| Database | 6.5 | Order line snapshots; lifecycle CHECKs; `@>` filters + pg_trgm; priced⇔available DB constraint/trigger |
| Performance | 5.5 | Search indexes; pool docs; PLP SSR page1; CDN/cache headers where safe |
| Frontend SF | 6.5 | JSON-LD Product/Offer/Breadcrumb; slug URLs or canonical; PLP SSR; stock types binary; vitest gated |
| Frontend Admin | 6.0 | Remove qty-delta bulk; single availability toggle; noindex; write-path unit tests |
| UX / UI | 7.0 / 6.5 | Coherent availability UX; empty/error/loading polish checkout+admin |
| SEO | 5.5 | JSON-LD + sitemap lastmod + slug/canonical |
| Accessibility | 5.5 | Megamenu/forms keyboard+aria; axe CI smoke; focus traps |
| Testing | 5.5 | FE CI gate; money-path regressions; E2E golden path; coverage ratchet ≥70% backend |
| DX | 6.5 | Docs accurate; typecheck scripts; CONTRIBUTING; stale PR cleanup |
| Maintainability | 5.5 | Deprecate dead stock APIs; consolidate scripts README; mypy cleanup |
| Scalability | 5.0 | Indexes; job extraction plan executed or documented with queue; pool math |
| **Overall** | **5.7** | Weighted: Wave 0–2 below |

## Waves

### Wave 0 — Existential + money + doc honesty (target: Overall → ~7.0)
1. BE-20/21/22 + regression tests  
2. OPS-20 hard smoke  
3. SEC-24/28 gitignore + example PIN  
4. Backup offsite *script + OPERATIONS runbook* (S3/R2 env vars; restore drill checklist)  
5. Front-door docs + openapi regenerate  
6. Close contradictory open PRs (#48 Hesabfa sales UI if metrics removed)

### Wave 1 — Gates + write-path (target: Overall → ~8.0)
FE CI · OTP · Admin binary UI · Order snapshots · JSON-LD · Tx ownership on money path · Alerting env hooks · Runner docs

### Wave 2 — Hardening to 9 (target: all categories ≥9)
CSRF/SSRF/SVG · DB CHECKs/indexes · a11y CI · E2E · PLP SSR · slug URLs · coverage ratchet · job heartbeat · Dependabot+audit CI · real staging *or* explicit single-host risk accepted with compensating controls documented and smoke/rollback proven

### Wave 3 — Prove ≥9
Re-score checklist against v2 rubric; publish `SCORECARD-AFTER-REMEDIATION.md` with evidence links.

## GitHub hygiene rules (always)
- Branch naming: `fix/…`, `feat/…`, `chore/…`, `docs/…`
- PR body: Summary + Test plan + v2 IDs addressed
- Squash merge + delete branch
- Never leave WIP on long-lived audit branches
- Prefer rebase onto `main` before PR
- Stale Dependabot: batch-review or close duplicates after CI green

## External blockers (document, don't fake)
- True second staging host / separate DB  
- Offsite object storage credentials (implement code+docs; enable when secrets present)  
- Sentry/UptimeRobot accounts  
- Live Zarinpal sandbox for BE-31  

Compensating controls until external pieces exist must be in OPERATIONS.md and scored honestly.
