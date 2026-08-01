---
id: SPEC-knowledge-graph-model
version: 0.1.0
status: Accepted
date: 2026-07-30
governing_parents:
  - docs/architecture/karzar-knowledge-platform-master-architecture.md
  - docs/KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md
  - docs/architecture/specs/SPEC-product-knowledge-entity-model.md
  - docs/architecture/specs/SPEC-industrial-taxonomy-model.md
owner: Knowledge Architect + System Architect
task_id: KB-001
pack: docs/architecture/specs/README.md
---

# SPEC — Knowledge Graph Model

**Status:** **Accepted** (Architecture Board · ۱۴۰۵/۰۵/۱۰ · Mohammad Shebahati · Day-2 minute)  
**Document type:** Knowledge architecture specification  
**Non-goals:** Replacing Postgres commerce SoR with a graph DB for cart/orders · generative RAG · inventing Evidence corpus · schema DDL

---

## 1. Purpose

Define how knowledge entities connect: node types, edge types, identity, cardinality, provenance, and governance — so KarzarTools can support product comparison, applications, standards, related products, and SEO entity architecture at industrial scale.

The Knowledge Graph (KG) is a **logical overlay** on Systems of Record (Phase 2 locked decision). It does **not** become the cart/order system of record (Master Architecture non-goal).

---

## 2. Governing authority

| Source | Statement | Cite |
|--------|-----------|------|
| Master Architecture non-goals | Do not replace Postgres commerce SoR with graph DB as cart SoR | `docs/architecture/karzar-knowledge-platform-master-architecture.md:88-95` |
| Master Architecture §3 | Relation = typed knowledge edge; soft int arrays = transitional debt | `:191` |
| Master Architecture P3–P4 | Identity before intelligence; Evidence before generation | `:115-127` |
| Phase 2 | KG overlay; Entity + Relation engines; engines never write price/stock | `docs/KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md:11-22`, `:69` |
| Phase 2 modules | M1 Entity, M2 Relation, M3 Graph façade | `:77-79` |
| IA | Fact/KG hubs not required for EPIC 1 Wave | `…/karzar-information-architecture.md:20` |
| As-built soft links | `articles.related_product_ids` JSONB | `app/db/models/content.py:43` |
| KB-001 | Link articles↔products↔categories; avoid second taxonomy | `project-management/exports/tasks.json` KB-001 |

---

## 3. Graph principles

| ID | Principle |
|----|-----------|
| **G1** | Every node has a stable identity and a type. |
| **G2** | Every edge has a type, direction, and provenance. |
| **G3** | Commerce facts (price, stock) are **not** graph edges; they remain commerce SoR. |
| **G4** | Soft JSON arrays MAY project into edges; edges are the target SoT for relationships. |
| **G5** | Published claims that imply compliance (standards, certifications, accuracy) REQUIRE Evidence when customer-facing. |
| **G6** | Duplicate nodes are prevented by identity keys per type (§5). |
| **G7** | Graph writes are ingestion-governed (ADR-012 / data-ingestion-policy). |
| **G8** | Traverse for recommend/search boost; never for payment authorization. |
| **G9** | Scale target: thousands of products, **millions** of edges — storage MUST support dense accessory/similar graphs without N+1 public APIs. |
| **G10** | FA/EN labels are attributes/aliases, not duplicate nodes. |

---

## 4. Node types

| Node type | Meaning | Primary SoR / future table | Identity key (logical) |
|-----------|---------|----------------------------|------------------------|
| **Product** | Product Knowledge Entity (linked to commerce SKU) | `products` + PKE projection | `knowledge_entity_id` / provisional `product_id` |
| **Brand** | Marketed brand | `brands` | `brand_id` / `slug` |
| **Manufacturer** | Producing organization | **Missing today** — Proposed entity | `manufacturer_id` / normalized legal name |
| **Category** | Commerce merchandising category | `categories` | `category_id` / `slug` |
| **TaxonomyNode** | Knowledge taxonomy node (any dimension) | Proposed | `node_id` |
| **Application** | Application taxonomy node (specialization of TaxonomyNode) | Proposed | `node_id` |
| **Industry** | Industry taxonomy node | Proposed | `node_id` |
| **Standard** | Normative standard (ISO, DIN, ASME, …) | Proposed | `standard_code` + issuing body |
| **Article** | Editorial CMS article | `articles` | `article_id` / `slug` |
| **Guide** | Structured long-form guide (MAY start as Article subtype) | Proposed / Article | `guide_id` |
| **FAQ** | FAQ item or FAQ set module | Proposed / content module | `faq_id` |
| **Specification** | Specification Definition (Property) **or** Fact node (Style choice — UD-05/ADR) | Proposed | `definition_id` / `fact_id` |
| **Document** | Datasheet, catalog PDF, leaflet | Proposed; as-built `pdf_catalog_url` seed | `document_id` / content hash |
| **Certification** | Formal certification mark/claim | Proposed | `certification_id` |

### 4.1 Specification node style (Proposed default)

**Style A (reified Fact nodes)** — aligned with Master Architecture historical KG intent:

```text
Product --HAS_FACT--> Fact --OF_DEFINITION--> SpecificationDefinition
Fact --SUPPORTED_BY--> Evidence/Document
```

**Style B (property edges)** — simpler, weaker provenance:

```text
Product --HAS_SPEC{value,unit}--> SpecificationDefinition
```

**Default for this SPEC:** Style A for publishable industrial claims; Style B MAY be used only for non-published working drafts. Final storage ADR = UD-05.

---

## 5. Entity identity & duplicate prevention

| Type | Unique business key | Merge rule |
|------|---------------------|------------|
| Product | Active SKU; else Manufacturer+MPN | See Playbook entity resolution |
| Brand | Normalized slug / name | Admin stewardship; no silent merge |
| Manufacturer | Normalized legal name + country | Stewardship |
| Category | `categories.id` | Commerce-owned |
| TaxonomyNode | `dimension` + `slug` | Reject duplicate insert |
| Standard | `body` + `code` + `year?` | Same code different year = version nodes or version attribute (UD) |
| Article | `slug` | CMS-owned |
| Document | checksum + source URL | Same checksum = same Document |

**Alias nodes are forbidden.** Synonyms live on the canonical node (`synonyms[]`).

---

## 6. Edge types

For each edge: name, direction, meaning, cardinality, example.

### 6.1 Product ↔ classification / org

| Name | Direction | Meaning | Cardinality | Example |
|------|-----------|---------|-------------|---------|
| `PRODUCT_BELONGS_TO_CATEGORY` | Product → Category | Commerce merchandising placement | N:1 (as-built product has one category) | SKU 500-196-30 → Category `کولیس` |
| `PRODUCT_CLASSIFIED_AS` | Product → TaxonomyNode | Knowledge facet assignment | N:M (one primary Type + apps/industries) | Product → `digital-caliper` |
| `PRODUCT_MANUFACTURED_BY` | Product → Manufacturer | OEM | N:1 (typical) | Product → Mitutoyo Corporation |
| `PRODUCT_BRANDED_AS` | Product → Brand | Market brand | N:1 (typical) | Product → Mitutoyo |
| `PRODUCT_IN_FAMILY` | Product → TaxonomyNode(family) | Family membership | N:1 primary | Product → Dimensional Measurement / Calipers |

### 6.2 Product ↔ use

| Name | Direction | Meaning | Cardinality | Example |
|------|-----------|---------|-------------|---------|
| `PRODUCT_USED_FOR` | Product → Application | Application fit | N:M | Mitutoyo Caliper → CNC Inspection |
| `PRODUCT_USED_IN` | Product → Industry | Industry context | N:M | Mitutoyo Caliper → Automotive Quality Control |

### 6.3 Product ↔ product

| Name | Direction | Meaning | Cardinality | Example |
|------|-----------|---------|-------------|---------|
| `PRODUCT_COMPATIBLE_WITH` | Product → Product | Accessory / interface compatibility | N:M | Caliper → Depth bar accessory |
| `PRODUCT_SIMILAR_TO` | Product → Product | Same family, overlapping role | N:M undirected logically (store one direction + symmetric flag) | INSIZE 1112 ↔ Mitutoyo 500-196 |
| `PRODUCT_ALTERNATIVE_TO` | Product → Product | Substitute for purchasing decision | N:M | Brand A micrometer ↔ Brand B |
| `PRODUCT_SUCCESSOR_OF` | Product → Product | Lifecycle replacement | N:1 | New model → old model |

Compatibility claims that affect safety **SHOULD** require Evidence before `published`.

### 6.4 Content ↔ product

| Name | Direction | Meaning | Cardinality | Example |
|------|-----------|---------|-------------|---------|
| `ARTICLE_EXPLAINS_PRODUCT` | Article → Product | Editorial explains SKU/PKE | N:M | Guide “How to read a caliper” → Product |
| `GUIDE_COVERS_TAXONOMY` | Guide → TaxonomyNode | Guide scoped to class | N:M | Selection guide → Calipers |
| `FAQ_ABOUT` | FAQ → Product\|TaxonomyNode\|Brand | FAQ subject | N:M | FAQ → Digital Caliper type |

Projection from as-built: `related_product_ids` → candidate `ARTICLE_EXPLAINS_PRODUCT` edges (status=`asserted` until reviewed).

### 6.5 Compliance & documents

| Name | Direction | Meaning | Cardinality | Example |
|------|-----------|---------|-------------|---------|
| `PRODUCT_MEETS_STANDARD` | Product → Standard | Claims conformance | N:M | Product → DIN 862 |
| `PRODUCT_HAS_CERTIFICATION` | Product → Certification | Formal cert | N:M | Product → CE (if applicable) |
| `PRODUCT_HAS_DOCUMENT` | Product → Document | Datasheet/catalog | N:M | Product → Mitutoyo leaflet PDF |
| `FACT_SUPPORTED_BY` | Fact → Document | Evidence for a Fact | N:M | Accuracy Fact → OEM PDF page |

**Publish rule:** `PRODUCT_MEETS_STANDARD` and `PRODUCT_HAS_CERTIFICATION` with `status=published` **MUST** have ≥1 `FACT_SUPPORTED_BY` / document Evidence. Otherwise keep `asserted` for internal use only (Bible P4).

### 6.6 Brand / manufacturer

| Name | Direction | Meaning | Cardinality | Example |
|------|-----------|---------|-------------|---------|
| `BRAND_OWNED_BY` | Brand → Manufacturer | Brand ownership | N:1 typical | Mitutoyo → Mitutoyo Corporation |
| `BRAND_OFFERS_CATEGORY` | Brand → Category\|TaxonomyNode | Coverage (derived OK) | N:M | INSIZE → Measurement |

Derived edges MAY be materialized for query performance but MUST be recomputable.

---

## 7. Edge record shape (logical)

| Field | Required | Description |
|-------|----------|-------------|
| `edge_id` | Yes | Stable |
| `type` | Yes | From §6 enum (extensible registry) |
| `from_node_id` | Yes | |
| `to_node_id` | Yes | |
| `status` | Yes | `asserted` \| `published` \| `rejected` \| `deprecated` |
| `provenance` | Yes | source, actor, timestamp |
| `confidence` | MAY | 0–1 for AI suggestions |
| `attributes` | MAY | e.g. compatibility notes, rank weight |
| `evidence_ids` | MAY | Required for publish on compliance edges |

### 7.1 Extensibility

New edge types **MUST** be added to a versioned **Relation Type Registry** (Git-controlled), with: name, directionality, allowed endpoint types, cardinality, publish Evidence rule, owner.

**MUST NOT** invent free-string edge types in production writes.

---

## 8. Relationship governance

| Action | Who | Gate |
|--------|-----|------|
| Suggest edge (AI/rules) | Pipeline | status=`asserted`, confidence set |
| Publish non-compliance edge | Catalog/Knowledge steward | Review tier Medium (Playbook) |
| Publish compliance edge | Domain expert | Review tier High + Evidence |
| Delete/deprecate edge | Steward | Soft deprecate; keep audit |
| Bulk project from SoR | Versioned job | ADR-012 Category A/B |

Engines **MUST NOT** write `base_price`, stock, or order tables (Phase 2).

---

## 9. Provenance requirements

Minimum provenance on nodes (when knowledge-authored) and **all** edges:

| Field | Example |
|-------|---------|
| `source_kind` | `oem_pdf` \| `supplier_csv` \| `cms` \| `manual` \| `projection` \| `ai_draft` |
| `source_ref` | path/URL/checksum or article id |
| `recorded_at` | ISO timestamp |
| `recorder` | user id or job id |

AODS artifacts `SOURCE-DEPOSIT` / `KNOWLEDGE-EXTRACT` remain the file-level provenance for imports (`aods/40-artifacts/ARTIFACT-ARCHITECTURE.md` §2.4).

---

## 10. Query patterns (architectural, not API contract)

| Pattern | Use |
|---------|-----|
| Neighborhood(Product, depth=1) | PDP related / accessories |
| ProductsBy(Application) | Application hub / filter |
| Alternatives(Product, same Type) | Compare |
| ArticlesExplaining(Product) | PDP knowledge rail |
| StandardsFor(Product) | Compliance module |
| BrandCoverage(Brand) | Brand Hub knowledge face |

Public APIs, when built, SHOULD be additive under `/api/v1/knowledge/*` (Phase 2).

---

## 11. Migration from transitional soft links

| Current | Target edge | Notes |
|---------|-------------|-------|
| `articles.related_product_ids` | `ARTICLE_EXPLAINS_PRODUCT` | Project; keep JSON until cutover criteria |
| Same-category “related” heuristic | `PRODUCT_SIMILAR_TO` candidates | Never auto-publish without rules |
| `optional_accessories` JSON | `PRODUCT_COMPATIBLE_WITH` | Fill historically ≈ 0 |
| `category_id` | `PRODUCT_BELONGS_TO_CATEGORY` | Continuous projection |
| `brand_id` | `PRODUCT_BRANDED_AS` | Continuous projection |

KB-001 implementation **SHOULD** start with projections + Article↔Product↔Category typed edges — **without** creating a second commerce Category DAG (Taxonomy SPEC §1.3).

---

## 12. Requirements (testable)

| ID | Requirement | Criterion |
|----|-------------|-----------|
| **KG-R1** | Overlay, not commerce SoR replacement | Stated in §1 + Phase 2 cite |
| **KG-R2** | Node inventory complete for stated industrial scope | §4 table |
| **KG-R3** | Edge types include required set from mission | §6 includes BELONGS_TO, MANUFACTURED_BY, BRANDED_AS, USED_FOR, COMPATIBLE, SIMILAR, ALTERNATIVE, EXPLAINS, MEETS_STANDARD |
| **KG-R4** | Direction + cardinality + example per edge | §6 tables |
| **KG-R5** | Duplicate prevention keys | §5 |
| **KG-R6** | Provenance on edges | §7–§9 |
| **KG-R7** | Compliance publish requires Evidence | §6.5 |
| **KG-R8** | Extensible via registry not free text | §7.1 |
| **KG-R9** | Soft arrays transitional | §11 |

---

## 13. Open questions

| ID | Question |
|----|----------|
| **KG-Q1** | Store edges in relational tables only vs add graph engine later for traversal? (UD-05) |
| **KG-Q2** | Are Guide/FAQ separate node types or Article subtypes at v1? |
| **KG-Q3** | Symmetric similar edges: store once or twice? |
| **KG-Q4** | Standard year versioning model? |

---

## 14. Cross-document mappings

| Graph action | Upstream / downstream |
|--------------|----------------------|
| Create Product node | Entity SPEC identity |
| `PRODUCT_CLASSIFIED_AS` | Taxonomy SPEC assignment |
| Import creates edges | Playbook stages Entity Resolution → Classification → Enrichment |
| SEO entity pages | Consume Brand/Category/Product nodes; Taxonomy hubs gated |
| AI suggests edges | Playbook AI allow-list; human review tiers |
