# KarzarTools — Phase 1 Architecture Audit

**Status:** Complete — awaiting approval to start Phase 2 (target architecture design)  
**Date:** 2026-07-22  
**Scope:** Full codebase inspection (backend + Storefront + admin-panel). **No code changes in this phase.**  
**Mission context:** Evolve KarzarTools from industrial e-commerce + thin CMS into a modular **Industrial Knowledge Platform** powered by a Knowledge Graph — without breaking commerce.

**Paused work:** Product image import (resume after Knowledge Platform phases as agreed).

---

## 1. Executive verdict

KarzarTools today is a **solid Modular Monolith commerce platform** with:

- Mature catalog (3-depth categories, brands, JSONB specs, images, soft delete)
- Strong commerce spine (dual cart lanes, inquiry/purchase, payments, stock ledger, idempotency)
- Serious auth/security (JWT versioning, OTP, step-up PIN, throttles, SSRF guards)
- A **thin blog/CMS** with article↔product soft links
- SEO **columns half-shipped** (DB present; API/admin/FE productization incomplete)

It is **not yet** a knowledge platform. There is no entity graph, no content-intelligence pipeline, no SEO engine, no semantic search, no background job framework for knowledge tasks, and no entity landing pages.

**Strategic recommendation:** Keep Modular Monolith. Add a **Knowledge Graph overlay** that *integrates* with existing `products` / `brands` / `categories` / `articles` — do **not** replace those tables or rewrite commerce.

---

## 2. Current architecture (as-is)

### 2.1 Conceptual layers today

```text
Storefront (Next.js)  +  Admin Panel (Next.js)
            ↓  HTTP /api/v1
FastAPI endpoints  (mixed: some → services, some → crud)
            ↓
Services (strong in commerce; weak/absent in CMS & SEO)
            ↓
CRUD + SQLAlchemy 2 async ORM
            ↓
PostgreSQL (+ Redis for limits/locks, not jobs)
            ↓
Manual scripts (crawl/import/seed) + one in-process expiry worker
```

Documented intent: `docs/ARCHITECTURE.md` — `endpoints → services → crud → models`.  
Reality: commerce largely follows it; CMS/users/parts of catalog still leak orchestration into endpoints (`docs/BACKEND_STRUCTURE_REFACTOR_MAP.md` unfinished).

### 2.2 Backend package map

| Area | Path | Role |
|------|------|------|
| Entry | `app/main.py` | FastAPI, middleware, lifespan worker |
| HTTP | `app/api/endpoints/*` | Auth, catalog, cart, orders, payments, CMS, storefront |
| Domain | `app/services/*` | Commerce + category/product orchestration |
| Persistence | `app/crud/*` | SQLAlchemy helpers |
| Models | `app/db/models/*` | product, content, commerce, user, platform |
| Contracts | `app/schemas/*` | Pydantic |
| Cross-cutting | `app/core/*` | config, security, errors, throttle, health |
| Ops | `scripts/*`, `alembic/`, `deploy/` | imports, migrations, staging |

### 2.3 Frontend map

| App | Role |
|-----|------|
| `frontend/Storefront` | Shop + blog; App Router |
| `frontend/admin-panel` | Super-admin catalog/CMS/ops |

**Critical URL reality:**

| Concern | Current |
|---------|---------|
| Product | `/product/{id}` — not slug |
| Category / Brand | **No entity routes** — only `/catalog?category=` / `?brand=` |
| Search | Header → `/catalog?search=` (products only) |
| Blog | `/blog/{slug}` — strongest SEO surface |

---

## 3. Domain inventory (what already exists)

### 3.1 Data model (commerce + CMS)

| Table / concept | Strength | Knowledge-platform gap |
|-----------------|----------|------------------------|
| `products` | SKU, slug, specs JSONB, prices, soft delete | slug/meta not exposed in API; no entity projection |
| `categories` | Adjacency list `parent_id`; depth-3 leaf rule | No category landing content; meta unused in UI |
| `brands` | name, slug, country | No brand hub page/content; `logo_url` schema drift |
| `product_images` | primary + display_order | Coverage ~7% (separate track) |
| `articles` | blocks JSONB, tags, `related_product_ids` | No article meta columns; untyped blocks; no FTS |
| Users / auth | roles, OTP, step-up | No Author entity |
| Orders / payments / cart | Production-grade | Out of knowledge scope (keep as-is) |

### 3.2 SEO implementation

| Capability | Backend | Storefront | Admin |
|------------|---------|------------|-------|
| Product `meta_*` / slug columns | DB yes | Partial metadata by id | **Not editable** |
| Product JSON-LD | No | No | — |
| Article SEO | Hack via `blocks[type=meta]` | `generateMetadata` + Article/FAQ/Breadcrumb JSON-LD | Fragile free-text meta block |
| Category/Brand meta | DB yes | Static catalog metadata only | Name-only forms |
| Sitemap | — | Static + **blog only** | — |
| robots | — | Yes | — |
| Canonical product URL | — | `/product/{id}` | Weak for long-term SEO |

### 3.3 Search

- Products: `ILIKE` on name/SKU/brand + JSONB spec filters + subtree category filter.
- Articles: **no search**.
- No FTS, no trigram, no ranking, no unified index.

### 3.4 Internal linking

| Link | Mechanism | Quality |
|------|-----------|---------|
| Article → products | `related_product_ids` JSONB (no FK) | Manual, soft |
| Product → products | same category subtree | Heuristic, not semantic |
| Product → articles | Storefront shows **all** articles | Unscoped noise |
| Category breadcrumbs | Mostly text | Weak crawlable links |
| Article tags | Display chips | Not hubs |

### 3.5 Background processing

- **No** Celery/ARQ/RQ.
- One asyncio order-expiry worker + Redis lock.
- Knowledge tasks (extract, SEO score, link suggest, reindex) have **nowhere to run**.

### 3.6 Admin

Strong for commerce ops; weak for knowledge/SEO:

- No SEO dashboard
- No entity/graph UI
- No broken-link / coverage / cluster tools
- Categories/brands almost no SEO fields in forms

---

## 4. Strengths (keep and extend)

1. **Modular Monolith** already fits the 10-year target — do not split into microservices.
2. **Commerce spine** is enterprise-grade relative to catalog size; isolate knowledge work from payment/cart paths.
3. **Category depth-3 + JSONB specs + GIN** is a real industrial catalog advantage — feed the graph from these, don’t replace them.
4. **Security posture** (JWT versioning, step-up, OTP hashing, throttles) should wrap new admin knowledge APIs.
5. **Article `blocks` + `related_product_ids`** is the natural seed for Content Intelligence and Internal Link Engine.
6. **Slug columns** on product/category/brand already exist — productize them instead of inventing parallel identity.
7. **Presenter pattern** (`product_presenter`) shows how to expose new read models without leaking ORM.
8. **Contract/tests culture** (`API_CONTRACT`, SEO debt tests) — extend with knowledge contracts the same way.
9. **Import/crawl scripts** prove catalog enrichment pipelines; formalize as background jobs later.

---

## 5. Weaknesses & technical debt

| # | Issue | Impact |
|---|--------|--------|
| 1 | Layer leaks (endpoint→crud) in CMS/users | Harder to add Knowledge services cleanly |
| 2 | SEO half-shipped | Ranking/crawl capacity blocked |
| 3 | No entity routes (category/brand/topic) | Cannot become topical authority |
| 4 | Product URLs by numeric id | Unstable SEO identity |
| 5 | ILIKE-only search | Won’t scale to knowledge corpus |
| 6 | Untyped article blocks + meta-in-blocks | Fragile Content Intelligence input |
| 7 | Soft JSON links without graph | No bidirectional/entity-based linking |
| 8 | No job queue | Cannot run extract/SEO/reindex safely |
| 9 | Heavy client-rendered PDP/catalog | Thin HTML for crawlers |
| 10 | Brand `logo_url` schema vs ORM drift | Small but signals contract drift |
| 11 | God-ish modules (`crud/product`, large endpoints) | Raise change risk |
| 12 | Dual worlds: async API vs sync scripts | Knowledge jobs need a third, proper path |

---

## 6. Missing modules (vs mission brief)

| Proposed module | Exists? | Notes |
|-----------------|---------|-------|
| Knowledge Graph | No | Heart of platform — greenfield overlay |
| Entity Engine | No | Types must be configurable |
| Relation Engine | No | Configurable relation types |
| SEO Engine | No | Only ad-hoc FE metadata |
| Content Intelligence | No | Pipeline not started |
| Internal Link Engine | No | Manual related IDs only |
| Recommendation Engine | Partial | Category-proximity related products |
| Semantic Search | No | ILIKE only |
| Analytics Layer | Partial | GTM + admin reports (commerce) |
| Schema Generator | Partial | Article JSON-LD only in Storefront |

---

## 7. Database assessment

### 7.1 What works

- Normalized commerce tables
- Soft deletes where needed
- JSONB for flexible specs/blocks (good for *content*, bad as *only* graph)
- Alembic history intact

### 7.2 Problems for Knowledge Platform

1. **No first-class entities/relations tables** — everything is page/record oriented.
2. **`related_product_ids` / tags as JSON** — no referential integrity, no inbound queries (“which articles mention this tool?”).
3. **Article SEO not columnar** — hard to score/query.
4. **No aliases/synonyms** — Persian industrial language needs them (کولیس دیجیتال / ورنیه / caliper).
5. **Category adjacency only** — fine for catalog; graph needs many-to-many beyond tree.
6. **No job/outbox tables** — no durable async work.

### 7.3 Integration rule (non-negotiable)

```text
products / brands / categories / articles  =  System of Record (commerce + CMS)
entities / relations / aliases             =  Knowledge Overlay (projected + curated)
```

Bridge tables (e.g. `product_entities`, `article_entities`) link SoR ↔ graph.  
**Do not** duplicate price/stock into the graph.  
**Do not** destroy existing tables.

---

## 8. SEO & IA limitations (today)

1. Authority cannot form: no tool/standard/industry hubs.
2. Catalog filter URLs share one metadata blob.
3. Sitemap omits products (and has no category/brand paths to list).
4. Internal links are commerce-centric, not entity-centric.
5. Search intent (learn vs buy vs compare) is not modeled.
6. Schema coverage is article-only.
7. Admin cannot operate SEO health.

**Information Architecture today:** Shop IA (home → catalog filters → PDP) + Blog silo.  
**Needed IA:** Topic clusters (entities) that sit *between* blog and catalog and interconnect both.

---

## 9. Scalability risks

| Risk | Horizon | Mitigation direction |
|------|---------|----------------------|
| ILIKE full scans as content grows | Medium | FTS/trigram → later vectors |
| Knowledge jobs in-request | Immediate if naively built | Job table + worker |
| Rewriting commerce for graph | Catastrophic | Overlay only |
| Microservices split early | High ops cost | Stay Modular Monolith |
| Client-only PDP HTML | SEO ceiling | RSC/SSR for entity & content pages |
| Unbounded JSON blocks without schema | Content rot | Typed block contracts + extractors |

Catalog size (~3k products) is **not** the bottleneck; **architecture gaps** are.

---

## 10. Refactoring opportunities (before/alongside graph)

Priority order for *enabling* the platform (not implementing all modules):

1. Finish service boundary for CMS (ArticleService) — stop endpoint→crud.
2. Productize SEO fields in API + admin (product/category/brand/article).
3. Product-by-slug + prefer slug URLs (keep id redirects).
4. First-class article meta columns (migrate off meta-block hack).
5. Introduce durable `jobs` / outbox skeleton.
6. Postgres FTS on products + articles as stepping stone to semantic search.
7. Replace JSON `related_product_ids` gradually with `article_entities` / relations (compat period).

---

## 11. Design proposal vs your brief (important)

Your target modules and entity/relation flexibility are **correct** for a 10-year Industrial Knowledge Platform.

**Proposed refinement (better for this codebase):**

| Your brief | Recommended evolution |
|------------|----------------------|
| “Everything becomes an Entity” | Everything *can be projected as* an Entity; commerce SoR remains specialized tables |
| Hard cut to Knowledge Graph thinking | Dual-read: Shop APIs stay; Knowledge APIs grow beside them |
| Semantic search immediately | Phase: FTS + graph boost → embeddings later |
| Full pipeline at once | One pipeline stage module at a time (your Phase 4 rule) |
| New visualizer + SEO dashboard + 10 engines | Sequence after Entity+Relation core exists |
| Background services “queue-ready” | Start with Postgres job rows + in-process/worker; Redis broker optional later |

**Layering we will design in Phase 2 (aligned with your mission, adapted to monolith):**

```text
Presentation (Storefront + Admin Knowledge surfaces)
        ↓
Application / API (existing /api/v1 + new /api/v1/knowledge/*)
        ↓
Business services (commerce kept; knowledge services added)
        ↓
Knowledge Graph services (Entity, Relation, Link, SEO, Schema, Recommend)
        ↓
Content Intelligence pipeline (pluggable steps)
        ↓
Data (existing SoR tables + new graph tables)
        ↓
Background workers (extract, score, reindex, suggest)
```

This preserves your intent while avoiding a rewrite.

---

## 12. Phase roadmap (approval gates)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **1** | This audit — strengths, debt, gaps, risks, design caveat | **DONE — needs your approval** |
| **2** | Target architecture: folder structure, module boundaries, DB diffs, API diffs, migration strategy | Done — see KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md |
| **3** | Implementation roadmap: ordered tasks, complexity, dependencies | Done — see KNOWLEDGE_PLATFORM_PHASE3_IMPLEMENTATION_ROADMAP.md |
| **4+** | Implement **one** slice at a time (I0→I15); first coding = I0 after approval | Pending |
| *After KP track* | Resume product image import phases | Paused |

**Explicit non-goals until approved later:** microservices, destroying commerce tables, AI extractors as v1 requirement, full graph UI in first implementation slice.

---

## 13. Phase 1 decision checklist (for your approval)

Please confirm:

1. Accept **Knowledge Graph as overlay** on existing SoR tables (not replacement).
2. Accept **Modular Monolith** constraint (no microservices).
3. Accept Phase 2 will design folders/DB/API/migration **before any implementation**.
4. Image import remains **paused** until you reopen it.
5. Any constraint to add? (e.g. “must keep `/product/{id}` forever”, “Persian-only entities”, “no vector DB in year 1”)

---

## 14. Sources inspected (non-exhaustive)

- `backend/app/**` (main, api, services, crud, models, core, utils)
- `backend/docs/ARCHITECTURE.md`, `BACKEND_STRUCTURE_REFACTOR_MAP.md`, go-live/SEO notes
- `frontend/Storefront/src/app/**` (catalog, product, blog, sitemap, robots)
- `frontend/admin-panel/src/**` (catalog, CMS, nav)
- Live catalog metrics context from prior sessions (~2959 products; image/price gaps separate)

---

*End of Phase 1. No code was modified for Knowledge Platform implementation. This document is the approval artifact for Phase 2.*
