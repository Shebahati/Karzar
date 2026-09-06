# Task record — IMPL-2026-08-14-product-id-http-301

| Field | Value |
|-------|-------|
| **NODE_ID** | IMPL-2026-08-14-product-id-http-301 |
| **PROMPT** | aods/70-prompts/impl/IMPL-frontend-route.prompt.md (middleware node; that prompt forbids middleware on route nodes — this node *is* the redirect node) |
| **TASK_ID** | SEO-005 (HTTP 301 follow-up) |
| **CHANGE_CLASS** | C2 (existing URL HTTP status 200 → 301; ADR-010 Accepted) |
| **STATUS** | COMPLETE — local; push/merge/deploy pending |
| **Date** | 2026-08-14 |
| **Merge base** | origin/main @ 9fc9ceb |

## Goal

Make `/product/{numeric-id}` an HTTP 301 to `/product/{slug}` before Root Layout streams, so Google sees a real permanent redirect instead of 200 + meta-refresh.

## Authority

- `docs/architecture/adr/ADR-010-seo-url-contract.md:64-65` — legacy id URL MUST 301 when slug exists
- `docs/architecture/rfc/RFC-004-slug-migration-and-redirects.md:40,60`

## Files

1. `frontend/Storefront/src/middleware.ts` — numeric lookup + 301
2. `frontend/Storefront/src/lib/product-url.ts` — path/id/Location helpers
3. Tests: `product-url.test.ts`, `middleware.test.ts`
4. PMO notes + this record

## Non-goals

- Privacy `/faq` meta-refresh (same Next streaming class; not this node)
- KIH/KF contracts, slug values, sitemap filters
- nginx product redirects
