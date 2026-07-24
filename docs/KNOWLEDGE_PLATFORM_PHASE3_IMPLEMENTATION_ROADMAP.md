# KarzarTools — Phase 3 Implementation Roadmap

**Status:** Complete — awaiting approval to start **Implementation Slice I0** (first coding phase)  
**Date:** 2026-07-22  
**Depends on:**  
- [Phase 1 Audit](./KNOWLEDGE_PLATFORM_PHASE1_ARCHITECTURE_AUDIT.md)  
- [Phase 2 Target Architecture](./KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md)

**Rule:** After this document is approved, coding proceeds **one Implementation Slice (I-n) at a time**, with your explicit OK before the next slice. Never implement multiple major modules in parallel.

**Paused:** Product image import — reopen only after you say so (recommended: after I3 or I5 when hubs/SEO exist).

---

## 0. How to read this roadmap

| Term | Meaning |
|------|---------|
| **I-n** | Implementation Slice — one mergeable coding unit |
| **Complexity** | S ≤0.5d · M 0.5–1.5d · L 1.5–3d · XL 3–5d (agent+review calendar days, not wall-clock alone) |
| **d** | Focused engineering day ≈ 6–8h |
| **Dep** | Must be Done before start |
| **Gate** | You approve before next I-n |

**Total guided estimate (I0→I12):** ~**18–32 engineering days** (≈ 4–7 weeks calendar if sequential with review gates).  
Optional later (I13+): vectors, LLM extractors, graph viz polish — not required for MVP knowledge platform.

---

## 1. Dependency graph (high level)

```text
I0 Flags + package skeleton
 └─ I1 DB: knowledge + jobs + article meta
     └─ I2 Entity Engine (CRUD + aliases + seed types)
         └─ I3 Relation Engine (CRUD + seed relations)
             └─ I4 Projection SoR→Entity + dual-write
                 ├─ I5 Graph read API (neighborhood + public entity get)
                 ├─ I6 Jobs worker foundation
                 │    └─ I7 Content Intelligence pipeline (rule extractor)
                 │         ├─ I8 Internal Link Engine
                 │         ├─ I9 SEO Engine + reports
                 │         └─ I10 Schema Generator endpoint
                 ├─ I11 Search FTS unified
                 └─ I12 Recommend (graph + fallback)
                        └─ I13 Storefront hubs + slug PDP   [FE]
                        └─ I14 Admin Knowledge + SEO dashboard [FE]
                        └─ I15 Hardening / backfill / deprecations
```

**Critical path to “graph alive in API”:** I0 → I1 → I2 → I3 → I4 → I5  
**Critical path to “intelligence loop”:** … → I6 → I7 → (I8∥I9∥I10)  
**Critical path to “user-visible knowledge SEO”:** … → I11 + I13 + I14

---

## 2. Feature flags (introduce in I0)

| Flag | Default | Purpose |
|------|---------|---------|
| `KNOWLEDGE_ENABLED` | false | Mount routers / allow projection |
| `KNOWLEDGE_PIPELINE_ENABLED` | false | Worker runs intelligence jobs |
| `KNOWLEDGE_SEARCH_ENABLED` | false | Unified search endpoint live |
| `KNOWLEDGE_STOREFRONT_HUBS` | false | FE entity/brand/category hubs |

Staging can flip flags per slice without blocking commerce.

---

## 3. Implementation slices (ordered)

### I0 — Skeleton & governance
| | |
|--|--|
| **Goal** | Create empty packages, ports stubs, flags, mount empty router behind flag |
| **Touches** | `app/knowledge/**` stubs, `app/api/endpoints/knowledge/__init__.py`, `config.py`, docs pointer |
| **Complexity** | S |
| **Deps** | Phase 2 approved |
| **Tests** | App boots; `/api/v1/knowledge/health` 404 if flag off, 200 if on |
| **Out of scope** | Models, migrations, real CRUD |
| **Gate** | Approve → I1 |

---

### I1 — Database foundation
| | |
|--|--|
| **Goal** | Alembic migration for overlay tables + jobs + article SEO columns |
| **Tables** | `entity_types`, `entities`, `entity_aliases`, `relation_types`, `relations`, `article_entities`, `product_entities`, `category_entities`, `entity_images`, `jobs`, `content_analyses`, `link_suggestions` (+ optional `schema_snapshots`) |
| **SoR additive** | `articles.meta_title`, `articles.meta_description` |
| **Complexity** | L |
| **Deps** | I0 |
| **Tests** | Migration upgrade/downgrade on clean DB; model import smoke |
| **Out of scope** | Business logic, APIs |
| **Gate** | Approve → I2 |

---

### I2 — Entity Engine (first major module)
| | |
|--|--|
| **Goal** | Configurable entity types + entities + aliases; admin CRUD |
| **Deliverables** | Seed system `entity_types`; `crud/knowledge/entities.py`; `knowledge/entity/service.py`; admin endpoints; Pydantic schemas |
| **Complexity** | L |
| **Deps** | I1 |
| **Tests** | Create/update/archive entity; unique (type, slug); alias uniqueness |
| **Out of scope** | Relations, pipeline, FE |
| **Module** | M1 Entity Engine |
| **Gate** | Approve → I3 |

---

### I3 — Relation Engine (second major module)
| | |
|--|--|
| **Goal** | Configurable relation types + edges + basic traversal |
| **Deliverables** | Seed relation types; relation service; admin CRUD; prevent self-loops / duplicates |
| **Complexity** | M–L |
| **Deps** | I2 |
| **Tests** | Create edge; list outbound/inbound; symmetric handling if flagged |
| **Out of scope** | Auto-extraction, FE graph viz |
| **Module** | M2 Relation Engine |
| **Gate** | Approve → I4 |

---

### I4 — SoR projection & dual-write
| | |
|--|--|
| **Goal** | Every brand/category/product/article projects to an `entities` row (`sor_table`/`sor_id`) |
| **Deliverables** | `knowledge/entity/projection.py`; sync command/job; hooks from brand/product/category/article services (non-blocking / best-effort with log) |
| **Complexity** | L |
| **Deps** | I2 (I3 useful for `manufactured_by` / `belongs_to` edges but can land soft relations in same slice or thin follow-up) |
| **Tests** | Sync idempotent; updating product name updates entity name; unique sor pointer |
| **Also** | Create baseline relations: product `manufactured_by` brand, product `belongs_to` category (when I3 done) |
| **Out of scope** | Storefront hubs |
| **Module** | M3 Graph façade (projection part) |
| **Gate** | Approve → I5 |

---

### I5 — Graph read API (Knowledge Graph usable)
| | |
|--|--|
| **Goal** | Public/admin read: entity by type/slug + neighborhood |
| **Deliverables** | `GET /knowledge/entities/{type}/{slug}`, `GET .../neighborhood`; related products/articles via bridges when present |
| **Complexity** | M |
| **Deps** | I4 |
| **Tests** | Projected brand/product resolvable; neighborhood includes seeded edges |
| **Out of scope** | Pipeline, search UI |
| **Module** | M3 Knowledge Graph |
| **Gate** | Approve → I6 **or** optional parallel planning for FE later |
| **Milestone** | **MVP Graph API** |

---

### I6 — Jobs worker foundation
| | |
|--|--|
| **Goal** | Durable queue: enqueue, claim, retry, dead-letter; CLI/lifespan runner |
| **Deliverables** | `jobs` CRUD; `app/workers/runner.py`; `PostgresJobQueue` port impl; admin job list |
| **Complexity** | L |
| **Deps** | I1 (can start after I1 technically; **scheduled after I5** so graph exists before heavy jobs) |
| **Tests** | Claim concurrency safe; retry backoff; max attempts → dead |
| **Out of scope** | Intelligence steps |
| **Module** | M11 Jobs |
| **Gate** | Approve → I7 |

---

### I7 — Content Intelligence pipeline (core)
| | |
|--|--|
| **Goal** | Pipeline orchestrator + rule-based entity extractor + persist analyses stub |
| **Deliverables** | Steps 1–2–3 skeleton; `RuleBasedExtractor` using aliases + brand/tool lexicon; job type `intelligence.article`; write `article_entities` |
| **Complexity** | XL |
| **Deps** | I5, I6 |
| **Tests** | Fixture article (vernier) extracts known entities; job succeeds; idempotent re-run |
| **Out of scope** | LLM; perfect Persian NLP |
| **Module** | M4 Content Intelligence |
| **Gate** | Approve → I8 (links first) |
| **Milestone** | **MVP Intelligence** |

---

### I8 — Internal Link Engine
| | |
|--|--|
| **Goal** | Entity-based link suggestions; admin accept/reject |
| **Deliverables** | `link_suggestions` fills from pipeline step; admin PATCH; no auto-publish into article HTML in v1 (suggest only) |
| **Complexity** | M |
| **Deps** | I7 |
| **Tests** | Suggestion created for known entity mention; reject hides from queue |
| **Module** | M5 Internal Link Engine |
| **Gate** | Approve → I9 |

---

### I9 — SEO Engine
| | |
|--|--|
| **Goal** | Heuristic SEO report + score persisted on `content_analyses` |
| **Deliverables** | Analyzer dimensions from Phase 2; `GET /knowledge/admin/seo/report`; pipeline step |
| **Complexity** | L |
| **Deps** | I7 (can share analysis row) |
| **Tests** | Missing title → issue; score bounds 0–100 |
| **Module** | M6 SEO Engine |
| **Gate** | Approve → I10 |

---

### I10 — Schema Generator
| | |
|--|--|
| **Goal** | Registry + builders; `GET /knowledge/schema` |
| **Deliverables** | Article, Product, Breadcrumb, FAQ, Organization, WebSite, SearchAction builders; extendable registry |
| **Complexity** | M–L |
| **Deps** | I5 (entity/product context); I9 optional for “schema present” checks |
| **Tests** | Article fixture returns valid `@graph` keys; product offer fields when price present |
| **Module** | M7 Schema Generator |
| **Gate** | Approve → I11 |
| **Note** | Storefront may keep local JSON-LD until I13 switches to API |

---

### I11 — Semantic Search (FTS v1)
| | |
|--|--|
| **Goal** | Unified search across products, articles, entities (grouped) |
| **Deliverables** | tsvector columns/triggers or `search_documents`; indexer job; `GET /knowledge/search`; flag `KNOWLEDGE_SEARCH_ENABLED` |
| **Complexity** | XL |
| **Deps** | I4 (projections), I6 (reindex jobs); aliases from I2 |
| **Tests** | Search brand name returns brand entity + products; Persian yeh/kaf normalize basic |
| **Out of scope** | Embeddings / vector DB |
| **Module** | M9 Semantic Search (FTS stage) |
| **Gate** | Approve → I12 |
| **Milestone** | **MVP Knowledge Search** |

---

### I12 — Recommendation Engine
| | |
|--|--|
| **Goal** | Graph neighbors for related products/articles; fallback to existing category heuristic |
| **Deliverables** | `GET /knowledge/recommendations`; optional wire into `GET /products/{id}/related` behind flag |
| **Complexity** | M |
| **Deps** | I5; richer after I7 bridges |
| **Tests** | Same response shape as current related when fallback; graph path when edges exist |
| **Module** | M8 Recommendation Engine |
| **Gate** | Approve → I13 |

---

### I13 — Storefront presentation (FE)
| | |
|--|--|
| **Goal** | User-visible knowledge IA |
| **Deliverables** | `/entity/[type]/[slug]`, `/brand/[slug]`, `/category/[slug]` landings; `/product/[slug]` + redirect from id; `/search` unified; consume schema/search APIs; scoped related articles on PDP |
| **Complexity** | XL |
| **Deps** | I5, I10, I11 (I12 preferred) |
| **Tests** | Playwright/smoke: hub 200, product slug redirect, search groups render |
| **Out of scope** | Pixel-perfect graph viz |
| **Gate** | Approve → I14 |

---

### I14 — Admin Knowledge & SEO Dashboard (FE)
| | |
|--|--|
| **Goal** | Operate the graph and SEO health |
| **Deliverables** | Nav: entities, relations, link suggestions, jobs, SEO dashboard (coverage, scores, missing topics); light graph neighborhood view |
| **Complexity** | XL |
| **Deps** | I2–I3, I8–I9, I6; analytics aggregates API (thin, can be part of this slice or I9b) |
| **Module** | M10 Analytics surface |
| **Gate** | Approve → I15 |

---

### I15 — Hardening & deprecations
| | |
|--|--|
| **Goal** | Production readiness of knowledge track |
| **Deliverables** | Backfill analyses for published articles; dual-write monitoring; document deprecation of meta-block & plan to freeze `related_product_ids` writes; perf indexes; staging flag-on soak |
| **Complexity** | L |
| **Deps** | I13–I14 in use on staging |
| **Gate** | **Knowledge Platform MVP complete** → reopen image import or I16+ |

---

## 4. Optional later slices (not MVP)

| ID | Item | Complexity | When |
|----|------|------------|------|
| I16 | Embedding / hybrid search | XL | After search quality plateaus |
| I17 | LLM extractor port | L | After rule-based lexicon mature |
| I18 | Full force-directed graph visualizer | L | After curators need it |
| I19 | Merge duplicate entities tool | M | When projection noise appears |
| I20 | Broken-link crawler job | M | After hubs indexed |

---

## 5. Cross-cutting work (apply inside slices, not separate mega-PRs)

| Concern | Policy |
|---------|--------|
| Auth | Knowledge admin = `super_admin`; destructive = step-up |
| Layering | endpoints → services/engines → crud → models |
| Tests | Each I-n lands with pytest for its module |
| Docs | Update `API_CONTRACT` / OpenAPI tags per slice |
| Commerce safety | No imports from knowledge → payment/cart |
| Commits | Prefer one PR per I-n |

---

## 6. Effort summary

| Band | Slices | Est. days |
|------|--------|-----------|
| Foundation API graph | I0–I5 | 6–10 |
| Intelligence + SEO/schema/links | I6–I10 | 7–12 |
| Search + recommend | I11–I12 | 3–5 |
| FE Storefront + Admin | I13–I14 | 5–8 |
| Hardening | I15 | 1–2 |
| **MVP total** | **I0–I15** | **≈ 22–37** (use 18–32 if FE thinner) |

Parallelism allowed **only** after I5: e.g. FE shell mocked vs I6 — still **one agent coding slice at a time** unless you explicitly split humans.

---

## 7. Definition of MVP (exit criteria)

Knowledge Platform MVP is done when:

1. Brands/products/categories/articles project to entities  
2. Admin can curate entities, aliases, relations  
3. Article pipeline extracts entities (rule-based) and stores SEO score  
4. Link suggestions queue works  
5. Schema endpoint serves Article+Product JSON-LD  
6. Unified FTS search returns mixed groups  
7. Storefront has at least brand + entity hub + slug PDP redirect  
8. Admin has SEO/knowledge dashboard v1  
9. Flags on staging for 48h without commerce regressions  

Then: resume **product image import** (prior phase plan) if you want.

---

## 8. What we will implement first after your OK

**Next coding phase = I0 only** (skeleton + flags + health route).  
Stop and ask before I1.

---

## 9. Approval checklist (Phase 3 gate → coding)

Confirm:

1. Slice order I0→I15 accepted  
2. One-slice-at-a-time gate accepted  
3. MVP definition accepted  
4. Optional I16+ deferred  
5. Image import stays paused until you reopen  
6. Start coding with **I0** on your go-ahead  

---

*End of Phase 3. No application code was implemented in this phase.*
