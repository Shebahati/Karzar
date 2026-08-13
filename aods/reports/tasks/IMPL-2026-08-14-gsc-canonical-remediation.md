# Task record — IMPL-2026-08-14-gsc-canonical-remediation

| Field | Value |
|-------|-------|
| **NODE_ID** | IMPL-2026-08-14-gsc-canonical-remediation |
| **PROMPT** | aods/70-prompts/impl/IMPL-frontend-route.prompt.md |
| **TASK_ID** | SEO-004 (defect follow-up; not a new PMO ID) |
| **CHANGE_CLASS** | C1 |
| **ARCHETYPE** | IMPL (+ bundled TEST per human brief) |
| **STATUS** | COMPLETE — local; merge/deploy pending HC-07/HC-11 |
| **Date** | 2026-08-14 |
| **Merge base** | `origin/main` @ `396ae0a25710b0ad366ac402fef6a123ef16403a` |

## Goal

Stop Root Layout from imposing `https://www.karzartools.com/` as canonical on every descendant page. Give existing indexable static routes explicit self-canonicals. Preserve product id→slug 301, facet noindex, private noindex, and sitemap public-URL hygiene without KIH/KF contract changes.

## Authority (origin/main)

- `docs/architecture/adr/ADR-010-seo-url-contract.md:64-68` — `/product/{slug}` canonical; 301 from id; faceted URLs are not hubs; JSON-LD `@id` aligned
- `docs/architecture/rfc/RFC-004-slug-migration-and-redirects.md:40,60` — permanent 301 id→slug
- `docs/architecture/information-architecture/url-map.md:12-27` — static indexable; utilities noindex; catalog facets not entity hubs
- `docs/architecture/CANON-LOCK.md:35` — ADR-010 binds URL/canonical/JSON-LD changes
- Runtime defect: `frontend/Storefront/src/app/layout.tsx` previously set `alternates.canonical: SITE_URL`

## Files changed

1. `frontend/Storefront/src/app/layout.tsx` — removed global canonical
2. `frontend/Storefront/src/app/page.tsx` — homepage self-canonical `/`
3. `frontend/Storefront/src/app/about/page.tsx` — self-canonical `/about`
4. `frontend/Storefront/src/app/contact/page.tsx` — self-canonical `/contact`
5. `frontend/Storefront/src/app/terms/page.tsx` — self-canonical `/terms`
6. `frontend/Storefront/src/app/faq/page.tsx` — self-canonical `/faq`
7. `frontend/Storefront/src/app/blog/page.tsx` — self-canonical `/blog`
8. `frontend/Storefront/src/app/categories/page.tsx` — self-canonical `/categories`
9. `frontend/Storefront/src/app/catalog/page.tsx` — uses shared self-canonical helper
10. `frontend/Storefront/src/app/product/[slug]/page.tsx` — uses `numericProductRedirectPath`
11. `frontend/Storefront/src/app/sitemap.ts` — `SITEMAP_STATIC_PATHS` + `productPath`
12. `frontend/Storefront/src/lib/crawl-hygiene.ts` — canonical/sitemap constants + helper
13. `frontend/Storefront/src/lib/product-url.ts` — `numericProductRedirectPath`
14. Tests: `seo-canonical.test.ts`, `crawl-hygiene.test.ts`, `product-url.test.ts`
15. PMO: `tasks.json`, `TECHNICAL_SEO_PROGRESS.md`, `CHANGELOG.md`
16. This record

## Non-goals (honoured)

- No KIH/KF product, image, knowledge, ID, slug, or API contract change
- No bulk slug rename; no indexing gated on image or KF content
- No fake aggregateRating/reviews
- No merge, push, or production deploy in this node
- `/privacy` remains a FAQ redirect (runtime truth); not given an indexable self-canonical
- `/categories` index not added to sitemap (conservative; page now has self-canonical)

## Open questions (not invented)

1. Sitemap `listProducts` public-API active/unavailable semantics — owned by the catalog API. This node did not add an extra “must have image / KF content / is_active” filter.

## Verify

See completion report in the implementing session. Commands: Storefront `typecheck`, `lint`, `test`, `build`; `python3 aods/tools/aods_validate.py`.
