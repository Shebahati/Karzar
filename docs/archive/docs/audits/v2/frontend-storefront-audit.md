# Phase — Storefront Audit (v2, strict)

**Date:** 2026-07-25 · **Auditors:** Staff Frontend / SEO / Accessibility team (hostile due-diligence)
**Baseline:** v1 `docs/audits/frontend-storefront-audit.md` (SEO 6.5, a11y 7 provisional, UX 8, rendering 7, code quality 8)
**Branch:** `docs/engineering-audit-2026-07` @ `66e9ae9`
**Method:** Full read of `layout.tsx`, `sitemap.ts`, `robots.ts`, `product/[id]/page.tsx`, catalog/category pages, checkout steps, megamenu/header, Field primitive; greps for `application/ld+json`, `aria-*`, `<img`, test files; census of Vitest/Playwright (excl. `node_modules`). No live axe/Lighthouse — a11y scored on **static evidence only** (provisional scores banned).

---

## 1. What is genuinely good (re-verified)

1. **PDP SSR is real:** React Query prefetch + `HydrationBoundary` (`product/[id]/page.tsx:39–50`); `generateMetadata` for title/description/OG/canonical.
2. **SEO plumbing end-to-end:** `robots.ts`, `sitemap.ts` (static + categories + blog with real lastmod + products), `metadataBase`, title template, `fa_IR` OG locale. Routed pages export metadata.
3. **A11y fundamentals present:** `lang="fa" dir="rtl"` (`layout.tsx:55`), skip-link (`:63–65` + `globals.css:201–218`), `#main-content tabIndex={-1}` (`:70`), ~88 `aria-*` hits, mobile category menu uses `useFocusTrap`, filter drawer traps focus, several filter widgets set `aria-expanded`.
4. **Zero raw `<img>`** — `next/image` everywhere; self-hosted IRANYekanX woff2 with `font-display: swap`.
5. **State handling disciplined:** PDP skeleton/error/not-found; catalog Suspense + skeleton; global `error.tsx` / `loading.tsx` / `not-found.tsx`.
6. **Tests exist that v1 missed:** **8** Vitest files / **38** cases under `src/**/__tests__/` + `e2e/checkout-smoke.spec.ts` + `playwright.config.ts` + `vitest.config.ts`. (Still ungated in CI — see testing/devops phases.)
7. **No Hesabfa UI remnants** in Storefront (`rg hesabfa` → 0). CTAs gate on `availability` (`two-lane-actions.tsx`).

---

## 2. Critique of the v1 report

| Issue | Verdict |
|---|---|
| Accessibility **7.0 provisional** | **Forbidden under v2.** Static evidence shows concrete megamenu/form gaps → **5.5** (static only; live unverified). |
| “0 storefront tests” (via QA phase) | **Wrong** — 38 unit + 1 e2e exist on this branch/main lineage. |
| SEO 6.5 | Directionally right on JSON-LD/slug/PLP; too generous once PLP *and* category hubs are CSR and Product schema absent on 5,900 PDPs. |
| Stock semantics | Missed FE still modeling `stock_quantity` / `low_stock` / «موجودی محدود» after binary-availability pivot. |
| Doc drift | Missed `AI_CONTEXT.md` / `FRONTEND_INTEGRATION.md` actively teaching wrong auth/stock. |

---

## 3. Findings register

### Re-verified v1 findings

#### FE-S-01 — No Product structured data (JSON-LD)
- **Severity:** High · **Category:** SEO/Structured data · **Location:** PDP `src/app/product/[id]/page.tsx`; sole LD emit `src/app/blog/[slug]/page.tsx:107`
- **Evidence:** Repo-wide `application/ld+json` only on blog (`Article`/`BreadcrumbList`/`FAQPage` at `:57–98`). PDP has prefetch + metadata only — no Product/Offer schema.
- **Why / Risk / Impact:** Highest-leverage SEO asset for a 5,900-SKU catalog is missing; competitors with schema win SERP real estate.
- **Root cause:** Schema work stopped at blog.
- **Recommended:** `Product`+`Offer` (IRR, availability from `is_available`) + `BreadcrumbList` on PDP; `ItemList` on category; `Organization`+`WebSite`/`SearchAction` in root layout. **Alternative:** Merchant feed only (weaker organic). **Effort:** S–M · **Priority:** **P1** · **Dependencies:** stable price/availability contract.

#### FE-S-02 — Product URLs are ID-only despite slugs existing
- **Severity:** Medium · **Category:** SEO/IA · **Location:** `/product/{id}`; links e.g. `product-card.tsx:37`; `sitemap.ts:24`; canonical `product/[id]/page.tsx:27`
- **Evidence:** All hrefs `/product/${product.id}`; backend maintains unique product slug.
- **Recommended:** `/product/{id}-{slug}` + 301 + canonical. **Effort:** M · **Priority:** P2 · **Dependencies:** slug on list/detail DTOs.

#### FE-S-03 — PLP (and category hub grids) are client-rendered
- **Severity:** Medium · **Category:** SEO/Performance · **Location:** `app/catalog/page.tsx:13–18` → `CatalogView`; `CategoryHubView` → `CatalogView`
- **Evidence:** No `prefetchQuery`/`HydrationBoundary` on catalog (contrast home `page.tsx:13–43`, PDP). Category hub SSRs shell; product grid CSR.
- **Recommended:** Server-prefetch page 1 per category/default; keep filters client. **Effort:** M · **Priority:** P2.

#### FE-S-04 — Sitemap product `lastModified` is generation time
- **Severity:** Low · **Category:** SEO · **Location:** `sitemap.ts:23–28`
- **Evidence:** Products use `lastModified: now`; blog uses `published_at` (`:72`).
- **Recommended:** Expose `updated_at` on list API; pass through. **Effort:** S · **Priority:** P3.

#### FE-S-05 — Hardcoded site origin in multiple places
- **Severity:** Low · **Category:** Config hygiene · **Location:** `layout.tsx:14`, `sitemap.ts:4`, `robots.ts:10–11`, `blog/[slug]/page.tsx:8`
- **Evidence:** Literal `https://www.karzartools.com`; no staging noindex branch in `robots.ts`.
- **Recommended:** Single `SITE_URL` env; staging `robots` noindex. **Effort:** S · **Priority:** P3.

#### FE-S-06 — Static article data duplicated with CMS
- **Severity:** Low · **Category:** Content architecture · **Location:** `src/data/articles/how-to-read-vernier-caliper.ts` via `mock-data.ts:12`
- **Recommended:** CMS-only; mock fixtures from API shape. **Effort:** S–M · **Priority:** P3.

#### FE-S-07 — Accessibility: static gaps now concrete; live pass unverified
- **Severity:** Medium · **Category:** Accessibility (WCAG 2.2) · **Location:** Megamenu, checkout `Field`, filters
- **Evidence:** Fundamentals good (skip-link, RTL, mobile traps). Gaps: desktop mega trigger lacks `aria-expanded`/`aria-controls` (`site-header.tsx:102–115`); panel `role="region"` only (`mega-menu.tsx:66–67`); Escape close but **no** desktop focus trap (`mega-menu.tsx:42–46`); `Field` never sets `aria-invalid`/`aria-describedby` (`field.tsx:4–28`; storefront `rg aria-describedby` → **0**). Live axe/keyboard **unverified**.
- **Recommended:** axe + keyboard day on megamenu/PLP/checkout/OTP; wire disclosure pattern + error association. **Effort:** S (audit) + S–M (fixes) · **Priority:** P2.

#### FE-S-08 — No web-vitals monitoring
- **Severity:** Low · **Category:** Performance observability
- **Evidence:** GA/GTM present; no `useReportWebVitals`; no `ANALYZE` bundle script.
- **Recommended:** Report CWV → GA4; optional bundle analysis. **Effort:** S · **Priority:** P3.

---

### New findings (v2)

#### FE-S-20 — Desktop megamenu a11y incomplete vs mobile
- **Severity:** Medium · **Category:** Accessibility · **Location:** `site-header.tsx:102–115`, `mega-menu.tsx`
- **Evidence:** Trigger toggles `megaOpen` without `aria-expanded`/`aria-haspopup`/`aria-controls`; hover-open; mobile counterpart uses `useFocusTrap` + `aria-modal`.
- **Why / Impact:** Asymmetric a11y; keyboard/AT users lose category discovery on desktop.
- **Recommended:** Disclosure pattern with `aria-expanded`, focus trap when open, restore focus on close. **Effort:** S–M · **Priority:** P2 · **Dependencies:** FE-S-07.

#### FE-S-21 — Checkout/forms lack programmatic error association
- **Severity:** Medium · **Category:** Accessibility · **Location:** `components/ui/field.tsx`; checkout `details-step.tsx`, `auth-step.tsx`
- **Evidence:** Errors as sibling `<span>` with no `id`/`aria-describedby`; Field wrapper sets neither `aria-invalid` nor describedby.
- **Recommended:** Generate ids; wire `aria-describedby` + `aria-invalid`. **Alternative:** `role="alert"` live region on submit. **Effort:** S · **Priority:** P2.

#### FE-S-22 — Stock semantics still quantity/`low_stock`-shaped (binary-availability drift)
- **Severity:** Medium · **Category:** Domain/UX consistency · **Location:** `types/product.ts:76–80`, `mock-api.ts:124–128`, `filter-panel.tsx:343–348`, PDP badge
- **Evidence:** Detail type keeps `stock_quantity`/`low_stock`; mock `stockStatus` returns «موجودی محدود» from quantity; PLP filter «موجودی»/`in_stock`. CTAs correctly gate on `availability`.
- **Why / Impact:** Users see warehouse-tier copy after business abandoned quantity UX; trust inconsistency with admin («تعداد فقط در حسابفا»).
- **Recommended:** Binary labels only; drop low_stock UI; treat `stock_quantity` as deprecated wire field. **Effort:** S–M · **Priority:** P2 · **Dependencies:** FRONTEND_INTEGRATION rewrite.

#### FE-S-23 — Doc drift vs `AI_CONTEXT.md` / `FRONTEND_INTEGRATION.md`
- **Severity:** Medium · **Category:** Documentation · **Location:** `frontend/AI_CONTEXT.md`, `docs/FRONTEND_INTEGRATION.md`
- **Evidence:** AI_CONTEXT claims admin tokens in `localStorage`, «بدون refresh token», ComingSoon for live domains; FRONTEND_INTEGRATION: `low_stock` «quantity < 10», `availability = is_active && stock_quantity > 0` — contradicts binary `is_available`. Code: memory tokens + refresh.
- **Why / Impact:** Agents/devs implement wrong auth/stock; reopen quantity regressions.
- **Recommended:** Rewrite auth + stock sections; mark ComingSoon rows done. **Effort:** S · **Priority:** **P1** · **Dependencies:** documentation phase (DOC-*).

#### FE-S-24 — Private routes lack meta `noindex` (robots.txt only)
- **Severity:** Low · **Category:** SEO hardening · **Location:** `robots.ts:5–8`; account/checkout/login pages
- **Evidence:** `disallow` for private paths; `rg robots:` under Storefront `src` → **0** metadata robots.
- **Recommended:** `robots: { index: false }` on account/checkout/cart/login. **Effort:** S · **Priority:** P3.

#### FE-S-25 — Production GA4 ID in `.env.example`
- **Severity:** Low · **Category:** Config hygiene · **Location:** `frontend/Storefront/.env.example:13–17`
- **Evidence:** `NEXT_PUBLIC_GA_MEASUREMENT_ID=G-7LLQJ74Y4F` active by default; every fork/local build can fire production analytics.
- **Recommended:** Placeholder ID; document mutual exclusion with GTM. **Effort:** S · **Priority:** P3.

#### FE-S-26 — Test harness exists but commerce/SEO paths largely untested
- **Severity:** Medium · **Category:** Quality · **Location:** 8 unit files; `e2e/checkout-smoke.spec.ts`
- **Evidence:** 38 unit cases (validation, cart lanes, nav-groups, idempotency, payment-url, catalog-params); 1 Playwright mock checkout smoke. No coverage for megamenu a11y, JSON-LD, PLP SSR, slug URLs. **v1 storefront audit omitted this entirely.**
- **Recommended:** PDP metadata/JSON-LD snapshot tests; expand e2e to PLP add-to-cart; gate in FE CI. **Effort:** M · **Priority:** P2 · **Dependencies:** OPS-04.

#### FE-S-27 — Zero raw `<img>`; `next/image` confirmed *(positive)*
- **Severity:** Info · **Category:** Performance
- **Evidence:** `rg '<img\b'` → none across components; `next/image` in cart/gallery/card/hero/blog.

#### FE-S-28 — Metadata coverage solid; Organization JSON-LD absent at root
- **Severity:** Low · **Category:** SEO · **Location:** `app/**/page.tsx`, `layout.tsx:16–42`
- **Evidence:** Static/`generateMetadata` on catalog, product, category, blog, about, contact, legal, checkout; no root JSON-LD.
- **Recommended:** Root `Organization`/`WebSite` with FE-S-01. **Effort:** S · **Priority:** P2 · **Dependencies:** FE-S-01.

---

## 4. Doc-drift table (storefront-facing)

| Doc | Claim | Reality | Verdict |
|---|---|---|---|
| `FRONTEND_INTEGRATION.md:94–96` | `low_stock` when qty&lt;10; availability from stock qty | `low_stock=False` always in presenter; availability from `is_available` | **Drift** |
| `AI_CONTEXT.md` auth/stock sections | LS tokens; no refresh; ComingSoon commerce | Memory+cookie; refresh live; commerce live | **Major drift** |
| Storefront README | Env table | Matches `config/env.ts` | Accurate |
| Auth cookie contract | Cookie names/paths | Matches `auth_cookies.py` | Accurate |

---

## 5. Scores (0–10, strict)

| Category | v1 | v2 | Delta justification |
|---|---|---|---|
| SEO | 6.5 | **5.5** | −1.0. Plumbing excellent; Product JSON-LD absent on 5.9k PDPs + CSR PLP/category grids + slugless URLs cap commerce SEO under acquisition bar. |
| Accessibility | 7.0 provisional | **5.5** (static only) | −1.5. Provisional banned; concrete megamenu/form gaps; live axe unverified — score what evidence supports. |
| UX & states | 8.0 | **7.5** | −0.5. Skeletons/errors solid; stock-label drift (FE-S-22). |
| Rendering/performance posture | 7.0 | **6.5** | −0.5. PDP pattern right; category hubs also CSR lists. |
| Frontend code quality | 8.0 | **7.5** | −0.5. Strict TS + RQ hydration; types/docs lag binary availability. |
| Testing (new sub-score) | — | **5.0** | 38 unit + 1 e2e; v1 missed; thin on SEO/UI; ungated in CI. |
| **Storefront overall** | **7.5** | **6.5** | −1.0. Strong shell; SEO ceiling + a11y evidence gaps + stock drift pull below v1. |

**Unverified live (explicit):** contrast of brand red, megamenu focus order end-to-end, OTP target sizes, real LCP on PLP, Search Console indexing of private URLs.

---

## 6. Self-review

- Confirmed PDP truly server-renders (HydrationBoundary) — not SEO theater.
- Confirmed JSON-LD is blog-only (single hit).
- Confirmed desktop megamenu lacks `aria-expanded` while filters/mobile menus often have it.
- Confirmed Vitest census (8 files) — v1/QA undercount corrected.
- Did **not** run axe/Lighthouse; FE-S-07/20/21 priced on static evidence only.
- Did **not** claim Hesabfa UI remnants in Storefront — none found.
