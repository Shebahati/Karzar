---
id: FULL-PLATFORM-ARCHITECTURE-AUDIT
version: 0.1.0
status: Proposed
date: 2026-07-30
owner: Principal Software Architect
task_id: KB-001
pack: docs/architecture/specs/README.md
---

# Full Platform Architecture Audit

**Status:** Proposed (Evidence-oriented audit + architecture inventory — not Canon Lock)  
**Scope:** Repository as of branch base including Knowledge Foundation SPECs; runtime + docs  
**Non-goals:** Code changes · score inflation · inventing absent ADR-001…009 text

---

## 1. Executive verdict

KarzarTools is a **mature modular-monolith industrial commerce platform** with:

- Strong catalog SoR (`products` / `categories` / `brands` / images)
- Production-grade cart/order/payment/auth
- Thin CMS (articles + soft product links)
- EPIC-1 SEO URL surfaces largely **shipped in Storefront** (`/product/{slug}`, `/categories/{slug}`, `/brands/{slug}`)
- Rich offline import/enrichment script surface + binding ingestion policy

It is **not yet** an industrial knowledge platform:

- No `app/knowledge/` package
- No `/api/v1/knowledge/*` routes (OpenAPI: 0 knowledge paths)
- Specs = opportunistic JSONB + in-code admin templates
- No Manufacturer, Property Dictionary, Facts, Evidence, typed edges, or multi-dimensional taxonomy tables
- Knowledge Foundation SPECs exist as **Proposed** design only

**Strategic direction (already locked in docs, not reinvented):** keep commerce SoR; add knowledge overlay; additive APIs; JSONB strangler until Property dual-write is Board-gated.

---

## 2. Current architecture map

```text
┌─────────────────────────────────────────────────────────────┐
│ Storefront (Next.js)     Admin Panel (Next.js)              │
│ /product/{slug}          catalog / CMS / nav-groups         │
│ /categories/{slug}                                          │
│ /brands/{slug}                                              │
│ /catalog · /blog · sitemap                                  │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP /api/v1
┌────────────────────────────▼────────────────────────────────┐
│ FastAPI                                                     │
│ products · categories · brands · cms · cart · orders · …  │
│ (no knowledge router)                                       │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   services/              crud/                 utils/
   (commerce-strong;      (SQLAlchemy)          (specs dual-shape,
    spec_template_service)                       SEO description helpers)
                             │
                             ▼
                    PostgreSQL karzar_db
                    products.specifications JSONB + GIN
                             ▲
                             │
                    scripts/* + data/imports/*
                    (Category A → local API; ADR-012)
```

**Cite:** `app/main.py` mounts `/api/v1`; models `app/db/models/product.py`, `content.py`, `commerce.py`; Phase 2 target still design-only (`docs/KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md`).

---

## 3. Current entity model (as-built)

| Entity | Table | Identity | Knowledge-relevant notes |
|--------|-------|----------|--------------------------|
| Product | `products` | `id`, unique active `sku`, unique `slug` | Prices, `is_available`, JSONB specs, SEO scalars, soft delete — `product.py:130-204` |
| Category | `categories` | `id`, unique `slug`, `parent_id` | Merchandising tree; `spec_template_key`; megamenu flags — `:72-112` |
| Brand | `brands` | `id`, unique `name`/`slug` | No Manufacturer split — `:115-127` |
| ProductImage | `product_images` | per product | primary + `display_order` |
| Article | `articles` | `slug` | `related_product_ids` JSONB (untyped) — `content.py:31-45` |
| MegamenuNavGroup | `megamenu_nav_groups` | `slug` | Merchandising over L1 — **D1** |
| Order / Cart / Payment | commerce/platform | tracking codes | Out of knowledge SoR |
| Hesabfa maps | hesabfa | SKU↔ERP | Commerce integration |

**Missing first-class entities:** Manufacturer, PKE (distinct), TaxonomyNode (knowledge), Property Definition, Fact, Evidence/Document (beyond `pdf_catalog_url`), Standard, Certification, KnowledgeEdge, KnowledgeModule.

---

## 4. Current data flow

### 4.1 Read path (PDP)

```text
Storefront /product/{slug}
  → GET /api/v1/products/slug/{slug} (or id fallback + redirect)
  → ProductDetailResponse (specifications dict normalized for storefront arrays)
  → JSON-LD Product/Offer/Breadcrumb
```

### 4.2 Write path (catalog)

```text
Admin UI / scripts
  → POST|PUT /api/v1/products/  (Admin auth)
  → ProductService → CRUD
  → products row (+ JSONB specs)
```

### 4.3 Import / enrichment (ops)

```text
SOURCE-DEPOSIT (data/imports/<vendor>/…)
  → crawl JSONL / CSV / PDF extract
  → scripts/*_import.py | *_enrich*.py
  → ingestion_boundary.resolve_api_base()  (fail-closed vs production)
  → local Admin API writes (Category A)
```

**Cite:** `docs/architecture/data-ingestion-policy.md`; `scripts/ingestion_boundary.py`; examples `mitutoyo_import.py`, `enrich_mitutoyo_from_leaflets.py`.

---

## 5. Current SEO model

| Concern | As-built (Storefront on mainline) | Governing doc |
|---------|-----------------------------------|---------------|
| PDP | `/product/{slug}`; numeric → permanentRedirect to slug | ADR-010 |
| Category hub | `/categories/{slug}`; faceted qs → noindex | ADR-010 · url-map |
| Brand hub | `/brands/{slug}`; thin hubs may noindex | ADR-010 · RFC-005 · brand-hub contract |
| Catalog | `/catalog` facets; category id may redirect to hub | crawl-hygiene |
| Blog | `/blog`, `/blog/{slug}` | IA transitional |
| Sitemap | products (slug preferred), categories, brands≥1, articles | `sitemap.ts` |
| JSON-LD | Org/WebSite; Product/Offer; CollectionPage; Article | storefront `lib/json-ld.ts` |
| Knowledge hubs | `/guides`, Tool Class, Application, Standards | **Absent** (IA deferred) |

**Doc debt:** ADR-010 / IA §5 “CURRENT” prose still describes pre-cutover id PDP / missing brand hubs — prefer code + Accepted decisions for runtime truth (**CF-SPEC-05**).

---

## 6. Current import model

| Pattern | Examples | Trust |
|---------|----------|-------|
| Crawl → JSONL → import | Mitutoyo, Azarsanat, Shopmill/INSIZE | Medium; map-driven |
| OEM catalog enrich | Dasqua/Dohre/Chumpower/SAN OU | Higher when PDF deposited |
| CSV seed | `seed_products_from_csv.py`, `data/imports/*.csv` | Variable |
| Price reconcile | `import_price_lists.py`, `reconcile_prices_availability.py` | Commercial |
| SEO content publish | `publish_seo003_articles.py` | Category B CMS |
| Images | multiple `import_*_images_*` | Media track (D16) |

**Gaps vs playbook:** no unified stage machine; classification often hardcoded (`CATEGORY_RULES` in `mitutoyo_import.py`); no entity-resolution service; no Fact provenance tables; AI invent limits are policy/prose, not enforced in app.

---

## 7. Spec / template reality

| Layer | Reality |
|-------|---------|
| Storage | `products.specifications` JSONB + GIN |
| Default factory | Measurement-shaped keys for all products — `get_default_specifications()` `product.py:49-68` |
| Admin templates | In-code dicts: `default`, `measurement`, `insert`, `insert_holder`, `end_mill`, `drill` — `spec_template_service.py:135-142` |
| Binding | `categories.spec_template_key` walk-up resolve |
| API dual-shape | Storefront arrays vs admin maps — `app/utils/specifications.py` |
| FA/EN | Mixed keys in imports; no Property Dictionary |

This is **operational PIM scaffolding**, not a governed property system.

---

## 8. Frontend / navigation (as-built)

| Surface | Path |
|---------|------|
| Home + megamenu | Category hubs via L1 + `MegamenuNavGroup` |
| Catalog PLP | Facets: brand, category, `spec_*`, price, stock, search |
| PDP | Slug identity; PDF CTA + accessories slot (honest empty) |
| Brand strip | Links to `/brands/{slug}` |
| Blog | Strongest historical knowledge gravity |

Admin: product/category/brand CRUD, CMS articles, nav-groups — no Knowledge Graph UI.

---

## 9. Current limitations

1. Brand conflates manufacturer identity.
2. Single merchandising taxonomy cannot answer Application / Industry / Tool Class.
3. Specs ungoverned → weak compare, weak FA/EN collapse, weak Evidence.
4. Relationships soft/untyped → KB-001 blocked on vocabulary + storage ADR.
5. No knowledge job framework in-app (scripts only).
6. Evidence/PDF coverage historically ≈ 0 → generative AI remains gated (Bible P4).
7. Description fields are blobs, not module types.
8. Scale of relationships (millions) not modeled in schema.

---

## 10. Technical debt (architecture-relevant)

| Debt | Evidence |
|------|----------|
| Measurement-biased JSONB defaults | `product.py:49-68` |
| Soft `related_product_ids` | `content.py:43` |
| `optional_accessories` empty pattern | default specs |
| Stale “CURRENT IA” in Accepted docs vs shipped routes | ADR-010 context vs Storefront |
| Spec templates in Python, not versioned dictionary tables | `spec_template_service.py` |
| Per-vendor import rule duplication | `CATEGORY_RULES` etc. |
| Phase 1/2/3 knowledge docs vs Wave-1 Canon Lock partial promotion | Canon Lock §3 |

---

## 11. Conflicts (surface, do not silently resolve)

| ID | Conflict | Authority note |
|----|----------|----------------|
| CF-SPEC-01 | KB-001 “no second taxonomy” vs multi-dim knowledge taxonomy | Commerce tree stays single; knowledge dimensions orthogonal |
| CF-SPEC-02 | Brand ≈ manufacturer today vs required split | UD-01 |
| CF-SPEC-03 | JSONB SoT vs Property/Facts | Bible P6 strangler |
| CF-SPEC-04 | Reserved `domain/`/`pim/`/`knowledge-graph/` vs `specs/` | Interim in-repo foundation |
| CF-SPEC-05 | Docs CURRENT vs shipped SEO routes | Prefer code + ADR decisions |
| CF-AUD-01 | Phase-3 image pause vs D16 CATALOG_IMAGES_PLAN | D16 winning side for images |
| CF-AUD-02 | Next `permanentRedirect` (308) vs ADR “301” wording | Behaviorally permanent; status-code pedantry open |

---

## 12. Missing architecture layers (this completion pack)

| Layer | Deliverable in this phase |
|-------|---------------------------|
| Unified domain ER | `SPEC-domain-model.md` |
| Property Dictionary | `SPEC-property-dictionary-system.md` |
| Taxonomy seed | `SPEC-industrial-taxonomy-master-seed.md` |
| Relation registry | `SPEC-knowledge-graph-registry.md` |
| Transform architecture | `SPEC-data-transformation-architecture.md` |
| Target platform blueprint | `KNOWLEDGE_PLATFORM_TARGET_ARCHITECTURE.md` |
| Impl readiness gate | `FOUNDATION_IMPLEMENTATION_READINESS.md` |
| Foundation critique | `FOUNDATION_ARCHITECTURE_REVIEW.md` |

---

## 13. What must be preserved

1. Commerce SoR tables and checkout/payment integrity  
2. Single commerce Category tree + megamenu-as-presentation (**D1**)  
3. ADR-010 / RFC-004 / RFC-005 URL contracts  
4. ADR-012 / ingestion policy fail-closed boundary  
5. JSONB readability until Board enables dual-write  
6. AODS / Canon Lock process (no self-Accept)

---

## 14. Audit method notes

- Backend inventory: models, Alembic catalog/SEO migrations, OpenAPI path scan (0 knowledge), scripts classification  
- Frontend: Storefront App Router routes + ADR-010 TARGET alignment  
- Docs: Canon Lock Accepted set; Knowledge Foundation SPECs Proposed  
- Product row counts / quality scores: cite EPIC 0 historical numbers in Bible when needed; this audit does not re-measure production DB (no live DB in this environment)
