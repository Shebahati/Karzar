---
id: SPEC-product-knowledge-entity-model
version: 0.1.0
status: Accepted
date: 2026-07-30
governing_parents:
  - docs/architecture/karzar-knowledge-platform-master-architecture.md
  - docs/architecture/CANON-LOCK.md
  - docs/architecture/information-architecture/karzar-information-architecture.md
owner: PIM Architect + Domain Architect
task_id: KB-001
pack: docs/architecture/specs/README.md
---

# SPEC — Product Knowledge Entity Model

**Status:** **Accepted** (Architecture Board · ۱۴۰۵/۰۵/۱۰ · Mohammad Shebahati · Day-2 minute)  
**Document type:** Domain / PIM specification  
**Non-goals:** Schema DDL · migrations · API implementation · Canon Lock self-Accept · inventing missing ADR-001…009 text

---

## 1. Purpose

Define what a **product** means inside KarzarTools when the platform evolves from a commerce catalog into an industrial knowledge platform.

This specification **MUST** keep two concepts separate:

| Concept | Job | System of record (target) |
|---------|-----|---------------------------|
| **Commerce Product** | Sell / inquire / fulfill a SKU offer | Existing `products` (+ price, availability, cart/order) |
| **Product Knowledge Entity (PKE)** | Meaning, classification, technical understanding, applications, relationships, education | Knowledge overlay linked 1:1 or 1:N to commerce SKUs |

Merging them into one “god Product JSON” is an anti-pattern (Master Architecture P7).

---

## 2. Governing authority (cite, do not invent)

| Source | Binding / orientation statement | Cite |
|--------|--------------------------------|------|
| Master Architecture P7 | Commerce, PIM/specs, taxonomy, knowledge are separate contexts | `docs/architecture/karzar-knowledge-platform-master-architecture.md:143-148` |
| Master Architecture §3 | Product = commercial SKU offer; Series/Family largely missing; Tool Class ≠ Category | same file `:179-192` |
| Master Architecture P3 | Identity before intelligence | `:115-120` |
| Master Architecture P5–P6 | FA/EN mapping before Facts dual-write; JSONB operational until approved migration | `:129-141` |
| Master Architecture P4 | Evidence before generation | `:122-127` |
| IA dual-axis | Knowledge Axis vs Commerce Axis share entity identity | `docs/architecture/information-architecture/karzar-information-architecture.md:65-95` |
| ADR-010 | Public identity URLs; no Facts required for EPIC 1 | `docs/architecture/adr/ADR-010-seo-url-contract.md:63-71` |
| Phase 2 | KG overlay on SoR; engines must not write commerce price/stock | `docs/KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md:11-22`, `:69` |
| As-built Product | SKU, slug, category_id, brand_id, prices, JSONB specs, descriptions | `app/db/models/product.py:130-204` |
| As-built Brand | Single brand table; no Manufacturer | `app/db/models/product.py:115-127` |

---

## 3. Separation contract

### 3.1 Commerce Product (preserve)

Fields and concerns that **remain commerce-owned** (illustrative mapping to as-built):

| Concern | As-built field / system | Knowledge layer MAY |
|---------|-------------------------|---------------------|
| Offer identity | `products.id`, `sku`, `slug` | Link via foreign key / projection |
| Merchandising placement | `category_id` | Also assign knowledge taxonomy nodes (orthogonal) |
| Brand facet (today) | `brand_id` | Resolve to Brand **and** Manufacturer when split (UD-01) |
| Price / tax | `base_price`, `original_price`, `tax_percent` | **MUST NOT** store or invent |
| Availability | `is_available`, Hesabfa stock | Display only; not ontological |
| Media commerce | `product_images`, `pdf_catalog_url` | Treat PDF URL as candidate Evidence Source |
| Marketing blobs (transitional) | `short_description`, `description` | Migrate toward Knowledge Content Modules |
| Specs (transitional) | `specifications` JSONB | Project into Facts when dictionary exists |

### 3.2 Product Knowledge Entity (new meaning)

A PKE answers:

- **What is this artifact industrially?** (type, family, class)
- **Who makes / brands it?** (manufacturer ≠ brand)
- **How is it identified across suppliers?** (model, series, MPN)
- **What are its governed technical facts?**
- **How do engineers learn and apply it?**
- **What else is related?** (accessories, alternatives, standards, applications)

### 3.3 Cardinality

| Pattern | Meaning | Example |
|---------|---------|---------|
| 1 PKE : 1 Commerce Product | Default for sellable SKU | Mitutoyo 500-196-30 single offer |
| 1 PKE : N Commerce Products | Same knowledge identity, multiple commercial SKUs (pack sizes, warehouse variants) | Same model, different sell units — **requires Board policy before use** |
| N PKE : 1 Commerce Product | Forbidden | Would break offer identity |

Until UD-02 is decided, **implementation SHOULD treat `products.id` as the provisional link key** and introduce a stable `knowledge_entity_id` only via Accepted ADR.

---

## 4. Identity model

### 4.1 Identity attributes

| Attribute | Required | Definition | Notes |
|-----------|----------|------------|-------|
| **Product Entity ID** | Yes | Stable knowledge identity | Opaque; never reuse (AODS N-05 spirit) |
| **Manufacturer** | Yes (when known) | Legal/producing organization | e.g. Mitutoyo Corporation |
| **Brand** | Yes (when known) | Marketed brand label | e.g. Mitutoyo; MAY equal manufacturer name but MUST remain separately typed |
| **Model Number** | SHOULD | Manufacturer model / designation | e.g. CD-6″ ASX |
| **SKU** | Yes for commerce link | Karzar sellable stock-keeping unit | As-built unique among active (`uq_products_sku_active`) |
| **MPN** | SHOULD | Manufacturer part number when distinct from model | Often equals SKU for OEM catalogs |
| **Product Family** | SHOULD | Manufacturer family grouping | e.g. Digimatic Calipers |
| **Product Series** | MAY | Series within family | e.g. 500 Series |
| **Product Type** | SHOULD | Ontological type (Tool Class leaf) | e.g. Digital Caliper — **not** Category slug |
| **Product Variant** | MAY | Differentiator within model | Range, jaw length, IP rating, package |
| **Lifecycle Status** | Yes | Knowledge lifecycle | See §4.3 |

### 4.2 Manufacturer ≠ Brand (normative)

```text
Manufacturer: Mitutoyo Corporation
Brand:        Mitutoyo
SKU:          500-196-30
Model:        CD-6″ ASX
```

Rules:

1. A Commerce Product **MAY** have Brand without Manufacturer during migration (as-built today).
2. Knowledge Facts that cite OEM authority **SHOULD** resolve Manufacturer.
3. Private-label / rebrand cases: Manufacturer = OEM, Brand = Karzar or distributor brand — both edges required when known.
4. **MUST NOT** assume `brands.name` is the manufacturer legal name without stewardship review (UD-01).

### 4.3 Lifecycle status

| Status | Meaning | Storefront implication |
|--------|---------|------------------------|
| `draft` | Identity incomplete | Not knowledge-published |
| `active` | Current offer + knowledge | Normal |
| `superseded` | Replaced by another entity | Link to successor; commerce may deactivate |
| `discontinued` | No longer made; may remain knowledge | Commerce `is_active` may be false |
| `unknown` | Imported without lifecycle signal | Requires enrichment |

Commerce `is_active` / `deleted_at` remain commerce flags and **MUST NOT** be overloaded as knowledge lifecycle.

### 4.4 Identity matching keys (for resolution)

Ordered preference for “same product?” (full rules in Import Playbook):

1. Active SKU exact match (commerce unique)
2. Manufacturer + MPN / Model normalized match
3. Brand + Model normalized match (weaker; collision risk)
4. Similarity candidate → human review (never auto-merge)

---

## 5. Classification model (knowledge)

Classification is **independent of URL paths** and **independent of commerce Category tree depth**.

Commerce Category answers: “Where do we merchandise this for browsing?”  
Knowledge classification answers: “What is it industrially?”

### 5.1 Classification facets (assigned to PKE)

| Facet | Multiplicity | Example |
|-------|--------------|---------|
| Industrial Domain | 1 primary; MAY add secondary | Measurement |
| Industry | 0..N | Automotive, Aerospace |
| Tool Family | 1 primary | Dimensional Measurement |
| Product Category (knowledge) | 1 primary | Caliper |
| Product Subcategory | 0..1 | Digital Caliper |
| Product Type / Tool Class | 1 | Absolute Digimatic Caliper |
| Application Class | 0..N | CNC Inspection, Incoming QC |

Detailed node types, inheritance, and SEO rules: [`SPEC-industrial-taxonomy-model.md`](./SPEC-industrial-taxonomy-model.md).

### 5.2 Expansion rule

Adding Welding, Safety, Electrical, Automation, Lubrication **MUST** be possible by:

1. Adding taxonomy nodes + labels (FA/EN)
2. Adding Specification Definition templates for new families
3. Optionally adding content module templates

**MUST NOT** require redesign of PKE identity attributes or commerce Product table shape.

### 5.3 Relationship to as-built Category

| As-built | Role after this SPEC |
|----------|----------------------|
| `categories` tree | Commerce merchandising placement (preserve) |
| `spec_template_key` | Transitional hint toward Specification Template ID |
| Megamenu groups | Presentation only (**D1**) |

A PKE **MUST** keep a commerce Category assignment while knowledge facets are incomplete (strangler). Knowledge facets **MUST NOT** delete or fork the merchandising tree (CF-SPEC-01).

---

## 6. Technical knowledge model (governed specifications)

### 6.1 Reject uncontrolled JSON as final architecture

As-built `get_default_specifications()` hard-codes measurement-shaped keys (`range`, `accuracy`, `resolution`, …) into every product (`app/db/models/product.py:49-68`). That is operational transitional storage (Bible P6), **not** the target architecture.

Target: **Property Dictionary + Facts** (orientation in Master Architecture §3).

### 6.2 Core constructs

| Construct | Definition |
|-----------|------------|
| **Specification Definition (Property)** | Governed attribute: ID, canonical key, FA label, EN label, data type, unit dimension, validation, applicability |
| **Specification Template** | Ordered set of Definitions applicable to a Product Family / Tool Class |
| **Specification Value (Fact)** | Assertion: Entity × Definition → value (+ unit, qualifier, status, provenance) |
| **Unit** | Canonical unit code within a dimension (length: `mm`, `in`; resolution: `mm`, `µm`) |
| **Data Type** | `number`, `integer`, `boolean`, `enum`, `string`, `range`, `quantity` |
| **Validation Rule** | Type checks, enum membership, min/max, unit compatibility, regex for codes |

### 6.3 Example — Caliper template (illustrative)

| Definition key | FA label | Type | Unit | Example value |
|----------------|----------|------|------|---------------|
| `measurement_range` | بازه اندازه‌گیری | range | mm | 0–150 |
| `resolution` | تفکیک‌پذیری | number | mm | 0.01 |
| `accuracy` | دقت | quantity | mm | ±0.02 |
| `display_type` | نوع نمایش | enum | — | digital |
| `data_output` | خروجی داده | boolean | — | true |
| `protection_rating` | درجه حفاظت | enum | — | IP67 |

### 6.4 Example — Micrometer template (different attributes)

| Definition key | Notes |
|----------------|-------|
| `measurement_range` | Shared definition ID with calipers |
| `resolution` | Shared |
| `accuracy` | Shared |
| `spindle_type` | Micrometer-specific |
| `anvil_type` | Micrometer-specific |
| `flatness` | Micrometer-specific |

**Shared Definitions across families** are required for comparison and FA/EN collapse (Bible P5).

### 6.5 Fact status & provenance

| Fact status | Meaning |
|-------------|---------|
| `asserted` | Entered from trusted source, not yet published |
| `published` | Approved for customer-facing use |
| `disputed` | Conflict between sources |
| `deprecated` | Superseded value retained for audit |

Every Fact **MUST** carry: `source_id` (or source ref), `captured_at`, `capturing_agent` (human|pipeline|ai), `confidence` (optional), `evidence_ref` (optional).

AI **MUST NOT** invent Fact values (Playbook). Empty is honest.

### 6.6 JSONB strangler

Until dual-write is Board-enabled:

1. JSONB remains readable SoT for storefront/admin.
2. Dictionary mapping tables MAY exist offline / in Git (`MAPPING-TABLE` artifact per AODS).
3. No production dual-write without Accepted Property governance ADR/RFC (Canon Lock §3).

---

## 7. Knowledge content model

Do **NOT** store all education in one `description` field.

### 7.1 Content module types

| Module type | Purpose | Typical audience |
|-------------|---------|------------------|
| `overview` | What the product is | Buyer + engineer |
| `how_it_works` | Operating principle | Engineer |
| `how_to_use` | Procedure / best practice | Technician |
| `selection_guide` | Choose among variants/family | Buyer |
| `common_mistakes` | Failure modes / misuse | Technician |
| `maintenance` | Care, calibration intervals | Maintenance |
| `applications` | Narrative use cases (links Application nodes) | Engineer |
| `faq` | Q&A pairs | All |
| `buying_guide` | Commercial selection (not price invention) | Buyer |
| `comparison` | Structured compare vs siblings | Buyer |

### 7.2 Module entity shape (logical)

| Field | Rule |
|-------|------|
| `module_id` | Stable |
| `entity_id` | PKE (or Family-level module) |
| `type` | From §7.1 enum |
| `locale` | `fa` primary; `en` optional |
| `title` | Required |
| `body` | Structured blocks (reuse Article block spirit) — not untyped blob forever |
| `status` | draft / review / published |
| `provenance` | Author, source, timestamps |

### 7.3 Relationship to CMS Article

| Artifact | Role |
|----------|------|
| **Article** (`articles`) | Site-level editorial Expression; Learning/Guides gravity (IA) |
| **Content Module** | Entity-scoped knowledge attached to PKE / Family / Brand |

Article **MAY** explain a PKE via graph edge `ARTICLE_EXPLAINS_PRODUCT`. Modules **MUST NOT** replace Evidence Documents.

### 7.4 Honest empty slots

IA requires Document and Accessory slots even when empty (`karzar-information-architecture.md` principle 7). Same rule for knowledge modules: UI MAY reserve slots; content MUST NOT be fabricated to fill them.

---

## 8. Relationship model (vocabulary)

Full graph semantics: [`SPEC-knowledge-graph-model.md`](./SPEC-knowledge-graph-model.md).

Minimum relationship types owned at entity level:

| Relationship | From → To | Meaning |
|--------------|-----------|---------|
| Compatible accessory | Product → Product | Works with / attaches to |
| Alternative | Product → Product | Different brand/model, same job |
| Similar | Product → Product | Same family, overlapping specs |
| Successor | Product → Product | Lifecycle replacement |
| Explained by | Product → Article/Guide | Editorial explanation |
| Branded as | Product → Brand | Market identity |
| Manufactured by | Product → Manufacturer | OEM |
| Meets standard | Product → Standard | Compliance claim (Evidence required for publish) |
| Used for | Product → Application | Application class |
| Used in | Product → Industry | Industry context |
| Belongs to category | Product → Category (commerce) | Merchandising |
| Classified as | Product → Taxonomy Node | Knowledge facets |
| Has specification | Product → Fact → Definition | Technical knowledge |
| Has document | Product → Document | Datasheet/catalog Evidence candidate |
| Has certification | Product → Certification | Formal cert (Evidence required) |

As-built transitional debt:

- `articles.related_product_ids` JSONB — soft, untyped (`app/db/models/content.py:43`)
- `optional_accessories` inside JSONB — fill ≈ 0 historically

These **SHOULD** project into typed edges; they **MUST NOT** remain the long-term architecture.

---

## 9. SEO entity foundation (identity face)

| Surface | Uses |
|---------|------|
| PDP `/product/{slug}` | Commerce Product slug; knowledge modules enhance PDP |
| Brand Hub `/brands/{slug}` | Brand entity |
| Category Hub `/categories/{slug}` | Commerce Category |
| Future Tool Class / Application hubs | Taxonomy nodes — only if Board allows indexable hubs (UD-04) |

Knowledge Entity ID is **not** a public URL segment by default. Public identity remains slug per ADR-010.

---

## 10. Requirements (testable)

| ID | Requirement | Criterion |
|----|-------------|-----------|
| **PKE-R1** | Commerce and Knowledge MUST be separable models | Spec text defines distinct attribute sets; no requirement that price live on PKE |
| **PKE-R2** | Manufacturer ≠ Brand | Model defines both; example Mitutoyo Corporation vs Mitutoyo |
| **PKE-R3** | Classification independent of URL | Facets defined without path templates |
| **PKE-R4** | Specs governed by Definitions | Templates per family; shared Definition IDs across families |
| **PKE-R5** | Content not single description | ≥ module types in §7.1 enumerated |
| **PKE-R6** | Relationships typed | Vocabulary in §8; soft arrays marked transitional |
| **PKE-R7** | Expansion without schema redesign | §5.2 explicit |
| **PKE-R8** | No AI-invented Facts | Defers to Playbook; provenance mandatory for published Facts |
| **PKE-R9** | JSONB strangler honored | No mandate to drop JSONB in this SPEC |
| **PKE-R10** | Aligns CF-SPEC-01 | Does not replace commerce Category tree |

---

## 11. Open questions

See pack README **UD-01**, **UD-02**, **UD-03**. Additional:

| ID | Question |
|----|----------|
| **PKE-Q1** | Are pack-size SKUs variants of one PKE or separate PKEs? |
| **PKE-Q2** | Is Karzar private-label Brand allowed as Brand with external Manufacturer? |
| **PKE-Q3** | Minimum Fact set before a PKE may be `knowledge-published`? |

---

## 12. Cross-document mappings

| When… | Then… |
|-------|-------|
| PKE created | Assign taxonomy nodes (Taxonomy SPEC) |
| PKE linked to Brand/Manufacturer/Category | Emit graph edges (KG SPEC) |
| Import arrives | Resolve identity before enriching Facts (Playbook) |
| Spec template needed for new family | Add Definitions + Template; do not alter PKE identity schema |
