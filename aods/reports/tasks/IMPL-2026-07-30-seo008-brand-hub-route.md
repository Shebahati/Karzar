# Task record — IMPL-2026-07-30-seo008-brand-hub-route

| Field | Value |
|-------|-------|
| **NODE_ID** | IMPL-2026-07-30-seo008-brand-hub-route |
| **PROMPT** | aods/70-prompts/impl/IMPL-frontend-route.prompt.md |
| **TASK_ID** | SEO-008 |
| **CHANGE_CLASS** | C3 |
| **ARCHETYPE** | IMPL |
| **STATUS** | COMPLETE — route landed; sitemap residual |
| **Date** | 2026-07-30 |

## Goal

Ship `/brands/[slug]` per Accepted brand-hub-page-contract (D21).

## Files changed

1. `frontend/Storefront/src/app/brands/[slug]/page.tsx` (new)
2. `frontend/Storefront/src/components/brand/brand-hub-view.tsx` (new)
3. `frontend/Storefront/src/components/catalog/catalog-view.tsx` — `lockedBrandId`
4. `frontend/Storefront/src/lib/json-ld.ts` — `buildBrandHubJsonLd` / `brandPageUrl`
5. `frontend/Storefront/src/components/product/product-detail-view.tsx` — hub link
6. `frontend/Storefront/src/lib/__tests__/json-ld.test.ts`
7. PMO: tasks.json, CHANGELOG, SEO_PROGRESS, SPRINT_05
8. This record

## Non-goals (honoured)

- No `/brands` index (Q4=B)
- No sitemap wave (separate node)
- No dependency adds

## Verify

```text
AODS validation — PASS (openapi SKIP)
vitest json-ld.test.ts — 11 passed (incl. buildBrandHubJsonLd)
tsc --noEmit — exit 0
```
