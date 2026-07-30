---
id: SPEC-brand-hub-page-contract
version: 0.1.0
status: Accepted
date: 2026-07-30
governing_adr: docs/architecture/adr/ADR-010-seo-url-contract.md
governing_rfc: docs/architecture/rfc/RFC-005-brand-hub-launch.md
owner: Frontend Architect + SEO Engineer
task_id: SEO-008
aods_conflict: CR-014
accepted_by: Mohammad Shebahati / محمد شباهتی (Board — operator instructed agent to record Accepted 2026-07-30)
---

# Brand Hub page contract — `/brands/{slug}`

**Status:** **Accepted** (2026-07-30) — Q1–Q5 frozen **D21**; Board Accepted under `HC-01` (recorded per Owner order). Binding merge criteria for SEO-008 / Brand Hub IMPL (also listed in Canon Lock).  
**PMO:** `SEO-008` · Sprint 05 · closes `CR-014` / `G-01`.

## 1. Purpose

Give implementers a falsifiable page + API contract for first-class Brand Hub pages at
`/brands/{slug}`, so EPIC-1 deliverable 5 can ship without inventing IA, SEO, or thin-content
rules in code. Buyers and crawlers get an entity hub for a real brand; unbranded catalog stays
honest (no fake “Generic” brand).

## 2. Governing authority

| Source | Binding decision | Cite |
|--------|------------------|------|
| ADR-010 Decision 4 | Brand hubs MUST use `/brands/{slug}` | `docs/architecture/adr/ADR-010-seo-url-contract.md:67` |
| ADR-010 Decision 6 | JSON-LD `@id` / breadcrumbs align to canonical URLs | `…/ADR-010-seo-url-contract.md:69` |
| ADR-010 Decision 7–8 | No Facts/KG required; facet URLs are not entity hubs | `…/ADR-010-seo-url-contract.md:70-71` |
| RFC-005 §1 / §5 | Launch `/brands/{slug}` with meta via API; commerce-first grid; waves | `docs/architecture/rfc/RFC-005-brand-hub-launch.md:30-40`, `:61-95` |
| RFC-005 Non-goals | No fake brands; no Facts-blocker; no production scrape to fill blurbs | `…/RFC-005-brand-hub-launch.md:46-49`, `:132-136` |
| epic1-ia-readiness #5–6 | Ship Brand Hub; expose brand meta | `docs/architecture/information-architecture/epic1-ia-readiness.md:27-28` |
| url-map | Brand Hub TARGET `/brands/{slug}`; `?brand=` is not a hub | `docs/architecture/information-architecture/url-map.md:15`, `:35` |
| API envelope | Error shape + list `{data, meta}` for product lists | `docs/API_CONTRACT.md:51-56`, `:63-70` |
| As-built brand API | `GET /api/v1/brands/slug/{slug}` → `BrandResponse` | `app/api/endpoints/brand.py:46-61`, `app/schemas/brand.py:7-15` |
| As-built PLP filter | Products list accepts `brand_id` + `{data, meta}` pagination | `app/api/endpoints/products_catalog.py:67-71`, `:197-201` |

## 3. Non-goals

- Facts / Evidence / Knowledge Graph modules on the hub (RFC-005 Non-goals).
- Inventing brands or hubs for unbranded SKUs (ADR-002 / RFC-005 Option C rejected).
- Replacing Category Hub or treating `?brand=` / catalog facets as Brand Hubs (ADR-010 §8, url-map).
- Deciding thin-content **product-count** thresholds or indexability policy without Board — answered **D21** (see §9); do not re-open in IMPL.
- Implementing `/brands` collection index in this contract (RFC-005 §12 Q1 — open).
- Changing BE-01 transaction ownership or admin Brand CRUD semantics.
- Setting this document to `Accepted` — **done 2026-07-30** (Board / Owner order).

## 4. Data contract

### 4.1 Brand hub header (from existing public brand retrieve)

Reuse `BrandResponse` as returned by `GET /api/v1/brands/slug/{slug}` (no parallel DTO).

| Field | Type | Null | Source | Required for hub render |
|-------|------|------|--------|-------------------------|
| `id` | int | no | `brands.id` | yes (product filter key) |
| `name` | str | no | `brands.name` | yes (hero primary signal — RFC-005 §5 Content) |
| `slug` | str | no | `brands.slug` | yes (URL segment) |
| `country` | str \| null | yes | `brands.country` | optional display |
| `logo_url` | str \| null | yes | `brands.logo_url` | optional; logo asset policy open (RFC-005 §12) |
| `meta_title` | str \| null | yes | `brands.meta_title` | SEO; template fallback if empty (RFC-005 §5 SEO) |
| `meta_description` | str \| null | yes | `brands.meta_description` | SEO + short supporting blurb if no authored intro |
| `product_count` | int \| null | yes | counted active products | display / thin-policy input (**threshold open**) |

**As-built gap:** ORM `Brand` has **no** long `description` column (`app/db/models/product.py:115-124`). Hub “blurb” MUST NOT invent copy. **Q3 = B (frozen D21):** supporting sentence MAY use `meta_description` when present, else omit (name-only hero is allowed).

Example (illustrative):

```json
{
  "id": 3,
  "name": "INSIZE",
  "slug": "insize",
  "country": null,
  "logo_url": "/uploads/brands/insize.png",
  "meta_title": "INSIZE | ابزار اندازه‌گیری",
  "meta_description": "کولیس و میکرومتر صنعتی INSIZE",
  "product_count": 420
}
```

### 4.2 Product grid

Reuse existing catalog list contract: `GET /api/v1/products/` with `brand_id=<id>`, `is_active` defaulting to storefront rules, pagination via `{ data, meta }` (`PaginationMeta`: `total_count`, `skip`, `limit`, `has_next`, `has_prev` — `app/schemas/common.py:10-15`).

Product card fields: existing storefront `ProductSummary` / card contract (no new parallel product shape in EPIC-1).

### 4.3 SEO document fields (HTML)

| Field | Rule |
|-------|------|
| `<title>` / OG title | `meta_title` if non-empty; else template including brand `name` (RFC-005 §5 SEO) |
| meta description | `meta_description` if non-empty; else template; never fabricated specs |
| canonical | `https://{site}/brands/{slug}` self-canonical |
| robots | **Q2=A (D21):** below-threshold / empty → `noindex`; MUST NOT treat facet URLs as this hub |

### 4.4 JSON-LD (minimum)

| Type | Rule |
|------|------|
| `@id` | Absolute canonical hub URL `/brands/{slug}` (ADR-010 Decision 6) |
| Brand / Organization node | Brand `name` + `@id`; no false AggregateRating |
| ItemList / CollectionPage | Optional EPIC-1; if present, item URLs MUST be `/product/{slug}` when slug exists (ADR-010 / RFC-004 alignment) |
| BreadcrumbList | Home → {Brand} for wave 1 (**Q4=B** — no `/brands` index yet); revisit when index ships |

## 5. Behaviour

### 5.1 Success

1. Storefront receives `slug`, calls `GET /api/v1/brands/slug/{slug}`.
2. On 200, renders hub: brand name hero, optional logo, optional short blurb per §4.1, product grid filtered by `brand.id`.
3. Pagination controls use `meta.has_next` / `has_prev` (or equivalent page params mapped to skip/limit).
4. PDP with `brand_id` links to `/brands/{slug}` (RFC-005 §5 URL & IA).
5. Launched-wave brands appear in sitemap as `/brands/{slug}` (RFC-005 §5 SEO / rollout).

### 5.2 Errors and edges

| Case | HTTP / UX | Notes |
|------|-----------|-------|
| Unknown slug | API 404 `NOT_FOUND`; page **notFound** | `brand.py:54-58` |
| Brand exists, zero active products | **Q1=A / Q2=A (D21):** still publish hub (≥1 threshold means empty is below); **200 + `noindex`** | CR-014 / D21 |
| Unbranded product | No hub membership; PDP ok | RFC-005 Wave table |
| Invalid `brand_id` query on products | 422 `VALIDATION_FAILED` | products_catalog |
| Admin-only mutations | Unchanged (step-up delete etc.) | out of hub page scope |
| Thin meta (empty meta_*) | Route still allowed; templates + backlog | RFC-005 §8 “don’t block route” for thin *meta* |
| Facet `?brand=` catalog URL | Not a Brand Hub; must not be indexed as entity hub | ADR-010 Decision 8 |

## 6. URL / route contract

| Item | Contract |
|------|----------|
| Canonical path | `/brands/{slug}` (plural `brands`) |
| Superseded path | None for hubs (new surface). Do not introduce `/brand/{slug}` |
| Filter anti-pattern | ` /catalog?brand=` (or equivalent) remains PLP aid, not hub |
| Redirect | N/A for first ship; rollback MAY 404 or flag-hide `/brands/*` (RFC-005 §9) |

## 7. Acceptance criteria

1. Given an existing brand slug `insize` with API 200, when a client GETs `/brands/insize`, then the response is HTTP 200 and the document canonical equals `/brands/insize`.
2. Given brand slug `insize`, when the hub product grid loads, then every listed product request is filtered by that brand’s `id` via the existing products list API (not a one-off unfiltered dump).
3. Given brand slug `no-such-brand`, when a client GETs `/brands/no-such-brand`, then the storefront yields a not-found outcome consistent with API 404.
4. Given a product with `brand.slug` set, when the PDP renders brand navigation, then it links to `/brands/{slug}` (not a facet-only URL presented as the hub).
5. Given a launched-wave brand, when sitemap is generated for that wave, then it emits an absolute `/brands/{slug}` entry for that brand.
6. Given hub JSON-LD is emitted, when `@id` is read, then it equals the canonical `/brands/{slug}` URL (absolute).
7. Given `meta_title` and `meta_description` are null, when the hub renders, then the page still returns 200 with template fallbacks and does **not** invent product datasheet claims.
8. Given this spec is **Accepted** (2026-07-30), IMPL PRs MAY cite it as merge criteria together with ADR-010 / RFC-005 / Canon Lock.

## 8. Out-of-scope discoveries

- Account order links still using `/product/{id}` (SEO-006 residual) — not Brand Hub scope.
- BE-01 service-level commits (`CR-005`) — unrelated.
- `/brands` index page, logo asset requirements, multi-brand OEM names — RFC-005 §12.
- Category empty-hub hygiene is a pattern reference only; copying its threshold without Board decision would invent policy (`CR-014`).

## 9. Open questions — **FROZEN** (2026-07-30 / D21)

| # | Question | Board answer | Consequence |
|---|----------|--------------|-------------|
| Q1 | Minimum active product count to **publish** a hub? | **A) ≥1** | Empty-grid brands: see Q2 |
| Q2 | If below threshold (or empty grid): what? | **A) 200 + `noindex`** | Thin hubs stay reachable; not indexed |
| Q3 | Hub intro copy source? | **B) `meta_description` only** | No authored intros file in EPIC-1 |
| Q4 | Is `/brands` index in wave 1? | **B) Later** | Breadcrumb omits intermediate `/brands` for now |
| Q5 | Brand logo required for wave 1? | **B) Optional** | Render logo when `logo_url` present |

**Still required for IMPL merge criteria:** ~~Board sets front-matter `status: Accepted`~~ — **done 2026-07-30**. Cite this Accepted contract + ADR-010 / RFC-005.

## 10. Implementation node breakdown

| Node | Archetype | Notes |
|------|-----------|--------|
| `HC-01` Accept this spec | Human | **DONE 2026-07-30** — Q1–Q5 + Accepted + Canon Lock row |
| `IMPL-backend` brand hub readiness | IMPL | Confirm public slug + meta + counts; product filter already exists — gap only if contract tests missing |
| `IMPL-frontend-route` `/brands/[slug]` | IMPL | Page regions per §4–5; wire SEO-008; apply Q1–Q5 |
| `IMPL-sitemap-nav` | IMPL | Wave sitemap + PDP/category internal links (no `/brands` index until Q4 revisit) |
| `TEST-from-spec` | TEST | Automate AC 1–7 where feasible |
| `DOC-api-contract-sync` | DOC | If any new public field ships, update API_CHANGELOG / OpenAPI |
| `GOV-pmo-sync` | GOV | Mark SEO-008 progress; close CR-014 when Accepted + shipped or when SPEC Accepted clears G-01 |

## 11. Decision log

| Date | Decision | By | Note |
|------|----------|----|------|
| 2026-07-30 | Draft Proposed page contract; thresholds left open | AODS SPEC node | Resume path A after HALT; `CR-014` SPEC-ready |
| 2026-07-30 | Freeze Q1=A, Q2=A, Q3=B, Q4=B, Q5=B | Mohammad Shebahati / Board | **D21** |
| 2026-07-30 | `status: Accepted` + Canon Lock row | Mohammad Shebahati / Board (Owner ordered agent to record) | Closes `CR-014` G-01; unlocks SEO-008 IMPL |
