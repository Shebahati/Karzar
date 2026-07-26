# Karzar — Master Engineering Report v2 (Strict)

**Date:** 2026-07-25 · **Basis:** 9 completed v2 phase reports under `docs/audits/v2/` (+ plan)
**Repository:** `Shebahati/Karzar` monorepo — FastAPI backend, Next.js storefront + admin, PostgreSQL/Redis, single-VPS Docker
**Baseline:** v1 master (`docs/audits/master-engineering-report.md`) overall **6.8/10** — treated as a baseline to beat *and* as an audit subject (missed findings, incorrect claims, generous scores)
**Live context:** ~5,900 products, 40 brands, 159 categories, karzartools.com + admin.karzartools.com
**Posture:** Acquisition-bar due diligence. No provisional scores. Every score states v1 and justifies delta.

---

## 1. Executive Summary

Karzar remains **better engineered than a typical two-person commerce build** — and under strict review is **not yet at the bar a multi-million-dollar acquisition diligence team would call production-grade without pricing material risk**.

What still holds: boot-time config validators that make weak production configs unbootable; a payment substrate with row locking, idempotency, allowlisted redirects, and append-only ledgers (convention, not schema-enforced); hashed refresh tokens and step-up JTIs; a real backend suite (242 tests, 62% coverage floor); storefront SSR on PDPs with complete metadata/sitemap/robots plumbing and native RTL; admin memory+HttpOnly token client with HMAC edge session cookie.

What v2 found that v1 missed or underpriced:

1. **Documentation is a first-class failure mode.** Front-door docs (`README.md`, `frontend/AI_CONTEXT.md`, stale `openapi/v1.json`, abandoned `BACKEND_NON_COMPLIANCE.md` / `GO_LIVE`) actively mislead. Documentation score collapses **7.0 → 4.5**.
2. **Money-path correctness gaps** in the flagship payment flow: refund-after-fulfillment rolls back DB after gateway success (BE-20); expiry sweep can lose to a concurrent verify (BE-21); callback verifies without the row lock `/verify` uses (BE-22). These were not in v1.
3. **OTP is 5-digit (~10⁵) with unsalted SHA-256** — v1 said 6-digit/10⁶. Auth strength re-scored.
4. **Ops release gating is softer than claimed:** full `smoke-staging.sh` unused; admin curl soft-failed with `|| true`; backups still same-disk (P0).
5. **Frontend tests exist** (v1 said ~0) — 38+5 Vitest cases + 2 Playwright smokes — but **are not CI-gated**, and admin write-path (bulk quantity UI, dual availability toggles) still contradicts the binary-availability business decision.

**One sentence:** Offsite backups + hard smoke this week, fix BE-20 before the gateway goes live, and stop shipping docs that contradict code — otherwise the genuine strengths will not survive diligence.

**Why this v2 pass was interrupted earlier:** a prior agent hit API rate limits mid-corpus, and a content-filter tripped on security-report wording; this completion reframes security as defensive posture / hardening / misconfiguration only and finishes the missing reports + PR.

---

## 2. Overall Engineering Score

| Category | v1 | v2 | Δ | Primary source |
|---|---:|---:|---:|---|
| Architecture | 7.5 | **6.0** | −1.5 | architecture-audit |
| Backend | 7.0 | **6.25** | −0.75 | backend-audit |
| Frontend (storefront) | 7.5 | **6.5** | −1.0 | frontend-storefront-audit |
| Frontend (admin) | 6.5 | **6.0** | −0.5 | frontend-admin-audit |
| Database | 7.0 | **6.5** | −0.5 | database-audit |
| Performance | 6.0 | **5.5** | −0.5 | backend + database |
| Security | 7.5 | **6.0** | −1.5 | security-audit |
| UX | 7.5 | **7.0** | −0.5 | storefront + admin |
| UI consistency | 7.0 | **6.5** | −0.5 | storefront + admin |
| SEO | 6.5 | **5.5** | −1.0 | storefront |
| Accessibility | 7.0 *(provisional)* | **5.5** | −1.5 | storefront (static only; provisional banned) |
| DevOps | 5.5 | **5.0** | −0.5 | devops-audit |
| Testing | 6.0 | **5.5** | −0.5 | testing-quality-audit |
| Developer Experience | 7.5 | **6.5** | −1.0 | testing + documentation |
| Maintainability | 6.5 | **5.5** | −1.0 | architecture |
| Scalability | 6.0 | **5.0** | −1.0 | architecture + database |
| Documentation | 7.0 | **4.5** | −2.5 | documentation-audit (**new dedicated phase**) |
| **Overall Engineering** | **6.8** | **5.7** | **−1.1** | weighted toward ops/DR, money-path, and doc drift |

### Why overall 5.7 (not 6.x)

The code-quality average across product phases sits near mid-6s. Acquisition-bar grading **pulls overall down** by:

- DevOps/DR still existential (same-disk backups + soft smoke + staging=live)
- Documentation actively misleading at the front door (−2.5 alone)
- Security OTP/upload/secret-hygiene footguns (−1.5)
- Unfixed High money-path defects discovered only in v2

A 5–6 band means: *works, with systemic weaknesses a diligence team prices in*. That is the honest placement. Path back toward 7.0 is mostly S–M effort items (Wave 0–1 below) — the team’s craft is not the bottleneck; remediation follow-through and doc discipline are.

---

## 3. Biggest NEW findings (esp. doc drift)

| ID | Finding | Why new / why it matters |
|---|---|---|
| DOC corpus | README wrong cart methods; AI_CONTEXT claims SQLAdmin / no refresh / ComingSoon for live features; openapi missing ~11 routes; NON_COMPLIANCE & GO_LIVE broke their own update rules | Docs teach wrong inventory, auth, and API shape to humans and agents |
| BE-20 | Refund of shipped/delivered: gateway refunds, DB rolls back, retry can double-refund | P0 money-path; v1 called payment “strongest code” |
| BE-21 / BE-22 | Expiry lost-update vs verify; callback without row lock | Concurrency holes in flagship flow |
| SEC-20 / SEC-04 | OTP is **5-digit** + unsalted SHA-256 (v1 said 6-digit) | Auth strength overstated in v1 |
| SEC-28 | `.env.example` PIN `8472916350` **passes** weak-PIN validator | Public footgun for production-like copies |
| OPS-20 | Full smoke script unused; admin curl `\|\| true` | Broken admin can ship green |
| FE-A-20 / FE-A-21 | Bulk quantity-delta UI + dual availability toggles after binary pivot | Write-path UX contradicts business decision (PR #55 aftermath) |
| QA census | FE tests exist (38+5 + e2e) but ungated; TESTING.md lists nonexistent file | v1 undercounted tests and overstated FE void |

### v1 errors corrected

- Dependabot **exists** (v1/devops said no)
- Storefront tests **exist** (v1/QA said 0)
- OTP width **5 digits** (v1 said 6)
- Accessibility **provisional 7.0 banned** → 5.5 on static evidence
- Documentation **7.0 unsupported** → 4.5 after ~200 claim checks
- Live Dockerfile is staging (prod deps) — root Dockerfile still ships dev deps

---

## 4. Consolidated Issue Register (deduplicated, prioritized)

Full evidence, root cause, alternatives, and effort live in phase reports. IDs below are the canonical references.

### P0 — Critical (this week)

| # | Issue | ID | Effort |
|---|---|---|---|
| 1 | Backups on same VPS disk; no offsite copy / restore drills | OPS-02 | S |
| 2 | Post-deploy smoke soft-fails admin; full smoke script unused | OPS-20 | S |
| 3 | Refund shipped/delivered: gateway success then DB rollback / retry double-refund | BE-20 | M |
| 4 | Add regression tests for BE-20/21/22 before gateway live | QA-26 | M |

### P1 — High (this month)

| # | Issue | ID | Effort |
|---|---|---|---|
| 5 | No true pre-prod; rename deploy-live + hard smoke + rollback | OPS-01 | S–M |
| 6 | Zero alerting/uptime/Sentry; metrics likely public | OPS-07 / SEC-23 | M |
| 7 | Order items lack product name/SKU/tax snapshot | DB-01 / ARCH-06 | S |
| 8 | Transaction ownership anarchy (commits in endpoints *and* services) | BE-01 | M |
| 9 | Payment callback commits on unexpected exceptions / swallows them | BE-02 | S |
| 10 | Expiry sweep lost-update vs concurrent verify | BE-21 | S–M |
| 11 | Callback verify without row lock | BE-22 | S |
| 12 | Frontend CI gate (lint + vitest + tsc); typecheck scripts | OPS-04 / OPS-25 / QA-21 / QA-24 | S |
| 13 | Admin bulk quantity UI + dual availability toggles | FE-A-20 / FE-A-21 | M / S |
| 14 | Runner offline = silent deploy freeze | OPS-03 | S |
| 15 | No Product/Offer/Breadcrumb JSON-LD on PDPs | FE-S-01 | S–M |
| 16 | Rotate chat-transited credentials; password manager | SEC-09 | S |
| 17 | OTP 5-digit + unsalted hash → 6+ digits + HMAC pepper | SEC-20 / SEC-04 | S |
| 18 | `.gitignore`/`.dockerignore` secret gaps; example PIN footgun | SEC-24 / SEC-28 | S |
| 19 | README / AI_CONTEXT / openapi / NON_COMPLIANCE / GO_LIVE doc drift cluster | DOC-* / ARCH-03 / FE-S-23 / FE-A-25 | S–M |
| 20 | Deploy-time frontend source mutation (sed/patches) | OPS-21 | S |
| 21 | bcrypt sync on event loop | BE-23 | S |
| 22 | Admin write-path unit tests (api-client, availability, orders) | QA-01 / QA-23 / FE-A-01 | M |

### P2 — Medium (this quarter)

Shared PIN / CSRF Origin check / SVG+extension-only uploads / SSRF resolve-time / Redis auth / register flag harden / gateway timeout as UNKNOWN / lifecycle CHECKs / JSONB `@>` filters / pg_trgm + Persian normalization / priced⇔available invariant / tax default 9 vs 0 / Hesabfa retry job / PLP SSR / slug URLs / a11y megamenu+forms / admin noindex / Dependabot+audit scanners / TESTING.md fix / mypy disable cleanup / stock semantic FE cleanup / base compose loopback binds / deploy concurrency race.

(See phase reports: SEC-01…05,10,21,22,25; BE-03,05,07,09; DB-02…05,08,21,24; FE-S-02,03,07,20–22; FE-A-03,22,27; OPS-05,22,24; QA-02,03,20,22.)

### P3 / P4 — Low (opportunistic)

JWT iss/aud, CORS narrowing, sitemap lastmod, SITE_URL env, web-vitals, inline expiry sweeps, in-memory limiter warning, migration-on-boot note when scaling, image slim root Dockerfile, test file naming, ruff on scripts, mock-credentials verification, payment localhost allowlist, inactive-user oracle, etc.

---

## 5. Contradiction resolution across phases

| Tension | Resolution |
|---|---|
| v1: “append-only ledgers” vs ARCH: cascade deletes | Ledgers are **conventionally** append-only; schema allows CASCADE — Architecture wins; do not claim append-only without CHECK/REVOKE. |
| v1 Security 7.5 vs Backend money-path High bugs | Security posture ≠ payment state-machine correctness. Both scored; overall pulled by BE-20 cluster. |
| “FE tests absent” vs files on disk | Census corrected: tests exist, CI does not run them. Severity remains High/P1 for write-path gaps. |
| Staging Dockerfile prod-only vs root Dockerfile with dev deps | Live path uses staging Dockerfile — OPS-06 severity lowered for *deployed* image; root still wrong. |
| Dependabot present vs “no supply-chain” | Dependabot credit applied; CI audit scanners still missing (SEC-30 / OPS-05 revised). |
| Documentation volume vs accuracy | Volume is a strength; **currency discipline** is the defect. Score 4.5 reflects misleading front door, not empty corpus. |
| Accessibility “fundamentals good” vs 5.5 | Fundamentals keep it out of 3–4; concrete megamenu/form gaps + no live axe forbid 7. |

---

## 6. Technical debt report

- **Deliberate, documented debt (healthy):** crud shims (though now primary import path — ARCH-24), `redirect_slashes=False`, phase-named tests, single product router aggregator — pay down opportunistically.
- **Accidental debt (needs owners):** `scripts/` pricing sprawl; transaction ownership; stock_quantity legacy surface (column + endpoints + admin bulk UI + FE types); stale doc corpus; deploy-time FE mutation.
- **Interest currently being paid:** deploy-time discovery of FE type errors; manual Hesabfa invoice reconciliation; every doc reader mis-learning inventory/auth; admin availability regressions.

---

## 7–13. Roadmaps (compressed)

### Wave 0 (1 week) — existential + money
1. Offsite backups + restore drill (OPS-02)
2. Hard smoke gate; remove admin `|| true` (OPS-20)
3. Rotate secrets (SEC-09); fix example PIN / gitignore (SEC-28/24)
4. Design+test fix for BE-20 (do not ship gateway without it)

### Wave 1 (3–4 weeks) — correctness + gates
BE-01/02/21/22 · DB-01 · OPS-01/03/04/07/21 · FE-A-20/21 · FE-S-01 · DOC front-door cluster · OTP SEC-20/04 · QA-26 regressions · FE typecheck+CI

### Wave 2 (4–6 weeks) — integrity + hardening
SEC CSRF/SSRF/SVG/uploads · DB CHECKs + search indexes · BE timeout UNKNOWN · Hesabfa retry · a11y pass · admin noindex · Dependabot audit gates

### Wave 3 — scale + SEO + depth
PLP SSR · slug URLs · coverage ratchet · scripts consolidation · job runner extraction · real staging host

---

## 14. Risks if nothing changes

1. **Total data loss** on single disk failure (backups co-located).
2. **Silent production breakage** — no staging, soft smoke, no FE CI, no alerts.
3. **Money loss / reconciliation hell** — BE-20 double-refund window when gateway goes live.
4. **Accounting drift** — mutable order lines + unretried Hesabfa invoices.
5. **Wrong systems built from docs** — AI_CONTEXT / README / openapi teaching abandoned inventory and dead endpoints.
6. **SEO ceiling** — 5,900 PDPs without Product schema; CSR category lists.
7. **Auth weakness understated** — 5-digit unsalted OTP if `otp_codes` ever leaks.

---

## 15. Strengths (unchanged in kind; re-verified)

1. Boot-time production-config validation (best-in-class for size).
2. Payment substrate: locking, idempotency, ledgers, allowlists, capability-token verify (correctness bugs sit *on top* of a good substrate).
3. Session/auth architecture (incl. admin memory+HttpOnly + HMAC soft session).
4. Risk-weighted backend tests + enforced coverage floor.
5. Correct PDP SSR/hydration + metadata/sitemap/robots + native RTL.
6. Disciplined DB patterns: partial uniques, tz triggers, hashed secrets at rest, selectinload hygiene.
7. Honest workflow comments (“staging = live”) and accurate ops docs (`HESABFA.md`, `OPERATIONS.md`, `COLLABORATOR_DEPLOY.md`).
8. Dependabot enabled; Vitest/Playwright harnesses started (need CI).

---

## 16. Weaknesses (strict)

1. Disaster-recovery posture (same-disk backups, no drills).
2. Release gating theater (soft smoke, staging=live, deploy-time FE mutation).
3. Zero alerting; metrics possibly public.
4. Documentation currency failure at the front door.
5. Money-path concurrency/refund state machine.
6. Frontend write-path testing void (harness without enforcement + shallow admin units).
7. Transaction-boundary inconsistency.
8. Catalog search/filter scalability + stock semantic drift across FE/docs.
9. OTP entropy + secret-example footguns.
10. `scripts/` as unmanaged pricing layer.

---

## 17. External-reviewer verdict (hostile)

**Stripe:** Would open `payment.py` refund path and the bare `except Exception: commit` on callback — then ask where the regression tests for shipped→refund and concurrent verify+sweep are. Would credit the idempotency reservation pattern.

**Shopify:** “When a merchant renames a product, what happens to last month’s invoices?” — DB-01 + Hesabfa fallback to live price. Would also ask why admin still offers quantity-delta bulk after binary availability.

**Google SRE:** Would stop at backups (same disk), alerting (none), and staging (is production). Conversation over until Wave 0.

**Cloudflare:** Chunked body bypass, SSRF DNS gap, SVG uploads, unauthenticated metrics, single VPS edge story — plus compliment fail-closed rate limiter.

**Microsoft:** 242 backend tests vs ungated shallow FE tests; mypy with major error codes disabled; docs that contradict code; 35 scripts owning pricing — maintainable by exactly the two people who wrote it.

**Common thread:** None would call the core craft bad. Every first criticism lands on **operational shell, documentation honesty, and money-path edge cases** — not on “can these people write FastAPI/Next.js.”

---

## 18. Score delta highlights (quick)

| Biggest drops | Δ | Why |
|---|---:|---|
| Documentation | −2.5 | Dedicated phase; front-door drift verified |
| Accessibility | −1.5 | Provisional banned; concrete gaps |
| Security | −1.5 | OTP width + secret footguns + upload/SVG |
| Architecture | −1.5 | Layering/own Done criteria failed; money-path architecture |
| SEO | −1.0 | JSON-LD + CSR PLP under commerce ceiling |
| Overall | −1.1 | Ops + money-path + docs dominate |

| Small rises / corrections | Δ | Why |
|---|---:|---|
| Admin auth/session | +0.5 | HMAC middleware real |
| Frontend testing subscore | +2.0 | Tests exist (still overall Testing −0.5 after ungated + money-path gaps) |

---

## 19. Phase report index

| File | Status |
|---|---|
| `00-audit-plan-v2.md` | ✅ |
| `architecture-audit.md` | ✅ |
| `documentation-audit.md` | ✅ |
| `database-audit.md` | ✅ |
| `backend-audit.md` | ✅ |
| `security-audit.md` | ✅ |
| `frontend-storefront-audit.md` | ✅ |
| `frontend-admin-audit.md` | ✅ |
| `devops-audit.md` | ✅ |
| `testing-quality-audit.md` | ✅ |
| `master-engineering-report-v2.md` | ✅ (this file) |

**Ship rule:** docs-only under `docs/audits/v2/`; no application code changes in this PR.
