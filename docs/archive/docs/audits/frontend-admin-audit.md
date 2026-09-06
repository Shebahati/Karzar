# Phase 6 — Admin Panel Audit (Next.js)

**Date:** 2026-07-25 · **Auditors:** Staff Frontend Engineer, Security Engineer, QA Lead
**Scope:** `frontend/admin-panel` — feature architecture, auth token handling, mock mode, error handling, test coverage.
**Method:** Full read of `src/lib/api-client.ts` (auth-critical), structure census of `src/features`, mock-mode grep, test census, tsconfig review.

---

## 1. What is genuinely good (verified)

1. **Token handling is the correct browser pattern, not the common mistake.**
   In live mode, access/refresh tokens live **in memory only** with HttpOnly
   cookies as transport (`withCredentials: true`); `localStorage` is used
   exclusively in mock mode, and the client actively **purges legacy
   localStorage tokens** on first use (`api-client.ts:49–55`). XSS token
   exfiltration from storage is structurally prevented.
2. **Refresh logic is production-grade:** single-flight refresh promise
   (prevents thundering-herd refresh on parallel 401s), near-expiry proactive
   refresh before each request, `Retry-After` header parsing (both seconds and
   HTTP-date forms) surfaced into typed `ApiError` with field-error mapping
   that matches the backend envelope exactly.
3. **Feature-sliced structure** (`features/{audit,auth,catalog,cms,customers,
   hesabfa,orders,system}`) mirrors backend domains; `strict: true` TypeScript
   in both frontends.
4. **Mock mode is cleanly separated** — `USE_MOCK` gates transport, credential
   hints are dynamically imported so live bundles exclude them, and
   `withCredentials` flips accordingly.
5. **Hesabfa feature respects the business decision**: admin reads are gated
   off (`HESABFA_ADMIN_READS_ENABLED=false` server-side), and the panel no
   longer renders Hesabfa-sourced metrics.

## 2. Findings

### FE-A-01 — Effectively zero test coverage
- **Severity:** High · **Category:** Quality · **Location:** whole package — exactly **1** test file found under `src/`
- **Evidence:** `rg --files -g '*.test.*' src | wc -l` → 1. The admin panel encodes order state transitions, price editing, availability toggles, step-up PIN flows — all regression-prone, all untested. This week's availability/stock display regression reached staging and was caught by a human.
- **Why problematic:** The panel is the write-path to the catalog and orders; a UI regression here corrupts real data or blocks operations. The typecheck error that blocked Deploy Staging this week (PR #50 aftermath) would have been caught by a minimal CI test job.
- **Recommendation:** Start with the highest-risk units: `api-client` refresh logic, order status transition components, product edit form validation. Vitest + Testing Library; target the 10 files that write data. Wire `tsc --noEmit` + tests into CI as a PR gate (see DevOps phase).
- **Effort:** M · **Priority:** P1

### FE-A-02 — No route-level authorization guard beyond API 401s
- **Severity:** Medium · **Category:** Security/UX · **Location:** `src/middleware.ts` (present but thin), page guards
- **Evidence:** Auth enforcement relies on API calls failing with 401 and the client redirecting; there is no server-side session check in Next middleware (it cannot read the HttpOnly cookie's validity without an API roundtrip — inherent to the design).
- **Why problematic:** Not a data-exposure hole (API enforces authz), but unauthenticated visits briefly render admin chrome/skeletons before redirect — information architecture leaks (menu labels, feature names) and jarring UX.
- **Recommendation:** Middleware check for cookie *presence* (fast, no validation) to redirect obviously-unauthenticated visitors; keep API as the real gate.
- **Effort:** S · **Priority:** P3

### FE-A-03 — Admin panel not indexed-protection unverified
- **Severity:** Low · **Category:** Hardening
- **Evidence:** Admin runs on a separate (sub)domain in staging; we did not find `robots` meta/noindex emission or an nginx-level `X-Robots-Tag` for it in the repo.
- **Recommendation:** Add `X-Robots-Tag: noindex, nofollow` at nginx for the admin host, plus basic-auth or IP allowlist as defense-in-depth for the login page.
- **Effort:** S · **Priority:** P2

### FE-A-04 — Error taxonomy handled, loading/empty states inconsistent across features
- **Severity:** Low · **Category:** UX consistency
- **Evidence:** `ApiError` mapping is excellent at the transport layer; feature-level spot checks show newer features (megamenu groups, Hesabfa) with full skeleton/error/empty states while older tables degrade to spinners. (Sampled, not exhaustive.)
- **Recommendation:** Extract a standard `AsyncTable`/`QueryBoundary` wrapper; adopt in older features opportunistically.
- **Effort:** M · **Priority:** P3

### FE-A-05 — Mock credential hint file ships in repo (cross-ref SEC-08)
- **Severity:** Info · **Location:** `src/lib/mock-credentials.ts`
- **Status:** Acceptable given dynamic import; verify no real environment seeds `Admin@123456`.

## 3. Self-challenge

- The initial hypothesis "tokens in localStorage" (suggested by grep hits) was **disproved** by reading the full client: localStorage is mock-only plus an active legacy purge. This is worth stating because a shallow audit would have reported a false critical.
- Checked `withCredentials` flows against the backend cookie paths (`/api/v1` access, `/api/v1/auth` refresh) — consistent.
- Did not run the panel against staging in this pass; findings FE-A-02/03/04 are code-level and deserve a live confirmation pass.

## 4. Scores

| Category | Score | Justification |
|---|---|---|
| Auth/session handling | **8.5/10** | Memory+HttpOnly pattern, single-flight refresh, legacy purge — best practice. |
| Architecture | **7.5/10** | Feature slicing mirrors backend; strict TS. |
| Testing | **2/10** | One test file for the platform's entire write-path UI. |
| UX consistency | **6.5/10** | Transport-level error handling excellent; view-level states uneven. |
| Admin panel overall | **6.5/10** | Well-engineered shell dragged down by absent tests. |
