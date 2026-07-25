# Phase 5 — Storefront Audit (Next.js, SEO, Accessibility, UX)

**Date:** 2026-07-25 · **Auditors:** Staff Frontend Engineer, Technical SEO Specialist, Accessibility Expert, Senior Product Designer, UX Researcher
**Scope:** `frontend/Storefront` — App Router structure, rendering strategy, SEO artifacts, accessibility, loading/error/empty states, RTL/Persian correctness, performance posture.
**Method:** Full read of `layout.tsx`, `sitemap.ts`, `product/[id]/page.tsx`, `catalog/page.tsx`; greps for images/aria/state handling; route census.

---

## 1. What is genuinely good (verified)

1. **Rendering strategy is correct for commerce SEO.** PDP does server-side
   React Query prefetch + `HydrationBoundary` (`product/[id]/page.tsx:39–50`),
   so product HTML ships rendered; `generateMetadata` fetches the product for
   per-page title/description/OG image/canonical.
2. **SEO plumbing exists end-to-end:** `robots.ts`, `sitemap.ts` (static +
   categories with product-count filter + blog with real lastmod + products,
   paginated with a runaway-API cap), `metadataBase`, title template, `fa_IR`
   OG locale, canonical on all indexed routes. Every route exports metadata
   (15/15 checked).
3. **Accessibility fundamentals are present, not bolted on:** `lang="fa"
   dir="rtl"` at the root, a skip link to `#main-content` with `tabIndex={-1}`
   target, 88 `aria-` attributes across components, focus-visible styles in the
   design system.
4. **Zero raw `<img>` tags** — `next/image` everywhere (14 component files);
   self-hosted IRANYekanX woff2 with `font-display: swap` (no external font
   CDN dependency — matters for Iranian networks).
5. **State handling is disciplined:** PDP has skeleton, error, and not-found
   branches; catalog wraps `useSearchParams` in Suspense with a proper skeleton
   grid fallback; global `error.tsx`, `loading.tsx`, `not-found.tsx` exist.
6. **Mobile UX is deliberate:** fixed bottom nav with
   `env(safe-area-inset-bottom)` clearance, viewport-fit cover, theme color.
7. **Analytics is CSP-aware** (nonce passed from middleware into GTM/GA heads)
   and GTM/GA are mutually exclusive by documented convention.

## 2. Findings

### FE-S-01 — No Product structured data (JSON-LD)
- **Severity:** High (for SEO) · **Category:** SEO/Structured data · **Location:** PDP; JSON-LD exists only in `blog/[slug]/page.tsx`
- **Evidence:** Repo-wide search finds `application/ld+json` only in the blog route. No `Product`, `Offer`, `AggregateRating`, `BreadcrumbList`, or `Organization` schema anywhere.
- **Why problematic:** Rich results (price, availability, ratings in SERPs) are the highest-leverage SEO asset for an e-commerce catalog of 5,900 products. Competitors with schema win the SERP real estate.
- **Recommendation:** Emit `Product` + `Offer` (price in IRR with `priceCurrency`, availability from `is_available`) + `BreadcrumbList` on PDP; `ItemList` on category pages; `Organization` + `WebSite` (with SearchAction) in the root layout.
- **Effort:** S–M · **Priority:** P1

### FE-S-02 — Product URLs are ID-only despite slugs existing
- **Severity:** Medium · **Category:** SEO/IA · **Location:** `/product/{id}` routes; `products.slug` column is populated and unique
- **Evidence:** Sitemap and all links use `/product/123`; the backend already maintains a unique `slug` per product.
- **Why problematic:** Keyword-free URLs forfeit relevance signals and readable share links; the data to fix it already exists.
- **Recommendation:** Move to `/product/{id}-{slug}` (ID prefix keeps lookup O(1) and tolerates slug edits; 301 old URLs). Canonicals make the migration safe.
- **Effort:** M · **Priority:** P2

### FE-S-03 — PLP content is client-rendered
- **Severity:** Medium · **Category:** SEO/Performance · **Location:** `app/catalog/page.tsx` → `CatalogView` (client, `useSearchParams`)
- **Evidence:** Unlike the PDP, the catalog list has no server prefetch — first paint is a skeleton grid; product names/links enter the DOM only after client fetch.
- **Why problematic:** Category/catalog pages are the primary crawl paths to 5,900 PDPs. Google renders JS but with crawl-budget cost and delay; other crawlers (and users on slow connections) see skeletons.
- **Recommendation:** Server-prefetch page 1 of the product list per category (same HydrationBoundary pattern already used on PDP); keep filters client-side.
- **Effort:** M · **Priority:** P2

### FE-S-04 — Sitemap product `lastModified` is generation time
- **Severity:** Low · **Category:** SEO · **Location:** `sitemap.ts:23–28`
- **Evidence:** All product entries get `lastModified: now` on every generation; blog entries use real `published_at` (the right pattern is already in the file).
- **Why problematic:** Fake freshness teaches crawlers to distrust lastmod, reducing recrawl efficiency for actually-updated products.
- **Recommendation:** Expose `updated_at` in the product list API (it exists on every row via `Base`) and pass it through.
- **Effort:** S · **Priority:** P3

### FE-S-05 — Hardcoded site origin in two places
- **Severity:** Low · **Category:** Config hygiene · **Location:** `layout.tsx:14`, `sitemap.ts:4`
- **Evidence:** `https://www.karzartools.com` is a literal in both files; staging deployments emit production canonicals/sitemap URLs.
- **Why problematic:** Staging pages canonicalizing to production is actually *desirable* for duplicate-content safety, but a staging sitemap advertising production URLs is noise; and any domain change touches N files.
- **Recommendation:** Single `SITE_URL` from env with production fallback; ensure staging sets `robots` to noindex (verify `robots.ts` behavior per environment).
- **Effort:** S · **Priority:** P3

### FE-S-06 — Static article data duplicated with CMS (cross-ref ARCH-04)
- **Severity:** Low · **Location:** `src/data/articles` vs backend CMS
- **Recommendation:** Single source; prefer CMS. · **Effort:** S–M · **Priority:** P3

### FE-S-07 — Accessibility depth not verified beyond static analysis
- **Severity:** Medium (unknown) · **Category:** Accessibility (WCAG 2.2)
- **Evidence:** Static signals are good (skip link, aria usage, focus styles), but we could not run axe/lighthouse in this audit pass. Specific WCAG 2.2 risks typical for this stack remain unverified: contrast of the red-on-white brand palette for small text, focus order in the mega-menu, `aria-expanded` state on mobile nav, form error association (`aria-describedby`) in checkout, target size (24×24) for mobile filter chips.
- **Recommendation:** Run axe-core + keyboard-only pass on: megamenu, PLP filters, checkout form, OTP login. Budget one day; fix list will be concrete.
- **Effort:** S (audit) · **Priority:** P2

### FE-S-08 — No web-vitals monitoring
- **Severity:** Low · **Category:** Performance observability
- **Evidence:** GA/GTM present, but no `useReportWebVitals`/CrUX wiring; no bundle-analyzer script in `package.json`.
- **Recommendation:** Add `useReportWebVitals` → GA4 events; add `ANALYZE=true` bundle analysis to CI on demand.
- **Effort:** S · **Priority:** P3

## 3. Self-challenge

- Verified PDP truly server-renders (HydrationBoundary + prefetch, not a bare client component) — the strongest counter-evidence to "SPA with SEO theater".
- Checked all 15 routed pages export metadata — none missing.
- Tried to find raw `<img>`/external font/CDN dependencies — none found.
- Could not execute Lighthouse/axe in this environment; FE-S-07 explicitly scopes what remains unproven.

## 4. Scores

| Category | Score | Justification |
|---|---|---|
| SEO | **6.5/10** | Excellent plumbing (metadata/sitemap/canonical/robots), but missing Product JSON-LD and slugless URLs cap the ceiling for a catalog business. |
| Accessibility | **7/10** (provisional) | Strong fundamentals; unverified interactive-widget behavior. |
| UX & states | **8/10** | Skeletons/error/empty everywhere we looked; mobile ergonomics deliberate. |
| Rendering/performance posture | **7/10** | PDP pattern is right; PLP client-only rendering is the gap. |
| Frontend code quality | **8/10** | TS strict, feature-sliced, React Query with SSR hydration, no raw img. |
