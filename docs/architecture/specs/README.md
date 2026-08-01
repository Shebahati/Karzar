# Knowledge Foundation Specs Pack

**Status:** **Accepted** (Architecture Board · ۱۴۰۵/۰۵/۱۰ · Mohammad Shebahati · Day-2 minute)  
**Date:** 2026-07-30  
**Parents:** [`../karzar-knowledge-platform-master-architecture.md`](../karzar-knowledge-platform-master-architecture.md) · [`../CANON-LOCK.md`](../CANON-LOCK.md)  
**PMO:** prerequisite foundation for `KB-001` (content graph seed)  
**Board minute:** [`../../../aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md`](../../../aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md)  
**Non-goals:** Code/migrations in *this* pack PR · MASTER_* documents · parallel authority systems · dual-write / RAG (still Board-gated)

This pack is the **living Accepted knowledge foundation** under `docs/architecture/specs/` (UD-07: reserved `domain/` / `knowledge-graph/` / `pim/` paths remain deferred). Core SPECs below are Canon Lock §1c merge criteria; seed/audit/target/readiness/FA summary remain Proposed/REFERENCE.

---

## 0. Repository context analysis (Phase 1)

### 0.1 What already exists (preserve)

| Layer | As-built | Cite |
|-------|----------|------|
| Commerce Product | `products` with SKU, slug, price, availability, stock fields, soft delete | `app/db/models/product.py:130-204` |
| Merchandising Category | Self-referential tree, depth discipline, `spec_template_key`, megamenu flags | `app/db/models/product.py:72-112` |
| Brand | Name/slug/country/logo/meta; used as commerce facet + EPIC-1 hub | `app/db/models/product.py:115-127` · ADR-010 · RFC-005 |
| Specs store | Uncontrolled JSONB (`technical_specs` / `features` / `dimensions` / `optional_accessories`) | `app/db/models/product.py:49-68`, `:190-192` |
| CMS Article | Soft `related_product_ids` JSONB; blocks; tags | `app/db/models/content.py:31-45` |
| Megamenu | Merchandising overlay over L1 roots — **not** a second taxonomy | `app/db/models/content.py:62-74` · PMO **D1** |
| SEO/URL contract | `/product/{slug}`, `/categories/{slug}`, `/brands/{slug}` | ADR-010 |
| Dual-axis IA | Knowledge Axis vs Commerce Axis | `information-architecture/karzar-information-architecture.md` §3 |
| Ingestion boundary | Category A local-only; mandatory Source/Destination/Owner/Validation/Audit/Rollback | ADR-012 · `data-ingestion-policy.md` |
| Knowledge overlay intent | Modular monolith; KG overlay on SoR; additive `/api/v1/knowledge/*` | `docs/KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md` §0–§2 |
| Bible principles | Identity before intelligence; Evidence before generation; Category ≠ Tool Class; JSONB until approved migration | Master Architecture P3–P7 |

### 0.2 What must be preserved

1. **Commerce SoR tables** (`products`, `brands`, `categories`, `articles`, orders/cart) remain systems of record for sell/inquire — Bible §0 SoT planes; Phase 2 Decision “Knowledge Graph = Overlay”.
2. **Category tree** remains the **commerce merchandising** taxonomy (depth ≤ 3); megamenu stays presentation over L1 (**D1**).
3. **ADR-010 / RFC-004 / RFC-005** URL and Brand Hub contracts — knowledge work MUST NOT invent alternate PDP/hub URL classes.
4. **Ingestion policy + ADR-012** — enrichment never defaults to production API.
5. **Canon Lock / AODS** — core SPECs in this pack are **Accepted** (Day-2 · ۱۴۰۵/۰۵/۱۰); further status upgrades still require Board + minute + Canon Lock rows.
6. **JSONB operational** until Property/Facts dual-write is Board-gated (Bible P6) — specs here define the **target governed model**, not a big-bang drop.

### 0.3 What is missing

| Gap | Impact |
|-----|--------|
| Product Knowledge Entity distinct from commerce SKU row | Meaning, lifecycle, manufacturer≠brand, family/series/variant absent as first-class concepts (Bible §3) |
| Multi-dimensional industrial taxonomy | Only one merchandising tree; no Application / Industry / Tool Family axes |
| Governed Property/Specification dictionary | JSONB keys free-text; measurement-biased defaults (`get_default_specifications`) |
| Typed Knowledge Graph | Soft JSON arrays (`related_product_ids`, `optional_accessories`); no edge types/provenance |
| Knowledge content types | One `description` + blog articles; no overview / how-to / selection / FAQ modules as entities |
| Manufacturer entity | Collapsed into Brand |
| Import/enrichment playbook spanning identity → classification → knowledge → SEO → human review | Scripts exist per vendor; no unified lifecycle stages |
| Evidence / Source / Certification / Standard entities | PDF fill ≈ 0; AI gated (Bible P4) |

### 0.4 Conflict risks (do not silently pick winners)

| ID | Tension | Handling in this pack |
|----|---------|------------------------|
| **CF-SPEC-01** | `KB-001` AC “avoid second taxonomy” / “No DAG categories” vs multi-dimensional industrial taxonomy | Commerce Category stays **one** merchandising tree. Knowledge taxonomy is **orthogonal dimensions** (Domain / Family / Application / Industry), not a second storefront category DAG. See SPEC-industrial-taxonomy §1.3. |
| **CF-SPEC-02** | Bible Brand orientation treats Brand ≈ manufacturer label; identity model requires Manufacturer ≠ Brand | SPEC-product-knowledge separates them; migration of existing `brands` rows needs Board decision (UD-01). |
| **CF-SPEC-03** | Bible P6 JSONB remains operational vs governed Spec Definitions | Strangler: Property Dictionary + Facts overlay; JSONB readable until dual-write gate (no schema rewrite ordered here). |
| **CF-SPEC-04** | Historical reserved paths `domain/` / `knowledge-graph/` / `pim/` vs this `specs/` location | Pack is interim foundation in-repo; Board may later promote/rename into reserved packs without changing meaning. Do **not** invent missing ADR-001…009 contents. |
| **CF-SPEC-05** | Phase-1 audit CURRENT IA (id PDP, no brand hub) vs Wave-1 Accepted ADR-010 TARGET | Prefer Accepted Canon Lock documents over stale Phase-1 “CURRENT” prose for URL truth. |

### 0.5 Commerce-specific vs knowledge-layer split

| Remain commerce-specific | Move / add in knowledge layer |
|--------------------------|-------------------------------|
| `base_price`, `original_price`, `tax_percent` | Product Knowledge Entity identity & classification |
| `is_available`, warehouse/Hesabfa stock, `stock_movements` | Technical Facts (Property + value + unit + provenance) |
| Order/cart/payment | Applications, Industries, Standards, Certifications |
| Merchandising Category placement + megamenu | Tool Family / Product Type ontological class |
| Offer/availability messaging | Educational content modules (overview, how-to, guides) |
| Supplier commercial terms | Typed relationships (compatible, alternative, explains) |

---

## 1. Pack contents

### 1.1 Foundation SPECs (2026-07-30)

| Spec | Path | Owns |
|------|------|------|
| Product Knowledge Entity Model | [`SPEC-product-knowledge-entity-model.md`](./SPEC-product-knowledge-entity-model.md) | Identity, classification hooks, technical knowledge, content modules, relationship vocabulary |
| Industrial Taxonomy Model | [`SPEC-industrial-taxonomy-model.md`](./SPEC-industrial-taxonomy-model.md) | Multi-dimensional taxonomy, node types, SEO page rules, expansion without schema redesign |
| Knowledge Graph Model | [`SPEC-knowledge-graph-model.md`](./SPEC-knowledge-graph-model.md) | Nodes, edges, cardinality, identity, provenance, governance |
| Product Import & Enrichment Playbook | [`SPEC-product-import-enrichment-playbook.md`](./SPEC-product-import-enrichment-playbook.md) | Raw→production pipeline stages, AI limits, human review tiers |

### 1.2 Architecture completion pack (2026-07-30)

| Document | Path | Owns |
|----------|------|------|
| Full Platform Architecture Audit | [`FULL_PLATFORM_ARCHITECTURE_AUDIT.md`](./FULL_PLATFORM_ARCHITECTURE_AUDIT.md) | As-built map, SEO/import reality, debt, conflicts |
| Foundation Architecture Review | [`FOUNDATION_ARCHITECTURE_REVIEW.md`](./FOUNDATION_ARCHITECTURE_REVIEW.md) | Consistency critique of foundation SPECs |
| Domain Model | [`SPEC-domain-model.md`](./SPEC-domain-model.md) | Full logical ER, ownership, strangler map |
| Property Dictionary System | [`SPEC-property-dictionary-system.md`](./SPEC-property-dictionary-system.md) | Definitions, templates, Facts, FA/EN, units |
| Industrial Taxonomy Master Seed | [`SPEC-industrial-taxonomy-master-seed.md`](./SPEC-industrial-taxonomy-master-seed.md) | Concrete nodes + commerce L1 bridge |
| Knowledge Graph Registry | [`SPEC-knowledge-graph-registry.md`](./SPEC-knowledge-graph-registry.md) | Official relation vocabulary + publish rules |
| Data Transformation Architecture | [`SPEC-data-transformation-architecture.md`](./SPEC-data-transformation-architecture.md) | Mapping, duplicates, provenance, rollback |
| Knowledge Platform Target Architecture | [`KNOWLEDGE_PLATFORM_TARGET_ARCHITECTURE.md`](./KNOWLEDGE_PLATFORM_TARGET_ARCHITECTURE.md) | PDP composition; plane integration |
| Foundation Implementation Readiness | [`FOUNDATION_IMPLEMENTATION_READINESS.md`](./FOUNDATION_IMPLEMENTATION_READINESS.md) | What engineering may/may not build yet |
| خلاصه اجرایی فارسی | [`KNOWLEDGE_PLATFORM_ARCHITECTURE_SUMMARY_FA.md`](./KNOWLEDGE_PLATFORM_ARCHITECTURE_SUMMARY_FA.md) | One-page precise FA summary of the full pack |

### 1.3 Seeds (Git-first; not Canon alone)

| Seed | Path | Notes |
|------|------|-------|
| Property Dictionary v0 (metrology) | [`seeds/property-dictionary-v0-metrology.json`](./seeds/property-dictionary-v0-metrology.json) | UD-03 A · Day-4 · **no** dual-write |
| Taxonomy v0 (metrology) | [`seeds/taxonomy-v0-metrology.json`](./seeds/taxonomy-v0-metrology.json) | UD-03 A · Day-4 · bridge only · **no** second Category DAG |
| Classification map INSIZE v0 | [`seeds/classification-map-insize-v0-metrology.json`](./seeds/classification-map-insize-v0-metrology.json) | Readiness §5 · one brand · Git `MAPPING-TABLE` · **no** CLASSIFIED_AS projection |
| Seeds README | [`seeds/README.md`](./seeds/README.md) | Operator checklist + rules |

---

## 2. Architectural decision summary (Accepted — Day 2)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **D-KE-1** | Separate **Commerce Product** (SKU offer) from **Product Knowledge Entity** (meaning) | Bible P7 bounded contexts; price ≠ ontological essence |
| **D-KE-2** | Manufacturer and Brand are distinct entities | Industrial reality (OEM vs marketed brand); Bible §3 Series/Family gap |
| **D-TX-1** | Multi-dimensional taxonomy; commerce Category is one projection | Grainger/RS-style findability; CF-SPEC-01 |
| **D-TX-2** | New industrial domains = new taxonomy nodes + attribute templates, not DDL | 10-year expansion requirement |
| **D-KG-1** | Knowledge Graph is a **logical overlay** on Postgres SoR | Phase 2 locked decision; no cart SoR replacement |
| **D-KG-2** | Edges are typed, directional, provenanced; soft JSON arrays are transitional debt | Bible §3 Relation |
| **D-SPEC-1** | Governed Specification Definitions + Values (Facts); JSONB strangler | Bible P5–P6 |
| **D-IMP-1** | Pipeline stages mandatory; AI may classify/draft, MUST NOT invent specs/standards/prices | ADR-012 · Bible P4 |
| **D-IMP-2** | Human review risk tiers gate publish of knowledge Facts | Evidence before generation |

---

## 3. Dependency diagram

```text
┌─────────────────────────────────────┐
│  Product Knowledge Entity Model     │
│  (identity · meaning · content)     │
└─────────────────┬───────────────────┘
                  │ classified by
                  ▼
┌─────────────────────────────────────┐
│  Industrial Taxonomy Model          │
│  (domain · family · application ·   │
│   industry · technical class)       │
└─────────────────┬───────────────────┘
                  │ projected as
                  ▼
┌─────────────────────────────────────┐
│  Knowledge Graph Model              │
│  (nodes · typed edges · provenance) │
└─────────────────┬───────────────────┘
                  │ populated by
                  ▼
┌─────────────────────────────────────┐
│  Import & Enrichment Playbook       │
│  (raw → validate → resolve →        │
│   classify → enrich → review → prod)│
└─────────────────────────────────────┘
```

**Cross-mapping (import of one new product):**

1. **Entity identity** (SKU / manufacturer / model) → Product Knowledge Entity + Commerce Product link  
2. **Taxonomy assignment** → Domain + Tool Family + Application (+ Industry as applicable)  
3. **Graph edges** → Brand, Manufacturer, Category (commerce), Application, Standard, related Products  
4. **Enrichment tasks** → technical Facts, knowledge modules, SEO scalars — each with risk tier

---

## 4. Board decisions (Day 2 · 2026-08-01) + remaining opens

| ID | Question | Disposition |
|----|----------|-------------|
| **UD-06** | Accept core SPEC pack into Canon Lock? | **CLOSED — A** Accepted (core pack §1c); seed/audit/target/readiness/FA summary stay Proposed |
| **UD-05** | Graph storage | **CLOSED — A** → **ADR-013** Postgres tables only for wave-1 |
| **UD-02** | PKE identity | **CLOSED — A** → **ADR-014** `products.id` 1:1 wave-1 |
| **UD-03** | Dictionary seed scope | **CLOSED — A** Metrology first |
| **UD-08** | AI FA prose auto-publish | **CLOSED — A** Never auto-publish customer-facing FA AI prose |
| **OI-KF-04** | Phase1–3 vs specs pack | **CLOSED — A** Specs pack is living path; Phase docs HISTORICAL |
| **KB-001 freeze** | Wave-1 edges | **CLOSED — Yes** `PRODUCT_BELONGS_TO_CATEGORY`, `PRODUCT_BRANDED_AS`, `ARTICLE_EXPLAINS_PRODUCT` |
| **UD-01** | Manufacturer ≠ Brand migration | **OPEN — Deferred** after KB-001 edge slice |
| **UD-04** | Tool Class / Application indexable hubs | **OPEN — Deferred** (ADR-010 facet risk) |
| **UD-07** | Promote into reserved `domain/` / `pim/` / `knowledge-graph/` | **OPEN — Deferred** (keep `specs/`) |
| Dual-write / RAG | JSONB↔Facts; generative RAG | **OPEN — Deferred / Blocked** |

---

## 5. Recommended implementation sequence (post-Accept)

1. ~~**Board Accept** this pack (UD-06)~~ **Done** Day-2 minute + Canon Lock §1c.  
2. ~~**ADR** storage + PKE identity~~ **Done** ADR-013 / ADR-014. Manufacturer / Property dual-write ADRs still future.  
3. **KB-001 IMPL** — three frozen projection edges + queryable read + tests (cite SPECs + ADR-013/014).  
4. **Property Dictionary v0** metrology (Calipers) + FA/EN aliases — dual-write still gated.  
5. **Taxonomy seed** (Proposed seed SPEC) for Measurement — commerce Category unchanged.  
6. **Import playbook tooling** — entity resolution + classification job interfaces wrapping existing scripts.  
7. **KB-001** content graph seed — now implementable without inventing a second merchandising taxonomy.  
8. **Knowledge content modules** on PDP / Brand Hub (honest empty slots until filled).  
9. **Compare / Application hubs** only after UD-04.

---

## 6. Design principles checklist

| # | Principle | Spec coverage |
|---|-----------|---------------|
| 1 | Category expansion without schema changes | Taxonomy + Spec Definition templates |
| 2 | Commerce ≠ Knowledge separation | Entity model §2 |
| 3 | SEO entity foundation | Taxonomy SEO rules + Graph identity + Playbook SEO stage |
| 4 | Thousands of products | Entity identity + resolution |
| 5 | Millions of relationships | Graph cardinality + storage principles |
| 6 | AI-assisted enrichment | Playbook AI allow/deny |
| 7 | Human-controlled accuracy | Review tiers + provenance |
| 8 | Industrial terminology consistency | Taxonomy + Property Dictionary |
| 9 | No uncontrolled free-text as architecture | Spec Definitions; free-text only in content modules |
| 10 | Future PIM/KG compatibility | Overlay model; portable entity/edge vocabulary |
