---
id: SPEC-industrial-taxonomy-model
version: 0.1.0
status: Proposed
date: 2026-07-30
governing_parents:
  - docs/architecture/karzar-knowledge-platform-master-architecture.md
  - docs/architecture/information-architecture/karzar-information-architecture.md
  - docs/architecture/adr/ADR-010-seo-url-contract.md
owner: Information Architect + Domain Architect
task_id: KB-001
pack: docs/architecture/specs/README.md
---

# SPEC — Industrial Taxonomy Model

**Status:** Proposed (not binding merge criteria until Architecture Board Accepts)  
**Document type:** Information Architecture / Domain taxonomy specification  
**Non-goals:** Replacing commerce `categories` table · shipping Tool Class hubs in EPIC 1 · unbounded facet indexation · schema DDL

---

## 1. Purpose

Make taxonomy the foundation for:

- Navigation (knowledge + commerce)
- SEO entity hubs (where Authorized)
- Filtering facets (non-hub)
- Knowledge graph classification nodes
- Product classification
- Content architecture (guides by domain/family)

This is **not** a simple ecommerce Category → Subcategory → Product tree. That pattern alone is insufficient for industrial PIM (Grainger, RS, McMaster-Carr, Mitutoyo knowledge ecosystems).

### 1.1 Questions the taxonomy MUST answer

| Question | Dimension |
|----------|-----------|
| What is this? | Domain → Tool Family → Knowledge Category → Type |
| What is it used for? | Application taxonomy |
| Where is it used? | Industry taxonomy |
| How is it specified? | Technical classification + Spec Templates (Entity SPEC) |

### 1.2 Explicit non-design: single merchandising ladder

**Avoid as the sole model:**

```text
Category
  └── Subcategory
        └── Product
```

As-built Karzar already has a merchandising adjacency tree (`categories`, depth discipline). That tree is **necessary for commerce** and **insufficient for knowledge**.

### 1.3 Conflict resolution: “no second taxonomy” (CF-SPEC-01)

`KB-001` acceptance criteria include “avoid second taxonomy” / “No DAG categories”.

**Normative interpretation in this SPEC:**

| Allowed | Forbidden |
|---------|-----------|
| One **commerce merchandising tree** (`categories`) | A second storefront Category DAG competing with `categories` |
| Multiple **knowledge dimensions** (Domain, Family, Application, Industry) as classification facets | Replacing Category hubs with ad-hoc facet URLs as entity homes (ADR-010 §8) |
| Megamenu as presentation over L1 roots (**D1**) | Treating megamenu as ontological taxonomy |

Knowledge taxonomy nodes are **classification & graph nodes**. They become public hub URLs **only** when Board authorizes a URL class (UD-04). Until then they power filters, graph, and content — not parallel `/categories`-class paths.

---

## 2. Governing authority

| Source | Statement | Cite |
|--------|-----------|------|
| Master Architecture §3 | Category ≠ Tool Class; Ontology ≠ megamenu | `docs/architecture/karzar-knowledge-platform-master-architecture.md:181-192` |
| Master Architecture §4 Taxonomy context | Merchandising tree depth ≤ 3 | `:202` |
| IA dual-axis | Knowledge vs Commerce; Tool Class hubs deferred past EPIC 1 | `…/karzar-information-architecture.md:65-80`, `:172` |
| ADR-010 | Category hubs `/categories/{slug}` enhance-in-place; unbounded facets ≠ hubs | `ADR-010-seo-url-contract.md:68-71` |
| PMO D1 | Megamenu is merchandising over L1 — not second taxonomy | `project-management/DECISIONS.md` D1 |
| As-built Category | `parent_id`, `slug`, `spec_template_key`, megamenu flags | `app/db/models/product.py:72-112` |
| Seed tree | Persian industrial roots (toolholding, inserts, end mills, drills, measurement, …) | `scripts/seed_categories.py:40-80` |

---

## 3. Multi-dimensional model

```text
                    ┌──────────────────┐
                    │ Industrial Domain│
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      Tool Family     Application      Industry
              │              │              │
              ▼              ▼              ▼
     Knowledge Category   Use case      Sector
              │
              ▼
        Product Type
              │
              ▼
     Spec Template bind
```

A Product Knowledge Entity receives **one primary path** on the Domain/Family/Category/Type ladder, plus **0..N** Application and Industry nodes.

### 3.1 Dimension 1 — Domain taxonomy

**Purpose:** Top-level industrial knowledge pillars (stable, few).

Example (illustrative; not a freeze of catalog):

```text
Industrial Tools
├── Measuring Tools          (Measurement / Metrology)
├── Cutting Tools
├── Workholding / Toolholding
├── Power Tools
├── Welding Tools            (future)
├── Safety Equipment         (future)
├── Electrical Tools         (future)
├── Automation Equipment     (future)
└── Lubrication Systems      (future)
```

**As-built bridge:** Current L1 commerce roots in `seed_categories.py` (ابزارگیر، اینسرت، انگشتی، مته، …، اندازه‌گیری) **map into** Domains; they are not required to equal Domain 1:1.

Rules:

- Domain count SHOULD stay small (≈5–15).
- New domain = new node + stewardship owner + Spec Template plan — **not** DDL.
- Metrology MAY be flagship knowledge domain without erasing others (IA principle 6).

### 3.2 Dimension 2 — Product family taxonomy

**Purpose:** Ontological “what kind of tool” hierarchy under a Domain.

Example:

```text
Measurement Tools
└── Dimensional Measurement
    ├── Calipers
    │   ├── Vernier Caliper
    │   ├── Dial Caliper
    │   └── Digital Caliper
    ├── Micrometers
    ├── Height Gauges
    ├── Dial Indicators
    └── Gauge Blocks
```

This dimension owns **Tool Class / Product Type** meaning (Bible “Tool Class”).

### 3.3 Dimension 3 — Application taxonomy

**Purpose:** “What is it used for?”

Example:

```text
Application
├── Quality Control
├── Incoming Inspection
├── CNC In-Process Inspection
├── Workshop Measurement
├── Calibration Lab
├── Welding Fabrication          (future)
└── Predictive Maintenance       (future)
```

Applications are **cross-cutting**: the same Digital Caliper may link to Quality Control **and** Workshop Measurement.

### 3.4 Dimension 4 — Industry taxonomy

**Purpose:** “Where is it used?”

Example:

```text
Industries
├── Automotive
├── Aerospace
├── Steel / Metals
├── Oil & Gas
├── Machine Manufacturing
├── Medical Device
└── Education / Training
```

Industry nodes are optional on PKE; valuable for SEO landing strategy and B2B discovery — **indexable hub** status is Board-gated (UD-04).

### 3.5 Dimension 5 — Technical classification

**Purpose:** Filterable engineering classes that are not always a family leaf.

Examples:

- Accuracy class / grade
- Measurement principle (contact / non-contact)
- Power source (manual / battery / pneumatic / electric)
- Material system (HSS / carbide / ceramic)
- Mounting interface (BT40, HSK-A63, VDI…)

Technical classification nodes **MAY** bind to Specification Definitions (enums) rather than free-text facets.

---

## 4. Taxonomy node model

### 4.1 Node attributes

| Attribute | Required | Description |
|-----------|----------|-------------|
| `node_id` | Yes | Stable opaque ID |
| `dimension` | Yes | `domain` \| `family` \| `application` \| `industry` \| `technical` \| `commerce_category` |
| `node_type` | Yes | Fine type within dimension (see §4.2) |
| `slug` | Yes | URL-safe unique **within dimension** (global unique if public hub) |
| `name_fa` | Yes | Persian display name |
| `name_en` | SHOULD | English name for PIM / OEM alignment |
| `parent_id` | Dimension-dependent | Single parent within dimension tree |
| `status` | Yes | `draft` \| `active` \| `deprecated` |
| `synonyms` | MAY | FA/EN aliases for search/resolution |
| `seo_meta_title` | MAY | Only if hub-eligible |
| `seo_meta_description` | MAY | Only if hub-eligible |
| `spec_template_id` | MAY | Bind to Specification Template |
| `commerce_category_id` | MAY | Bridge to as-built Category when 1:1 |
| `sort_order` | MAY | Nav ordering |
| `steward` | SHOULD | Human owner role |

### 4.2 Node types

| node_type | Dimension | Parent rules |
|-----------|-----------|--------------|
| `industrial_domain` | domain | parent null or root `industrial_tools` |
| `tool_family` | family | parent domain **or** broader family |
| `knowledge_category` | family | parent tool_family |
| `product_subcategory` | family | parent knowledge_category |
| `product_type` | family | parent subcategory or knowledge_category |
| `application` | application | tree or flat under application root |
| `industry` | industry | tree or flat under industry root |
| `technical_class` | technical | parent technical root or group |
| `commerce_category` | commerce_category | Existing `categories` projection — **not** duplicated as editable second tree |

### 4.3 Parent–child rules

1. **Intra-dimension trees only** for structural parent_id (Domain tree, Family tree, …).
2. **No multi-parent within the same dimension** (avoids DAG categories in the KB-001 sense).
3. **Cross-dimension links** are graph edges / assignments on PKE — not parent_id.
4. Maximum recommended depth for family dimension: **4–5** (Domain bridge → Family → Category → Sub → Type). Commerce Category depth remains ≤ 3 as today.
5. Deprecated nodes remain for redirects/history; new assignments MUST NOT use them.

### 4.4 Multiple inheritance

**Structural inheritance (parent_id):** single parent only.

**Classification inheritance (PKE assignments):** a product **MAY** hold multiple Application and Industry nodes; **MUST** hold exactly one primary Domain and one primary Product Type (when classified).

Optional secondary Domain is allowed for hybrid tools (e.g. welding gauge spanning Measurement + Welding) with stewardship review.

---

## 5. Slug strategy

| Rule | Detail |
|------|--------|
| ASCII kebab-case | AODS N-01/N-02 |
| Unique within dimension | `family:digital-caliper` vs future collisions |
| Globally unique if public hub | Required before any indexable URL ships |
| Stable | Renames use redirect matrix (RFC-004 spirit); do not reuse slugs |
| Commerce Category slugs | Remain owned by `categories.slug` (as-built unique) |
| Knowledge vs commerce | Prefer distinct slug namespaces when both public (e.g. `/learn/...` or `/applications/{slug}` — **URL class TBD UD-04**) |

**MUST NOT** mint unbounded faceted slugs (`/catalog?a=&b=&c=`) as taxonomy hubs (ADR-010 Decision 8).

---

## 6. SEO usage

### 6.1 Hub-eligible vs filter-only

| Node class | Default SEO role | Indexable hub? |
|------------|------------------|----------------|
| Commerce Category | `/categories/{slug}` | **Yes** (CURRENT + TARGET enhance-in-place) |
| Brand | `/brands/{slug}` | **Yes** (ADR-010 / RFC-005) |
| Domain / Tool Family / Product Type | Knowledge classification | **No by default** until UD-04 |
| Application / Industry | Knowledge + future hubs | **No by default** until UD-04 |
| Technical class | Facet / compare | **Never** as unbounded combinations |

### 6.2 Category page generation rules (commerce)

When generating/enhancing Category Hub pages:

1. Use commerce Category entity as authority URL.
2. MAY inject knowledge intro modules mapped from linked Domain/Family.
3. MUST keep crumbs aligned to canonical URLs (ADR-010 Decision 6).
4. MUST NOT invent Tool Class as a Category slug.
5. Spec filters SHOULD use Specification Definitions bound via `spec_template_key` → Template ID strangler.

### 6.3 Future knowledge hub generation rules (Proposed)

If Board authorizes Application hubs:

1. One Application node → one URL class.
2. Page MUST list PKEs linked `USED_FOR` with honest empty state.
3. MUST include path to commerce inquiry/buy (IA dual-axis anti-pattern avoidance).
4. Thin-content policy MUST be Board-frozen before indexation (pattern: Brand Hub D21).

---

## 7. Assignment to products

| Assignment | Cardinality | Required for knowledge-published? |
|------------|-------------|-----------------------------------|
| Commerce Category | exactly 1 (as-built NOT NULL) | Yes (commerce) |
| Primary Domain | 1 | Yes |
| Primary Tool Family | 1 | Yes |
| Primary Product Type | 1 | SHOULD |
| Applications | 0..N | MAY |
| Industries | 0..N | MAY |
| Technical classes | 0..N | MAY |

Import pipeline **MUST** assign commerce Category before production write (as-built constraint) and **SHOULD** assign Domain/Family in the same job when rules exist (Playbook Classification stage).

---

## 8. Expansion without redesign

### 8.1 Adding a new industrial domain (procedure)

1. Create Domain node (`status=draft`) with FA/EN names + steward.
2. Add Family/Category/Type subtree as needed.
3. Create Specification Templates for families that need compare/filter.
4. Add classification rules to import playbooks (keyword/OEM map).
5. Optionally map existing commerce Categories → new Domain bridge.
6. Activate nodes; enqueue enrichment tasks for affected SKUs.
7. SEO hub decision is **separate** (UD-04).

### 8.2 What MUST NOT change

- PKE identity attribute schema
- Commerce order/cart model
- ADR-010 URL classes (unless new RFC)
- Requirement for Evidence on standards/cert Facts

---

## 9. Navigation roles

| UI surface | Taxonomy source |
|------------|-----------------|
| Megamenu | Commerce L1 + `MegamenuNavGroup` (presentation) |
| Category Hub | Commerce Category |
| Catalog facets | Spec Definitions + optional Application/Industry filters (non-indexable combinations) |
| Guides / Learning | Domain + Application grouping |
| Brand Hub | Brand; MAY show Domain coverage chips from graph |
| Admin classification | Full multi-dimension editor |

---

## 10. Requirements (testable)

| ID | Requirement | Criterion |
|----|-------------|-----------|
| **TX-R1** | Multi-dimensional | ≥ Domain, Family, Application, Industry defined |
| **TX-R2** | Not sole Category→Product ladder | §1.2 explicit |
| **TX-R3** | No second commerce Category DAG | §1.3; commerce_category is projection |
| **TX-R4** | Single parent within dimension | §4.3 |
| **TX-R5** | Expansion via nodes/templates | §8 |
| **TX-R6** | Slug stability rules | §5 |
| **TX-R7** | Facets ≠ hubs | §6.1 + ADR-010 cite |
| **TX-R8** | Bridge to as-built Category | `commerce_category_id` / mapping allowed |
| **TX-R9** | Answers what / used for / where | §1.1 |

---

## 11. Open questions

| ID | Question |
|----|----------|
| **TX-Q1** | Exact Domain list for Wave-2 seed (metrology-first vs full L1 map)? |
| **TX-Q2** | URL namespace for future Application hubs? |
| **TX-Q3** | Should commerce Category rename follow knowledge Type names or stay merchandising-Persian as today? |
| **UD-04** | Pack-level Board gate for indexable knowledge hubs |

---

## 12. Cross-document mappings

| Taxonomy event | Downstream |
|----------------|------------|
| Node created | Appears as KG `TaxonomyNode` |
| PKE assigned Type | Edge `PRODUCT_CLASSIFIED_AS` |
| Template bound to Family | Entity SPEC technical model |
| Import classification | Playbook Classification stage writes assignments |
| Category Hub render | Commerce Category + optional knowledge intro from Domain/Family |
