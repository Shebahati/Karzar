# Task record — IMPL-2026-07-30-seo008-brand-hub-sitemap-nav

| Field | Value |
|-------|-------|
| **NODE_ID** | IMPL-2026-07-30-seo008-brand-hub-sitemap-nav |
| **PROMPT** | aods/70-prompts/impl/IMPL-frontend-route.prompt.md |
| **TASK_ID** | SEO-008 |
| **CHANGE_CLASS** | C3 |
| **STATUS** | COMPLETE — SEO-008 done |
| **Date** | 2026-07-30 |

## Goal

Sitemap `/brands/{slug}` for brands with ≥1 products + slug; brand-strip → hub URL.

## Files

1. `frontend/Storefront/src/app/sitemap.ts` — `collectBrandEntries`
2. `frontend/Storefront/src/components/home/brand-strip.tsx` — hub href
3. PMO: tasks.json, CHANGELOG, SEO_PROGRESS, SPRINT_05, PROJECT_STATUS, DONE
4. This record

## Non-goals

- No `/brands` index (Q4=B)

## Verify

```text
AODS validation — PASS (openapi SKIP)
EXIT:0
```
