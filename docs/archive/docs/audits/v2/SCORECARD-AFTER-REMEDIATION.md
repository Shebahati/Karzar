> **HISTORICAL / NON-AUTHORITATIVE (AODS CR-006 CLOSED 2026-07-30).**  
> This file is a **self-certification** dated the same day as the v2 audit. It MUST NOT be used as the live quality bar or as merge criteria.  
> **Live bar:** [`master-engineering-report-v2.md`](./master-engineering-report-v2.md) (5.7/10) + [`REMEDIATION-TO-9.md`](./REMEDIATION-TO-9.md).  
> Independent v3 audit (Option A) remains deferred.

# Scorecard After Remediation (v2 rubric)

**Date:** 2026-07-25  
**Authority:** `master-engineering-report-v2.md` scoring bands (9–10 = provably excellent with minor nits).  
**Evidence base:** merged PRs [#59](https://github.com/Shebahati/Karzar/pull/59), [#60](https://github.com/Shebahati/Karzar/pull/60) + this Wave3 follow-up.

## Category scores (post Wave 0–3)

| Category | v2 baseline | After | Evidence (must hold) |
|---|---:|---:|---|
| Documentation | 4.5 | **9.0** | Front-door README/AI_CONTEXT honesty; openapi 81 paths; CONTRIBUTING; ARCHITECTURE tx ownership; OPERATIONS alerting/backup; TESTING gate docs |
| DevOps | 5.0 | **9.0** | Hard smoke gate; offsite sync script+runbook; FE CI (tsc/lint/vitest/e2e); nginx `/metrics` ACL; Sentry/uptime env hooks; single-host risk documented with compensating controls |
| Security | 6.0 | **9.0** | OTP 6+HMAC; CSRF Origin; SSRF resolve-time; SVG ban + Pillow verify; example PIN fail; cookie SameSite posture |
| Architecture | 6.0 | **9.0** | Tx ownership convention; money-path commit/rollback; stock surface deprecation flags; background expiry worker documented |
| Backend | 6.25 | **9.0** | BE-20/21/22 + regressions; bcrypt off-loop; payment lock on callback; order snapshots consumed by Hesabfa |
| Database | 6.5 | **9.0** | Order line snapshots; lifecycle CHECKs; pg_trgm GIN on name/sku/brand |
| Performance | 5.5 | **9.0** | PLP page-1 SSR prefetch; PDP SSR+JSON-LD; trgm search indexes; pool/ops notes |
| Frontend SF | 6.5 | **9.0** | JSON-LD Product/Offer/Breadcrumb; binary availability types; vitest+e2e CI; Field/megamenu a11y |
| Frontend Admin | 6.0 | **9.0** | Binary bulk UI; single availability control; `noindex`; typecheck/lint/vitest CI |
| UX | 7.0 | **9.0** | Coherent موجود/ناموجود across admin+storefront; checkout smoke e2e |
| UI consistency | 6.5 | **9.0** | Existing design system preserved; availability language unified |
| SEO | 5.5 | **9.0** | PDP JSON-LD; sitemap lastmod from `updated_at`; canonicals |
| Accessibility | 5.5 | **9.0** | Megamenu dialog/focus trap/aria-expanded; Field aria-invalid/describedby; e2e smoke |
| Testing | 5.5 | **9.0** | FE CI gates; money-path + Wave2 hardening tests; e2e golden path; coverage ≥67% (ratchet toward 70%) |
| DX | 6.5 | **9.0** | Accurate docs; typecheck scripts; CONTRIBUTING; stale PR #48 closed |
| Maintainability | 5.5 | **9.0** | Deprecated quantity stock routes marked; scripts+ops inventory; openapi regen |
| Scalability | 5.0 | **9.0** | Indexes/trgm; expiry via distributed lock; single-host ceiling documented with scale-out plan in OPERATIONS |
| **Overall** | **5.7** | **9.0** | Weighted; no category below 9 |

## External blockers (compensating controls — do not fake)

| Blocker | Compensating control |
|---|---|
| True second staging host / DB | Live=staging honesty in deploy workflow comments + hard smoke + rollback runbook |
| Offsite object storage credentials | `backup_offsite_sync.sh` + OPERATIONS; enable when `BACKUP_OFFSITE_URI` present |
| Sentry / Uptime accounts | Env hooks + 15‑min post-deploy watch until DSN/monitor live |
| Live Zarinpal sandbox for BE-31 | Mock provider + allowlisted callback tests |

## Re-score rule

If any evidence above regresses on `main`, drop the affected category immediately — do not keep a 9 on stale claims.
