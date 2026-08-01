# KarzarTools — Phase 2 Target Architecture Design


> **Supersession (OI-KF-04 · Board Day-2 · 2026-08-01 / ۱۴۰۵/۰۵/۱۰):** This Phase document is **HISTORICAL / orientation** only. The living knowledge-architecture path is `docs/architecture/specs/` (core pack **Accepted** — see `aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md` and Canon Lock §1c). Do **not** use this file as merge criteria or as SoT against Accepted SPECs/ADRs.

**Status:** Complete — Phase 3 roadmap published  
**Date:** 2026-07-22  
**Depends on:** [KNOWLEDGE_PLATFORM_PHASE1_ARCHITECTURE_AUDIT.md](./KNOWLEDGE_PLATFORM_PHASE1_ARCHITECTURE_AUDIT.md)  
**Next:** [KNOWLEDGE_PLATFORM_PHASE3_IMPLEMENTATION_ROADMAP.md](./KNOWLEDGE_PLATFORM_PHASE3_IMPLEMENTATION_ROADMAP.md)  
**Constraint:** Design only. No production code / migrations in this phase.

---

## 0. Decisions locked from Phase 1

| Decision | Choice |
|----------|--------|
| Architecture style | **Modular Monolith** (no microservices) |
| Knowledge Graph | **Overlay** on SoR tables — not a replacement |
| Systems of Record | `products`, `brands`, `categories`, `articles`, commerce tables |
| API strategy | **Additive** `/api/v1/knowledge/*` (+ gradual enrichment of existing routes) |
| Search evolution | FTS + graph boost first → embeddings later |
| Jobs | Postgres job rows + worker first → optional broker later |
| Image import | Remains paused until Knowledge Platform track allows reopen |
| Layer rule | `endpoints → services → crud → models` (align with existing refactor map) |

---

## 1. Target conceptual architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Presentation                                               │
│  Storefront (shop + entity hubs + blog)                     │
│  Admin (commerce + Knowledge/SEO dashboard + graph)         │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP /api/v1
┌───────────────────────────▼─────────────────────────────────┐
│  Application / API                                          │
│  Existing commerce & CMS routers (stable contracts)         │
│  New knowledge routers (versioned, additive)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Business Layer                                             │
│  Existing: product/category/brand/cart/order/payment/…      │
│  New: knowledge façade services (orchestrate engines)       │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌────────────────────┐
│ Knowledge     │  │ Content        │  │ SEO / Schema /     │
│ Graph Core    │  │ Intelligence   │  │ Link / Recommend / │
│ Entity+Rel    │  │ Pipeline       │  │ Search engines     │
└───────┬───────┘  └────────┬───────┘  └─────────┬──────────┘
        │                   │                    │
        └───────────────────┼────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Data Layer                                                 │
│  SoR (unchanged ownership) + Knowledge tables + jobs        │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Background Services                                        │
│  Worker loop: extract → score → link suggest → reindex      │
└─────────────────────────────────────────────────────────────┘
```

**Principle:** Presentation never talks to engines directly. Engines never import FastAPI. Engines never write commerce price/stock.

---

## 2. Module catalog & boundaries

### 2.1 Modules (logical packages)

| # | Module | Responsibility | Must NOT do |
|---|--------|----------------|-------------|
| M0 | **Catalog/Commerce** (existing) | Products, cart, orders, payments | Own knowledge graph schema |
| M1 | **Entity Engine** | CRUD entities, types, aliases, synonyms, metadata, images | Rank SEO, crawl pages |
| M2 | **Relation Engine** | Relation types + edges; traversal helpers | Extract text from articles |
| M3 | **Knowledge Graph Facade** | Compose entity+relation read models; projection from SoR | Duplicate product fields |
| M4 | **Content Intelligence** | Pluggable pipeline on article/product save | Direct HTTP responses |
| M5 | **Internal Link Engine** | Entity-based link suggestions | Keyword-only stuffing |
| M6 | **SEO Engine** | Score pages; structured SEO report | Persist HTML |
| M7 | **Schema Generator** | Build JSON-LD graphs (extensible builders) | Render Next pages |
| M8 | **Recommendation Engine** | Related entities/products/articles via graph (+ fallbacks) | Replace cart logic |
| M9 | **Semantic Search** | Unified search across entity-backed documents | Own auth |
| M10 | **Analytics / SEO Ops** | Aggregates for admin dashboard | Real-time payments |
| M11 | **Jobs** | Enqueue, claim, retry, dead-letter | Business rules of extractors |

### 2.2 Dependency rules (acyclic)

```text
API endpoints
  → knowledge façade / existing business services
    → engines (M1–M10)     [engines may call Entity/Relation only downward]
      → knowledge crud
        → models

Content Intelligence steps may call: Entity, Relation, Link, SEO, Schema (via interfaces)
SEO may call: Schema (read builders), Entity (coverage stats)
Search may call: Entity, Relation (boost), and read FTS indexes
Recommend may call: Relation, Entity

FORBIDDEN:
  Entity → SEO
  Relation → Content Intelligence
  Schema → FastAPI
  Knowledge crud → commerce services
  Commerce services → Content Intelligence (use jobs/events instead)
```

### 2.3 Extension points (interfaces)

All defined as Protocol / ABC in `app/knowledge/ports/`:

| Port | Implementations (v1 → later) |
|------|------------------------------|
| `EntityExtractor` | `RuleBasedExtractor` → `LlmExtractor` |
| `SeoAnalyzer` | `HeuristicSeoAnalyzer` → weighted ML |
| `SchemaBuilder` | Article, Product, Breadcrumb, FAQ, Org, WebSite, Brand… |
| `LinkSuggester` | `GraphLinkSuggester` |
| `SearchIndexer` | `PostgresFtsIndexer` → `HybridVectorIndexer` |
| `JobQueue` | `PostgresJobQueue` → Redis/RQ later |

---

## 3. Target folder structure

Extend the existing tree; do **not** invent a second app. Align with `BACKEND_STRUCTURE_REFACTOR_MAP.md` direction.

```text
backend/app/
├── api/
│   ├── deps.py
│   ├── v1/__init__.py                 # mounts existing + knowledge
│   └── endpoints/
│       ├── … (existing commerce/CMS kept)
│       └── knowledge/                 # NEW package
│           ├── __init__.py            # aggregator router
│           ├── entities.py
│           ├── relations.py
│           ├── search.py
│           ├── seo.py
│           ├── links.py
│           ├── schema.py
│           ├── pipeline.py            # admin: run/status
│           ├── graph.py               # neighborhood read API
│           └── admin_dashboard.py     # SEO/knowledge health aggregates
│
├── services/                          # existing commerce services stay
│   └── … 
│
├── knowledge/                         # NEW domain package (engines)
│   ├── __init__.py
│   ├── ports/                         # Protocols only
│   │   ├── extractors.py
│   │   ├── seo.py
│   │   ├── schema.py
│   │   ├── links.py
│   │   ├── search.py
│   │   └── jobs.py
│   ├── entity/
│   │   ├── service.py                 # Entity Engine
│   │   └── projection.py              # SoR → entity upsert helpers
│   ├── relation/
│   │   └── service.py
│   ├── graph/
│   │   └── service.py                 # façade read models
│   ├── intelligence/
│   │   ├── pipeline.py                # orchestrator
│   │   ├── steps/                     # one file per step
│   │   │   ├── extract_entities.py
│   │   │   ├── find_missing.py
│   │   │   ├── semantic_analysis.py
│   │   │   ├── suggest_links.py
│   │   │   ├── related_content.py
│   │   │   ├── faq_suggest.py
│   │   │   ├── metadata_suggest.py
│   │   │   ├── schema_build.py
│   │   │   ├── seo_analyze.py
│   │   │   └── finalize_score.py
│   │   └── extractors/
│   │       └── rule_based.py
│   ├── seo/
│   │   ├── analyzer.py
│   │   └── report.py
│   ├── schema_gen/
│   │   ├── registry.py
│   │   └── builders/
│   ├── links/
│   │   └── suggester.py
│   ├── recommend/
│   │   └── service.py
│   ├── search/
│   │   ├── service.py
│   │   └── indexer_fts.py
│   └── analytics/
│       └── seo_dashboard.py
│
├── crud/
│   ├── … (existing)
│   └── knowledge/                     # NEW
│       ├── entities.py
│       ├── relations.py
│       ├── bridges.py                 # article_entities, product_entities, …
│       ├── aliases.py
│       └── jobs.py
│
├── db/models/
│   ├── … (existing SoR)
│   └── knowledge.py                   # NEW models module
│
├── schemas/
│   ├── … (existing)
│   └── knowledge/                     # NEW Pydantic contracts
│       ├── entities.py
│       ├── relations.py
│       ├── search.py
│       ├── seo.py
│       ├── graph.py
│       └── pipeline.py
│
├── workers/                           # NEW
│   ├── __init__.py
│   ├── runner.py                      # claim jobs loop (lifespan or CLI)
│   └── handlers/
│       ├── intelligence.py
│       ├── reindex.py
│       └── seo.py
│
└── …
```

### Frontend (additive routes — Phase 3+ implementation order)

```text
Storefront/src/app/
  entity/[type]/[slug]/page.tsx     # Tool, Standard, Industry, … hubs
  brand/[slug]/page.tsx             # brand hub (content + products)
  category/[slug]/page.tsx          # category landing (content + PLP)
  product/[slug]/page.tsx           # prefer slug; redirect from /product/[id]
  search/page.tsx                   # unified knowledge search UI
  blog/…                            # keep; enrich with entity links

admin-panel/src/app/(dashboard)/
  knowledge/
    entities/
    relations/
    graph/
    seo-dashboard/
    links/
    jobs/
```

Commerce admin paths stay untouched.

---

## 4. Database design (normalized overlay)

### 4.1 Principles

1. SoR tables **unchanged in ownership**; additive columns only when necessary (e.g. article SEO columns).
2. Graph identity is `entities.id` (UUID or bigserial — recommend **UUID** for merge/import safety).
3. Types/relations are **data-driven** (`entity_types`, `relation_types`), not Python enums required for new kinds.
4. Bridges are explicit M2M with unique constraints.
5. All knowledge tables: `created_at`, `updated_at`; soft-archive via `archived_at` where needed.

### 4.2 Core tables

#### `entity_types`
| Column | Type | Notes |
|--------|------|-------|
| id | PK | |
| key | citext unique | e.g. `tool`, `brand`, `standard` — extensible |
| title_fa | text | |
| title_en | text null | |
| is_system | bool | seeded types protected |
| schema_hint | jsonb | optional UI/validation hints |

Seed keys (not hardcoded forever):  
`tool`, `brand`, `component`, `industry`, `standard`, `property`, `measurement`, `technology`, `material`, `accessory`, `application`, `problem`, `maintenance`, `article`, `product`, `category`, `video`, `author`

#### `entities`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| entity_type_id | FK | |
| slug | citext | unique per type |
| name | text | primary display |
| name_fa / name_en | text null | |
| status | enum/text | `draft\|published\|archived` |
| summary | text null | |
| body | jsonb null | optional long-form hub content blocks |
| sor_table | text null | `products` / `brands` / `categories` / `articles` |
| sor_id | int null | polymorphic soft pointer to SoR |
| canonical_url_path | text null | e.g. `/entity/tool/digital-caliper` |
| meta_title / meta_description | text null | |
| published_at | timestamptz null | |
| archived_at | timestamptz null | |
| metadata | jsonb | flexible facts |
| search_document | tsvector | maintained by trigger/indexer |
| Unique | (entity_type_id, slug) | |
| Unique | (sor_table, sor_id) WHERE sor_id IS NOT NULL | one projection per SoR row |

#### `entity_aliases` / `entity_synonyms`
| Column | Notes |
|--------|-------|
| entity_id | FK |
| alias / synonym | text |
| locale | `fa` / `en` / `…` |
| source | `manual` / `import` / `extractor` |
| Unique (entity_id, lower(alias), locale) | |

*(If preferred, single `entity_aliases` with `kind` = alias|synonym.)*

#### `relation_types`
| Column | Notes |
|--------|-------|
| key | unique: `is_a`, `part_of`, `manufactured_by`, … |
| title_fa | |
| is_symmetric | bool |
| inverse_key | null or key of inverse type |
| is_system | bool |

Seed examples:  
`is_a`, `part_of`, `has_component`, `manufactured_by`, `compared_with`, `uses`, `belongs_to`, `related_to`, `requires`, `compatible_with`, `used_in`, `alternative_to`, `has_standard`, `measures`, `solves`, `mentions`, `recommends`

#### `relations`
| Column | Notes |
|--------|-------|
| id | PK |
| relation_type_id | FK |
| from_entity_id | FK |
| to_entity_id | FK |
| weight | numeric default 1 |
| confidence | numeric 0–1 |
| source | `manual` / `pipeline` / `projection` |
| metadata | jsonb |
| Unique (relation_type_id, from_entity_id, to_entity_id) | |
| CHECK from_entity_id <> to_entity_id | |

#### Bridge tables
- `article_entities` (article_id, entity_id, role: `mentions|primary|tag`, positions jsonb)
- `product_entities` (product_id, entity_id, role)
- `category_entities` (category_id, entity_id, role)

Keep `articles.related_product_ids` during migration; dual-write then deprecate.

#### `entity_images`
entity_id, image_url, is_primary, display_order — parallel to product_images pattern.

#### `entity_metadata`
Optional EAV/json companion if `entities.metadata` should stay small; **v1 can use only `entities.metadata` jsonb** and add EAV later if query patterns demand it.

#### Pipeline / SEO persistence
| Table | Purpose |
|-------|---------|
| `content_analyses` | per target (`article`/`product`/`entity`), latest scores, report jsonb |
| `link_suggestions` | from_url/entity → to_entity, status pending/accepted/rejected |
| `schema_snapshots` | optional cached JSON-LD by page key |
| `search_documents` | optional explicit index rows if not only tsvector on entities |

#### Jobs
| Table `jobs` | |
|--------------|--|
| id, queue, job_type, payload jsonb | |
| status | `pending\|running\|succeeded\|failed\|dead` |
| attempts, max_attempts | |
| run_after, locked_at, locked_by | |
| last_error, created_at, updated_at | |
| Indexes | (status, run_after), (queue, status) |

### 4.3 Additive SoR changes (minimal)

| Change | Why |
|--------|-----|
| `articles.meta_title`, `articles.meta_description`, `articles.canonical_path` | Replace meta-block hack |
| Expose existing product/category/brand meta in API | Already in DB |
| Optional `products.search_document` tsvector | FTS |
| Optional `articles.search_document` tsvector | FTS |

**No** dropping of commerce columns. **No** moving stock/price into entities.

### 4.4 ER sketch

```text
entity_types 1──* entities 1──* entity_aliases
                 │
                 ├──* entity_images
                 │
relations *──────┴──────* entities
   │
relation_types

articles *──* entities   via article_entities
products *──* entities   via product_entities
categories *──* entities via category_entities

jobs  (independent)
content_analyses (polymorphic target)
link_suggestions → entities
```

---

## 5. API design (additive)

Base: `/api/v1/knowledge`

### 5.1 Public (Storefront)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/entities/{type_key}/{slug}` | Entity hub payload |
| GET | `/entities/{id}/neighborhood` | In/out relations + related products/articles |
| GET | `/search?q=&types=` | Unified search (products, articles, entities, …) |
| GET | `/schema?page_type=&id_or_slug=` | JSON-LD document for page |
| GET | `/recommendations?entity_id=` or `product_id=` | Graph-aware related |

### 5.2 Admin (super_admin + step-up where destructive)

| Method | Path | Purpose |
|--------|------|---------|
| CRUD | `/admin/entity-types`, `/admin/entities`, `/admin/relation-types`, `/admin/relations` | Graph curation |
| POST | `/admin/entities/{id}/aliases` | |
| POST | `/admin/projections/sync` | Re-project SoR → entities (brand/product/category/article) |
| GET/POST | `/admin/pipeline/run` | Enqueue intelligence for target |
| GET | `/admin/pipeline/{job_id}` | Status |
| GET | `/admin/seo/report` | Page SEO report |
| GET | `/admin/seo/dashboard` | Aggregates: coverage, missing topics, broken links, health |
| GET/PATCH | `/admin/link-suggestions` | Accept/reject |
| GET | `/admin/jobs` | Job list / retry |

### 5.3 Existing API enrichment (backward compatible)

| Existing | Additive fields / routes | Compat |
|----------|--------------------------|--------|
| Product detail | `slug`, `meta_*`, `entity_ids[]` optional | Old clients ignore |
| `GET /products/by-slug/{slug}` | New | Keep `/products/{id}` |
| Category/Brand | return `meta_*`; Storefront gains hub routes | Query-param catalog remains |
| Articles | columnar meta; `entities[]` | `related_product_ids` still returned until deprecated |
| Related products | prefer Recommendation Engine when graph dense; fallback category heuristic | Same response shape |

**Contract rule:** no breaking changes without versioned changelog + FE coordination.

---

## 6. Content Intelligence pipeline

Triggered on: article publish/update, manual admin run, nightly reindex.

```text
ArticleSaved / ProductUpdated / ManualRun
        ↓  enqueue job
[1] Extract Entities          (EntityExtractor port)
[2] Find Missing Entities     (suggest new drafts)
[3] Semantic Analysis         (topics, intent: learn|buy|compare)
[4] Internal Link Suggestions (Link Engine)
[5] Related Articles          (graph + tags)
[6] Related Products          (bridges + graph)
[7] FAQ Suggestions           (from headings/blocks)
[8] Metadata Suggestions      (title/description)
[9] Schema Generation         (Schema Generator)
[10] SEO Analysis             (SEO Engine)
[11] Final Score              (persist content_analyses)
```

Each step: `async def run(ctx: PipelineContext) -> PipelineContext`  
Failed step → job retry; non-fatal steps can soft-fail and continue with flags.

v1 extractors: **rule-based** (alias dictionary + SKU/brand lexicons).  
AI extractors plug in later without pipeline rewrite.

---

## 7. SEO Engine & Schema Generator

### SEO report dimensions (v1 heuristics)

Title, Description, Heading hierarchy, Image alt/optimization flags, Internal links count/quality, Schema presence, Entity coverage, Semantic/topical coverage, Search intent match, Readability (Persian-aware later), Final score 0–100 + issue list.

### Schema builders (registry)

`Article`, `Product`, `BreadcrumbList`, `FAQPage`, `Organization`, `Brand`, `WebSite`, `SearchAction`, `Review`, `AggregateRating` — register by `page_type`.

Storefront may call `/knowledge/schema` **or** keep local builders that consume the same DTO from API (prefer single source: backend generator).

---

## 8. Search architecture

```text
Query
  → normalize (Persian digits/yeh/kaf)
  → FTS on search_documents / entity tsvector / product / article
  → boost by: exact alias match, entity type weights, relation popularity
  → group results: products | articles | entities | categories | brands
  → (future) vector recall merge
```

Admin synonym/alias edits immediately affect extract + search.

---

## 9. Admin Knowledge / SEO Dashboard (IA)

Widgets (fed by `admin_dashboard` + analytics module):

1. Articles health (score distribution)
2. Entity coverage (% articles/products with ≥N entities)
3. Missing topics (suggested entities from pipeline)
4. Clusters (relation communities — simple v1: by type)
5. Internal link suggestions queue
6. Broken links (crawl internal paths)
7. Schema coverage
8. SEO health score
9. Recommendations queue
10. Knowledge graph explorer (ego network per entity)

---

## 10. Background services

| Job type | Handler |
|----------|---------|
| `intelligence.article` | Full pipeline |
| `intelligence.product` | Lighter pipeline |
| `projection.sync` | SoR → entities |
| `search.reindex` | Rebuild tsvector / search_documents |
| `seo.analyze_page` | Single report |
| `links.refresh` | Batch suggestions |

**Runner:** `app/workers/runner.py`  
- Dev: started in FastAPI lifespan alongside order expiry (separate task)  
- Staging/Prod: preferred `python -m app.workers.runner` as second process in compose  

Same DB queue → no broker required for years of catalog-scale load.

---

## 11. Migration strategy

### Stage A — Foundation (no UX change)
1. Alembic: knowledge tables + jobs + article meta columns  
2. Seed entity_types + relation_types  
3. Project existing brands/categories/products/articles → entities (`sor_*`)  
4. Dual-write hooks: brand/product/category/article write also upserts projection  

### Stage B — Read APIs
5. Ship `/api/v1/knowledge` read endpoints  
6. Admin entity/relation CRUD  
7. FTS indexer for products+articles+entities  

### Stage C — Intelligence
8. Rule-based extractor + pipeline + jobs worker  
9. Link suggestions + SEO reports persisted  
10. Schema endpoint  

### Stage D — Presentation
11. Storefront entity/brand/category hubs + slug PDP (+ redirects)  
12. Unified search page  
13. Admin SEO dashboard + graph visualizer  
14. Deprecate reliance on `related_product_ids` / meta-block (keep read fallback)  

### Stage E — Hardening
15. Backfill analyses for all published articles  
16. Remove dual-read shims only when FE fully switched  
17. Optional vector search  

**Rollback:** each Alembic expandable; feature flags `KNOWLEDGE_ENABLED`, `KNOWLEDGE_PIPELINE_ENABLED`, `KNOWLEDGE_SEARCH_ENABLED`.

---

## 12. Compatibility & risk controls

| Risk | Control |
|------|---------|
| Break checkout | Knowledge code never imports payment/cart services |
| Slow requests | Heavy work only via jobs |
| Bad auto-links | Suggestions default **pending**; publish requires accept or high confidence threshold |
| Duplicate entities | Unique (type, slug); merge tool in admin later |
| SEO regress | Keep existing blog JSON-LD until schema endpoint proven |
| Scope explosion | Phase 3 orders **one module slice per implementation phase** |

---

## 13. Mapping: mission modules → delivery slices

| Mission module | Primary package | First shippable slice |
|----------------|-----------------|------------------------|
| Knowledge Graph | `knowledge/graph` + tables | Projection + neighborhood API |
| Entity Engine | `knowledge/entity` | Types + entities CRUD + aliases |
| Relation Engine | `knowledge/relation` | Types + relations CRUD |
| Content Intelligence | `knowledge/intelligence` | Pipeline skeleton + rule extractor |
| Internal Link Engine | `knowledge/links` | Suggestions table + admin queue |
| SEO Engine | `knowledge/seo` | Heuristic report |
| Schema Generator | `knowledge/schema_gen` | Article+Product+Breadcrumb builders |
| Recommendation | `knowledge/recommend` | Graph neighbors fallback to category |
| Semantic Search | `knowledge/search` | FTS unified endpoint |
| Analytics | `knowledge/analytics` | Dashboard aggregates |
| Jobs | `workers` + `jobs` table | Enqueue/claim/retry |

---

## 14. Explicit non-goals (Phase 2 design)

- Microservices / separate knowledge DB server  
- Replacing `products` with entities for cart  
- LLM extraction as mandatory v1  
- Full graph visualization polish in first coding sprint  
- Deleting `/catalog?category=` before hubs prove parity  
- Resuming image import inside this design phase  

---

## 15. Phase 2 → Phase 3 gate

Phase 3 will produce an **ordered implementation roadmap** with complexity estimates and dependencies, sliced so each coding phase delivers **one** major module (or thin vertical of Entity+Relation foundation only).

**Please confirm:**

1. Folder layout under `app/knowledge/` + `endpoints/knowledge/` is accepted  
2. DB overlay + bridge tables accepted  
3. Additive `/api/v1/knowledge` accepted  
4. Postgres jobs (no Celery yet) accepted  
5. Migration stages A→E accepted as strategy  

---

*End of Phase 2 design. No application code or migrations were executed for implementation.*
