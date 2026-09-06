# Phase — Admin Panel Audit (v2, strict)

**Date:** 2026-07-25 · **Auditors:** Staff Frontend / Security / QA (hostile due-diligence)
**Baseline:** v1 `docs/audits/frontend-admin-audit.md` (overall 6.5; auth 8.5; testing 2.0)
**Branch:** `docs/engineering-audit-2026-07` @ `66e9ae9`
**Method:** Full read of `src/lib/api-client.ts`, `middleware.ts`, `auth-gate.tsx`, catalog products list/edit/new, dashboard, `features/hesabfa`, mock-api stock helpers; test census (Vitest + Playwright, excl. `node_modules`); robots/noindex grep.

---

## 1. What is genuinely good (re-verified)

1. **Token handling is the correct browser pattern.** Live mode: access/refresh **in memory only** + HttpOnly cookies (`withCredentials: true`); `localStorage` mock-only with active legacy purge (`api-client.ts:43–55,57–65,226–275`). XSS token exfiltration from storage is structurally prevented.
2. **Refresh logic is production-grade:** single-flight refresh promise, near-expiry proactive refresh, `Retry-After` parsing (seconds + HTTP-date), typed `ApiError` matching backend envelope.
3. **Edge session gate is real (stronger than v1 claimed):** middleware HMAC-verifies `ADMIN_SESSION_COOKIE` via `verifyAdminSessionValue` and redirects to `/login` (`middleware.ts:45–89`). AuthGate still client-checks `/auth/me` + role.
4. **Feature-sliced structure** mirrors backend domains; `strict: true` TypeScript.
5. **Hesabfa admin-read metrics UI cleared** post PR #55 — dashboard uses website paid-sales (`useWebsitePaidSales`); no Hesabfa-sourced metrics rendered.
6. **Tests exist that v1 undercounted:** 1 Vitest file / **5** cases (`sanitize-next-path.test.ts`) + `e2e/admin-smoke.spec.ts` (login → products → step-up) + `vitest.config.ts` / `playwright.config.ts`.

---

## 2. Critique of the v1 report

| Issue | Verdict |
|---|---|
| “Effectively zero tests / 1 file” | Partially true on depth; **missed e2e smoke** and understated that Vitest harness exists. Still High severity for write-path gaps. |
| “Thin middleware” (FE-A-02) | **Overstated weakness** — HMAC session cookie verification is real. Downgrade severity. |
| Hesabfa “respects business decision” | Metrics UI yes; **missed** bulk quantity-delta UI, dual availability toggles, dashboard `low_stock` queue, unused status hook. |
| Auth 8.5 | Fair; v2 raises slightly for middleware proof. |
| Overall 6.5 | Too generous once binary-availability UX inconsistencies are priced. |

---

## 3. Findings register

### Re-verified / revised v1 findings

#### FE-A-01 — Test coverage thin (not zero) and write-path unguarded
- **Severity:** High · **Category:** Quality · **Location:** whole package
- **Evidence:** Unit: `src/lib/__tests__/sanitize-next-path.test.ts` — **5** cases. E2E: `e2e/admin-smoke.spec.ts`. **No** unit tests for `api-client` refresh, availability toggle, bulk adjust, order transitions. Vitest/e2e **ungated in CI**.
- **Why / Impact:** Panel is the write-path to catalog and orders; this week's availability/stock regressions reached live because nowhere else catches them. Foundation exists; culture has not crossed into high-risk units.
- **Recommended:** Unit-test api-client refresh + availability service mapping + order status actions; RTL for stock section; CI gate (OPS-04). **Effort:** M · **Priority:** **P1** · **Dependencies:** frontend CI.

#### FE-A-02 — Route gate improved; still not full authz *(severity)*
- **Severity:** Low–Medium (downgraded from Medium) · **Category:** Security/UX · **Location:** `middleware.ts:45–89`, `auth-gate.tsx:24–51`
- **Evidence:** Middleware HMAC-verifies soft session cookie and redirects; AuthGate checks `/auth/me` + role. Edge cannot validate HttpOnly API cookies without roundtrip — inherent to design. Skeleton chrome possible if soft cookie valid but API session dead.
- **Recommended:** Keep dual gate; shorten soft-cookie TTL; avoid rendering nav until AuthGate ready (already skeleton). **Effort:** S · **Priority:** P3.

#### FE-A-03 — Admin panel lacks noindex / X-Robots-Tag in app
- **Severity:** Medium (raised from Low) · **Category:** Hardening · **Location:** `app/layout.tsx:6–12`, `next.config.ts:61–75`
- **Evidence:** Metadata has title/description — **no** `robots: noindex`; security headers omit `X-Robots-Tag`; `rg robots|noindex` in admin-panel → **0**.
- **Recommended:** App `robots: { index:false, follow:false }` + nginx `X-Robots-Tag` + IP/basic-auth defense-in-depth. **Effort:** S · **Priority:** P2.

#### FE-A-04 — Async state patterns uneven across features
- **Severity:** Low · **Category:** UX consistency
- **Evidence:** Products/orders/quotes/contacts use pending/error/skeleton/refetch; documents still stub; older tables degrade to spinners. Transport `ApiError` remains excellent.
- **Recommended:** Shared `QueryBoundary`/`AsyncTable`. **Effort:** M · **Priority:** P3.

#### FE-A-05 — Mock credential hint ships in repo
- **Severity:** Info · **Category:** Secret hygiene · **Location:** `src/lib/mock-credentials.ts:5–8`; also embedded in `e2e/admin-smoke.spec.ts:3–5`
- **Evidence:** `passwordHint: "Admin@123456"`; dynamic-import claim in file comment.
- **Recommended:** Verify no prod seed; keep dynamic import; don't document as live password in AI_CONTEXT. **Effort:** S · **Priority:** P3 · **Dependencies:** SEC-08.

---

### New findings (v2)

#### FE-A-20 — Bulk “stock adjust” UI still quantity-delta after binary availability
- **Severity:** High · **Category:** Domain/UX · **Location:** `catalog/products/page.tsx:214–217,500–524`; `catalogService.bulkStockAdjust` (`catalog.ts:623+`)
- **Evidence:** Dialog asks for numeric delta «مثبت افزایش، منفی کاهش»; payload `quantity_delta`. Edit/create copy says warehouse qty only in Hesabfa + binary switch. Live `setProductAvailability` uses `PUT .../availability`; `adjustProductStock` maps `delta > 0` → boolean.
- **Why / Risk / Impact:** Operators believe they change warehouse counts; site only flips availability. Mis-set availability at scale; support burden; contradicts post–PR #55 business decision.
- **Root cause:** Bulk UI not rewritten after binary pivot.
- **Recommended:** Replace with موجود/ناموجود multi-select; rename copy. **Alternative:** Hide bulk until rewritten. **Effort:** M · **Priority:** **P1** · **Dependencies:** Backend bulk availability API (or N× PUT).

#### FE-A-21 — Dual availability controls on product edit
- **Severity:** Medium · **Category:** UX consistency · **Location:** `products/[id]/edit/page.tsx:293–347`
- **Evidence:** `ProductStockSection` (dedicated toggle + API) **and** form `Switch` `is_available` under «قیمت و موجودی» — two sources of truth.
- **Why / Impact:** Conflicting saves / stale form state; admin thinks save updated availability when only section toggle did (or vice versa).
- **Recommended:** One control — prefer `ProductStockSection`; remove or read-only the form field. **Effort:** S · **Priority:** **P1** · **Dependencies:** FE-A-20.

#### FE-A-22 — Dashboard «موجودی کم» / `low_stock` queue vs binary model
- **Severity:** Medium · **Category:** Domain/UX · **Location:** `(dashboard)/page.tsx:115–159`
- **Evidence:** Builds `lowStock` from `stock_status === "low_stock"`; list badge collapses to موجود/ناموجود (`products/page.tsx:46–49`). Backend presenter forces `low_stock=False`.
- **Why / Impact:** Dead/misleading ops queue → operator distrust of dashboard.
- **Recommended:** Queue only `!availability` / `out_of_stock`; or remove stock queue. **Effort:** S · **Priority:** P2.

#### FE-A-23 — Hesabfa feature module remnants after PR #55
- **Severity:** Low · **Category:** Architecture hygiene · **Location:** `features/hesabfa/`, `services/hesabfa.ts`
- **Evidence:** `useWebsitePaidSales` used on dashboard (OK). `useHesabfaStatus` **defined but unused** (`queries.ts:12–17`). `HesabfaStatus` still models sync intervals/warehouse. Copy still mentions حسابفا on stock UI. No Hesabfa metrics rendered (matches v1 positive).
- **Recommended:** Rename to `website-sales`; delete unused status hook or gate behind flag. **Effort:** S · **Priority:** P3.

#### FE-A-24 — Auth pattern re-verified: memory + HttpOnly (live); LS mock-only *(positive)*
- **Severity:** Info · **Category:** Security · **Location:** `api-client.ts:43–55,57–65,117–126,226–275`
- **Evidence:** Live memory tokens + `withCredentials: !USE_MOCK`; purge legacy LS; single-flight refresh. Disproves shallow “tokens in localStorage” critical.
- **Recommended:** Keep; update AI_CONTEXT which still claims LS-only admin auth.

#### FE-A-25 — `AI_CONTEXT.md` admin section severely stale
- **Severity:** Medium · **Category:** Documentation · **Location:** `frontend/AI_CONTEXT.md` §§7,9,14,17
- **Evidence:** Claims ComingSoon for orders/customers/reports while nav has live orders/quotes/customers/CMS/audit (`nav.config.tsx:51–75`); token-in-LS; no refresh. Phase-5 test section is accurate.
- **Recommended:** Rewrite §7–10 against current tree. **Effort:** S · **Priority:** **P1** · **Dependencies:** FE-S-23 / DOC-*.

#### FE-A-26 — Features structure still sound; commerce domains live *(positive)*
- **Severity:** Info · **Category:** Architecture · **Location:** `src/features/{audit,auth,catalog,cms,customers,hesabfa,orders,system}`
- **Evidence:** Mirrors backend; orders/customers no longer stubs (except documents «به‌زودی»).

#### FE-A-27 — Mock `stock_quantity` still drives availability in mock-api
- **Severity:** Low · **Category:** Test fidelity · **Location:** `lib/mock-api.ts:612–614,1185–1202`
- **Evidence:** Mock availability derived from numeric `stock_quantity`; live path forces `stock_quantity: "0"` in stock DTO (`catalog.ts:411–414`).
- **Why / Impact:** Mock teaches quantity semantics; FE-A-20 bugs harder to spot in mock/e2e.
- **Recommended:** Mock binary `is_available` only. **Effort:** S · **Priority:** P2 · **Dependencies:** FE-A-20.

---

## 4. Doc-drift table

| Doc | Claim | Reality | Verdict |
|---|---|---|---|
| `AI_CONTEXT.md` | ComingSoon orders/customers; LS tokens; no refresh | Live commerce; memory+cookie; refresh | **Major drift** |
| Auth cookie contract | HMAC admin session | Matches `middleware.ts` | Accurate |
| Admin README | Env / mock scoped | Matches; mock PIN on backend weak list | Accurate |
| `gaps/01` remaining BE gaps | settings/store, reports, invoice PDF | Confirmed absent in `app/api` | Accurate |

---

## 5. Scores (0–10, strict)

| Category | v1 | v2 | Delta justification |
|---|---|---|---|
| Auth/session handling | 8.5 | **9.0** | +0.5. HMAC session middleware now verified as real, not “thin.” |
| Architecture | 7.5 | **7.0** | −0.5. Feature slicing sound; Hesabfa leftovers + stock UX split. |
| Testing | 2.0 | **3.0** | +1.0. E2E + 5 unit cases v1 missed; still thin on write-path; ungated. |
| UX consistency | 6.5 | **5.5** | −1.0. Bulk qty + dual toggles + low_stock queue after binary pivot. |
| **Admin panel overall** | **6.5** | **6.0** | −0.5. Domain inconsistency outweighs auth gains under acquisition bar. |

**Unverified live:** staging indexing headers; real Hesabfa admin-reads responses; full keyboard pass on dialogs.

---

## 6. Self-review

- Initial “tokens in localStorage” hypothesis **disproved** by full client read — stated explicitly because shallow audits get this wrong.
- Cookie paths checked against backend (`/api/v1` access, `/api/v1/auth` refresh) — consistent.
- Bulk quantity UI and dashboard low_stock are the largest **new** post–PR #55 consistency failures — v1 missed both.
- Did not run the panel against staging in this pass; FE-A-03/20 deserve a live confirmation pass.
