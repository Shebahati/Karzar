---
id: SPEC-knowledge-graph-registry
version: 0.1.0
status: Proposed
date: 2026-07-30
governing_parents:
  - docs/architecture/specs/SPEC-knowledge-graph-model.md
  - docs/architecture/specs/SPEC-domain-model.md
owner: Knowledge Graph Architect
task_id: KB-001
---

# SPEC — Knowledge Graph Registry

**Status:** Proposed  
**Purpose:** Official relation vocabulary for KarzarTools knowledge edges  
**Rule:** Production writers MUST only emit types listed here (or later registry versions). Free-string edge types are forbidden.

Parent principles: `SPEC-knowledge-graph-model.md` (overlay, provenance, Evidence before publish for compliance).

---

## 1. Registry record schema

Every relation type declares:

| Field | Meaning |
|-------|---------|
| `name` | SCREAMING_SNAKE type code |
| `direction` | From → To |
| `allowed_from` | Node types |
| `allowed_to` | Node types |
| `cardinality` | Logical cardinality |
| `symmetric` | If true, inverse implied for query |
| `evidence_required_for_publish` | boolean |
| `publish_rules` | Human/AI gates |
| `attributes_allowed` | Optional edge payload keys |
| `example` | Concrete example |
| `status` | `active` \| `draft` \| `deprecated` |

---

## 2. Core relation vocabulary

### 2.1 Identity & org

#### PRODUCT_MANUFACTURED_BY

| Field | Value |
|-------|-------|
| Direction | Product(PKE) → Manufacturer |
| Cardinality | N:1 typical |
| Evidence for publish | No (steward assert OK); Yes if contested OEM claim |
| Publish rules | Medium review if AI-suggested; Low if OEM deposit map |
| Example | Mitutoyo Caliper 500-196-30 → Mitutoyo Corporation |

#### PRODUCT_BRANDED_AS

| Field | Value |
|-------|-------|
| Direction | Product(PKE) → Brand |
| Cardinality | N:1 typical |
| Evidence for publish | No |
| Publish rules | Projection from `products.brand_id` auto-asserted; publish with commerce |
| Example | SKU → Brand Mitutoyo |

#### BRAND_OWNED_BY

| Field | Value |
|-------|-------|
| Direction | Brand → Manufacturer |
| Cardinality | N:1 typical |
| Evidence for publish | Recommended |
| Publish rules | High if private-label ambiguity |
| Example | Brand Mitutoyo → Mitutoyo Corporation |
| Status | active (depends UD-01) |

---

### 2.2 Classification & commerce placement

#### PRODUCT_BELONGS_TO_CATEGORY

| Field | Value |
|-------|-------|
| Direction | Product → Category (commerce) |
| Cardinality | N:1 (as-built) |
| Evidence for publish | No |
| Publish rules | Continuous projection from `category_id` |
| Example | SKU → Category کولیس |

#### PRODUCT_CLASSIFIED_AS

| Field | Value |
|-------|-------|
| Direction | Product → TaxonomyNode |
| Cardinality | N:M (exactly one primary Type SHOULD) |
| Evidence for publish | No for non-compliance nodes |
| Publish rules | Closed label set only; AI → Medium |
| Attributes | `role=primary\|secondary`, `dimension` |
| Example | SKU → `type.caliper.digital` |

#### PRODUCT_IN_FAMILY

| Field | Value |
|-------|-------|
| Direction | Product → TaxonomyNode (family) |
| Cardinality | N:1 primary |
| Evidence for publish | No |
| Publish rules | May be derived from primary Type parent |
| Example | SKU → `fam.calipers` |
| Status | active (derivable) |

---

### 2.3 Use context

#### PRODUCT_USED_FOR

| Field | Value |
|-------|-------|
| Direction | Product → Application (TaxonomyNode) |
| Cardinality | N:M |
| Evidence for publish | No for soft suggestions; Yes for safety-critical use claims |
| Publish rules | Medium for AI; Low for steward map |
| Example | Digital Caliper → CNC Inspection |

#### PRODUCT_USED_IN

| Field | Value |
|-------|-------|
| Direction | Product → Industry |
| Cardinality | N:M |
| Evidence for publish | No typically |
| Publish rules | Medium for AI |
| Example | Caliper → Automotive |

---

### 2.4 Product ↔ product

#### PRODUCT_COMPATIBLE_WITH

| Field | Value |
|-------|-------|
| Direction | Product → Product |
| Cardinality | N:M |
| Symmetric | false (direction = “A works with B”) |
| Evidence for publish | **Yes** when safety/interface critical; else recommended |
| Publish rules | High if safety; Medium otherwise; AI suggest only |
| Attributes | `compatibility_notes`, `interface` |
| Example | Caliper → Depth-bar accessory |

#### PRODUCT_SIMILAR_TO

| Field | Value |
|-------|-------|
| Direction | Product → Product |
| Cardinality | N:M |
| Symmetric | true (store one direction + flag) |
| Evidence for publish | No |
| Publish rules | Auto candidates from same Type; Medium before SEO modules use |
| Attributes | `score`, `reason` |
| Example | INSIZE caliper ↔ Mitutoyo caliper |

#### PRODUCT_ALTERNATIVE_TO

| Field | Value |
|-------|-------|
| Direction | Product → Product |
| Cardinality | N:M |
| Symmetric | true typically |
| Evidence for publish | No |
| Publish rules | Steward/commercial; do not auto-publish solely from similarity score |
| Attributes | `reason` (brand/price/availability — availability not invented) |
| Example | Brand A micrometer ↔ Brand B same range |

#### PRODUCT_SUCCESSOR_OF

| Field | Value |
|-------|-------|
| Direction | Product(new) → Product(old) |
| Cardinality | N:1 |
| Evidence for publish | Recommended (OEM catalog) |
| Publish rules | Medium |
| Example | New Digimatic model → prior SKU |

---

### 2.5 Content

#### ARTICLE_EXPLAINS_PRODUCT

| Field | Value |
|-------|-------|
| Direction | Article → Product |
| Cardinality | N:M |
| Evidence for publish | No |
| Publish rules | Project from `related_product_ids` as asserted; Medium to publish on PDP rail |
| Example | “How to read a caliper” → SKU |

#### GUIDE_COVERS_TAXONOMY

| Field | Value |
|-------|-------|
| Direction | Guide/Article → TaxonomyNode |
| Cardinality | N:M |
| Evidence for publish | No |
| Publish rules | Editorial |
| Status | active |

#### FAQ_ABOUT

| Field | Value |
|-------|-------|
| Direction | FAQ/Module → Product\|TaxonomyNode\|Brand |
| Cardinality | N:M |
| Evidence for publish | No |
| Publish rules | Medium if AI-drafted |
| Status | active |

---

### 2.6 Documents, facts, compliance

#### PRODUCT_HAS_DOCUMENT

| Field | Value |
|-------|-------|
| Direction | Product → Document |
| Cardinality | N:M |
| Evidence for publish | Document **is** the artifact |
| Publish rules | Low if checksummed OEM deposit; Medium if scraped |
| Example | SKU → Mitutoyo leaflet PDF |

#### FACT_SUPPORTED_BY

| Field | Value |
|-------|-------|
| Direction | Spec Fact → Document (or Evidence Source) |
| Cardinality | N:M |
| Evidence for publish | N/A (this edge *is* evidence link) |
| Publish rules | Required before Fact `published` when policy says so |
| Example | accuracy Fact → OEM PDF page ref |

#### PRODUCT_MEETS_STANDARD

| Field | Value |
|-------|-------|
| Direction | Product → Standard |
| Cardinality | N:M |
| Evidence for publish | **Yes — mandatory** |
| Publish rules | High + Evidence; AI MUST NOT publish |
| Example | Caliper → DIN 862 |

#### PRODUCT_HAS_CERTIFICATION

| Field | Value |
|-------|-------|
| Direction | Product → Certification |
| Cardinality | N:M |
| Evidence for publish | **Yes — mandatory** |
| Publish rules | High + Evidence; AI MUST NOT publish |
| Example | Product → manufacturer inspection certificate artifact |

#### PRODUCT_HAS_FACT

| Field | Value |
|-------|-------|
| Direction | Product → Spec Fact |
| Cardinality | 1:N |
| Evidence for publish | Per Fact policy |
| Publish rules | Structural; may be FK rather than edge table |
| Status | active (Style A) |

---

### 2.7 Derived / coverage (optional materialization)

#### BRAND_OFFERS_TAXONOMY

| Field | Value |
|-------|-------|
| Direction | Brand → TaxonomyNode\|Category |
| Cardinality | N:M |
| Evidence for publish | No |
| Publish rules | Derived from product assignments; recomputable |
| Status | active |

---

## 3. Disambiguation rules

| Pair | Rule |
|------|------|
| SIMILAR vs ALTERNATIVE | Similar = engineering neighborhood; Alternative = purchase substitute intent |
| COMPATIBLE vs SIMILAR | Compatible = interface/accessory; not “same kind” |
| BELONGS_TO_CATEGORY vs CLASSIFIED_AS | Commerce placement vs knowledge ontology |
| MEETS_STANDARD vs FACT standard_ref | Prefer Standard node edge for publishable compliance |

---

## 4. Versioning

- Registry version SemVer in this document front-matter / future YAML export.  
- Adding a type: PR + steward; `draft` until active.  
- Removing a type: deprecate; keep edges readable.  
- Changing allowed endpoints: new type version; migrate.

---

## 5. KB-001 minimal slice

First implementable registry subset (projections):

1. `PRODUCT_BELONGS_TO_CATEGORY`  
2. `PRODUCT_BRANDED_AS`  
3. `ARTICLE_EXPLAINS_PRODUCT`  
4. `PRODUCT_CLASSIFIED_AS` (when seed + maps exist)  
5. `PRODUCT_HAS_DOCUMENT` (from `pdf_catalog_url` when present)

---

## 6. Requirements

| ID | Criterion |
|----|-----------|
| **REG-R1** | Each mission example relation defined with direction, endpoints, cardinality, evidence, publish rules, example |
| **REG-R2** | Compliance edges require Evidence to publish |
| **REG-R3** | No free-string types |
| **REG-R4** | Compatible with overlay SoR (Phase 2) |
| **REG-R5** | KB-001 minimal subset identified |

---

## 7. Open questions

| ID | Question |
|----|----------|
| **KG-Q1 / UD-05** | Edge table DDL vs later graph engine |
| **REG-Q1** | Store symmetric SIMILAR once or twice? |
| **REG-Q2** | Edge attributes JSON schema registry? |
