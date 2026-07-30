# IMPL — FE-002 PDP PDF CTA + accessories slot

| Field | Value |
|-------|-------|
| **DATE** | 2026-07-30 |
| **ARCHETYPE** | IMPL |
| **TASK_ID** | FE-002 |
| **PROMPT** | `aods/70-prompts/impl/IMPL-frontend-route.prompt.md` |
| **STATUS** | COMPLETE — FE-002 done |

## Goal

Render EPIC-1.7 Relation-layer Document (PDF) CTA and accessories slot on PDP with honest empty states.

## Authority (origin/main)

- `docs/architecture/karzar-knowledge-platform-master-architecture.md:619` — Surface honest empty for accessories
- `docs/architecture/information-architecture/epic1-ia-readiness.md:29` — PDF CTA + accessories (honest empty OK)
- `docs/FRONTEND_INTEGRATION.md` / `docs/examples/sample_product.json` — `optional_accessories` string[]
- `project-management/exports/tasks.json` FE-002 AC

## Delivered

- `product-pdf-cta.tsx` — CTA or Persian empty when `pdf_catalog_url` missing
- `product-accessories-slot.tsx` — always visible; empty / labels / `useProductsByIds` + `ProductCarousel`
- Wired in `product-detail-view.tsx` (PDF after trust strip; accessories before comments)
- `ProductSpecifications.optional_accessories?: string[]`

## Non-goals

- Catalog PDF fill / accessory edge ingestion
- Typed KG Relation Engine
- CAT-002 / KB-001
