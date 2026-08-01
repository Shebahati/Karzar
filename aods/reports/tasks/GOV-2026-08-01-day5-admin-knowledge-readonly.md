# Day 5 — Admin read-only Knowledge views

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Session** | Readiness §5 step 6 |
| **Attendees** | Mohammad Shebahati · Cursor |
| **Owner order** | «مرج کردم. گام بعدی.» (after classify-map hygiene #182) |
| **Parents** | FOUNDATION_IMPLEMENTATION_READINESS §5.6 · KB-001 Day-3 APIs · Day-2 three-edge freeze |

## Scope

**In:** Admin panel read-only consumption of existing Knowledge APIs:
- `/knowledge` — edges browser (`GET /knowledge/edges`)
- Product edit — neighborhood card (`GET /knowledge/products/{id}/neighborhood`)
- Mock API seed for `USE_MOCK`

**Out:** Facts assert/publish · dual-write · `PRODUCT_CLASSIFIED_AS` · Taxonomy/Dictionary editors · new dependencies · Admin UX page SPECs for full KM (still missing; this is OpenAPI-bound MVP only)

## Deliverables

- `frontend/admin-panel/src/types/knowledge.ts`
- `frontend/admin-panel/src/services/knowledge.ts`
- `frontend/admin-panel/src/features/knowledge/**`
- `frontend/admin-panel/src/app/(dashboard)/knowledge/page.tsx`
- Nav item «دانش محصول»
- Vitest: `edge-labels.test.ts`

## Evidence

- Sequence step 6: `docs/architecture/specs/FOUNDATION_IMPLEMENTATION_READINESS.md:157`
- APIs: `app/api/endpoints/knowledge.py` / OpenAPI `/api/v1/knowledge/*`
- As-built gap: audit «no Knowledge Graph UI»
