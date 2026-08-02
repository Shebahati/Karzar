---
id: SPEC-canonical-product-type-model
version: 0.1.1
status: Proposed
date: 2026-08-02
governing_parents:
  - docs/architecture/karzar-knowledge-platform-master-architecture.md
  - docs/architecture/adr/ADR-013-knowledge-edge-fact-storage.md
  - docs/architecture/adr/ADR-014-product-knowledge-entity-identity.md
  - docs/architecture/adr/ADR-015-product-type-engineering-classification.md
  - docs/architecture/specs/SPEC-master-knowledge-base-remediation.md
  - docs/architecture/specs/SPEC-product-knowledge-entity-model.md
  - docs/architecture/specs/SPEC-property-dictionary-system.md
  - docs/architecture/specs/SPEC-industrial-taxonomy-model.md
  - docs/architecture/CANON-LOCK.md
owner: Platform Architect + Knowledge Architect (author) · Owner implementation direction recorded 2026-08-02 · Final owner-review corrections KB-PT-00A
task_id: KB-PT-00A
pack: docs/architecture/specs/README.md
amends: KB-PT-00 (v0.1.0)
architecture_board_acceptance: not_granted
canonical_authority: not_accepted_canon
owner_implementation_direction: recorded
kb_pt_01_governance_block: mandatory_board_clarification_required
---

# SPEC — Canonical Product Type Model

**Status:** **Proposed** — owner implementation direction recorded; Architecture Board acceptance **not** granted  
**Document type:** Architecture / governance / sequencing contract (Plane B)  
**Authority:** This document does **not** claim Architecture Board acceptance and is **not** Accepted Canon. AODS registry classification MUST remain **PROPOSED**; `on_main` remains **false** until merged.  
**Non-goals of this SPEC file:** Database models · Alembic · runtime backend/frontend/tests · seeding Product Types · assigning products · migrating specifications · JSONB↔Facts dual-write · Board Accept claim.

---

## 1. Purpose and terminology

### 1.1 Purpose

Establish the **authoritative proposed architecture contract** for introducing **Product Type** as the **engineering-classification source of truth** in Karzar.

This contract governs later Product Type implementation prompts (`KB-PT-01` onward) and amends Master KB remediation sequencing so Property Dictionary / Facts work does not proceed under a Category-as-type architecture.

### 1.2 Explicit non-identity statements

| Statement | Norm |
|-----------|------|
| Product Type is **not** Category | Commerce navigation ≠ engineering class |
| Product Type is **not** SKU | SKU remains commerce offer identity |
| Product Type is **not** Brand | Brand/manufacturer remain orthogonal facets |
| Product Type is **not** Product identity | `products.id` remains Wave-1 PKE identity (ADR-014) |
| Product Type is **not** merely Digital/Dial/Vernier | Readout is an orthogonal profile |
| Product Type is **not** an arbitrary SEO landing page | SEO may consume labels; must not own engineering identity |

### 1.3 Terminology (normative)

| Term | Definition |
|------|------------|
| **Commerce Category** | Merchandising/navigation node in the existing `categories` tree. Owns browse placement, storefront grouping, and commercial landing structure. |
| **Engineering Domain** | Broad engineering knowledge area (e.g. **Dimensional Metrology**). Not a storefront Category. |
| **Tool Family** | Mid-level engineering grouping within a Domain (e.g. **Sliding Measuring Instruments**). Distinct from Product Family. |
| **Product Family** | Governed engineering family used for seed planning (e.g. **Calipers**). Initial families are governed candidate seeds, not an exhaustive universal taxonomy. |
| **Product Type** | First-class engineering classification entity expressing **engineering function**, **measurement purpose**, and **fundamental measurement geometry**, with materially distinct applicability/validation requirements (e.g. **General-purpose Caliper**). |
| **Product Type Definition** | Versioned specification of attribute membership, requiredness, type-specific validation, and profile defaults for one Product Type. |
| **Product Type Assignment** | Binding of one Product to one primary Product Type (Wave 1), including explicit unassigned/ambiguous states. |
| **Attribute / Property Definition** | Canonical property in the Attribute Registry / Property Dictionary (code, datatype, dimension, units, generic validation). |
| **Attribute Membership** | Product-Type-Definition-scoped membership of a Property Definition with requiredness and type-specific overrides. Does **not** duplicate the canonical property definition. |
| **Profile** | Bounded, named dimension of Product Type or Product (readout, geometry, protection, connectivity, construction, presentation, search/filter, comparison, knowledge, SEO). Profiles are referenced; Product Type MUST NOT become a God Object owning all mutable concerns. |
| **Capability** | Boolean or enumerated ability of a product instance (e.g. wireless, data output) typically modeled as attributes or profile fields, not as separate Product Types. |
| **Product Fact** | Governed, evidenced value of a Property Definition on a Product Knowledge Entity (future runtime; ADR-013). |
| **Legacy JSONB Specification** | Current `products.specifications` JSONB operational store (as-built). Remains in place until a separately approved migration/cutover task. |
| **Evidence** | Source artifacts, locators, provenance links, and verification records supporting Facts or critical metrology claims. |
| **Product Knowledge Entity (PKE)** | Knowledge meaning of a sellable SKU; Wave-1 join key = `products.id` (ADR-014). Product Type **classifies** a Product; it does **not** replace Product identity. |

### 1.4 Non-duplicative hierarchy example (normative illustration)

| Level | Example |
|-------|---------|
| Engineering Domain | Dimensional Metrology |
| Tool Family | Sliding Measuring Instruments |
| Product Family | Calipers |
| Product Type | General-purpose Caliper |

**Norm:** Tool Family and Product Family are **distinct** governed levels. They **MUST NOT** both default to the label “Calipers” without an explicit taxonomy decision recorded in a governed seed/Board-approved taxonomy artifact. The example above is illustrative and does not invent Accepted taxonomy node codes.

---

## 2. Ownership boundaries

### 2.1 Normative ownership matrix

| Concern | Owner | MUST NOT own |
|---------|-------|--------------|
| Navigation, merchandising, storefront grouping, commercial landing structure | **Commerce Category** | Engineering applicability, validation requiredness, comparison compatibility |
| Engineering identity/class; applicable attributes; requiredness/forbiddenness; validation applicability; engineering comparison compatibility; base knowledge-profile association | **Product Type** (via active Definition) | Price, inventory, SKU, SEO blueprint ownership, editorial content bodies |
| Canonical property code, labels, definition, datatype, dimension, canonical unit, allowed units, generic validation semantics | **Attribute Registry / Property Dictionary** | Product-instance values; commerce Category tree |
| Versioned membership of attributes; required/optional/conditional/forbidden; type-specific validation overrides; display grouping/order defaults; filter/comparison eligibility defaults | **Product Type Definition** | Canonical property identity; instance values |
| Actual model-specific values | **Product** (legacy JSONB until cutover) / **Fact Store** (when authorized) | Definition membership authorship |
| Source artifacts, locators, provenance links, verification evidence | **Evidence subsystem** | Engineering class identity |
| Price, inventory, commercial availability, SKU, brand/model commerce identity fields | **Commerce Product / Offer** | Product Type Definition membership |
| Articles and editorial content | **Content subsystem** | Product Type engineering identity |
| SEO blueprint fields | **SEO subsystem / SEO Profile** | Driving Product Type creation from SEO wording |

### 2.2 Aggregate-root rule

Product Type is the **aggregate root** connecting:

- versioned Product Type Definitions;
- bounded profiles (by reference);
- Product Type Assignments.

Product Type **MUST** reference bounded profiles rather than directly owning unrelated mutable commerce, SEO, content, UI, and knowledge payload data.

### 2.3 As-built gap (runtime truth)

| Concept | As-built | Cite |
|---------|----------|------|
| `products.product_type_id` | **Absent** | `app/db/models/product.py` (no product_type field) |
| Spec template ownership | Category `spec_template_key` + in-code templates | `product.py` Category model · `app/services/spec_template_service.py` |
| Property Dictionary / Facts / industrial taxonomy tables | **Absent** | alembic / `app/db/models/` |
| Legacy JSONB | Present; operational SoT for specs | `product.py` `specifications` JSONB |

Category currently acts as a **de facto** specification-template proxy. That practice is **not** the permanent engineering model under this contract.

---

## 3. Product Type identity rule

### 3.1 Primary identity dimensions

A Product Type is defined primarily by:

1. engineering function;
2. measurement purpose;
3. fundamental measurement geometry;
4. materially different applicability/validation requirements.

### 3.2 Justification gate (when a new Product Type is allowed)

A new Product Type is justified only when **at least one** is true:

- required attribute set differs materially;
- forbidden attribute set differs materially;
- validation rules differ materially;
- comparison compatibility differs materially;
- measurement geometry/function differs materially;
- evidence requirements differ materially.

### 3.3 Non-justifications (MUST NOT create a Product Type solely for)

Brand · range · size · IP rating · material · battery · data output · wireless support · handedness · jaw material · certificate inclusion · cosmetic presentation · SEO landing wording · Digital/Dial/Vernier alone.

### 3.4 Owner external evidence (non-repository)

Owner-provided catalogue summaries (INSIZE / DASQUA) are **external evidence**, not repository facts. They inform the initial Calipers seed (§5) and the orthogonality of readout vs function. They MUST NOT be presented as as-built DB truth.

---

## 4. Orthogonal profile model

### 4.1 Bounded profile dimensions (minimum)

| Profile | Role | Typical form |
|---------|------|--------------|
| **Readout Profile** | digital / dial / vernier | Controlled vocabulary; product assignment or definition default |
| **Geometry Profile** | jaw length, depth-bar shape, groove geometry flags | Definition defaults + product Facts/attributes |
| **Protection Profile** | IP rating and related | Product Facts; evidence-gated |
| **Connectivity Profile** | data output, wireless protocol, transmission distance | Capabilities + conditional attributes |
| **Construction / Material Profile** | jaw tips, body material | Product attributes/Facts |
| **Presentation Profile** | display grouping/order defaults | Definition-level defaults |
| **Search / Filter Profile** | filterable facets eligibility | Definition-level defaults; derived for PLP |
| **Comparison Profile** | comparability group eligibility | Definition-level + compatibility groups |
| **Knowledge Profile** | base knowledge association hooks | Definition-level defaults / references |
| **SEO Profile** | SEO blueprint consumption | Bounded profile; MUST NOT own engineering identity |

### 4.2 Profile implementation classes

| Class | Meaning |
|-------|---------|
| Controlled vocabularies | Closed enum sets (e.g. readout: `digital` \| `dial` \| `vernier`) |
| Versioned entities | Evolve only via new Definition version or versioned profile entity |
| Product assignments | Per-product values (nullable until assigned) |
| Definition-level defaults | Defaults on active Product Type Definition |
| Derived from Facts | Computed for search/comparison from published Facts (future waves) |

### 4.3 Wave-1 vs later structures

| PT-W1 required structures only | Later waves (not PT-W1) |
|--------------------------------|-------------------------|
| Product Type core entity + lifecycle | Product Type Definition v1 + Attribute Membership (**PT-W2**, after Prompt 11A Property Definitions) |
| Nullable `products.product_type_id` | Readout persistence (PT-W2 or dedicated profile sub-wave) |
| No Definition payload; no profile JSON | Ambiguity queue / assignment workflow (**PT-W3**) |
| No catalogue Product Type seed | Full SEO / Geometry / Comparison profile runtimes |

**PT-W1 MUST NOT** add readout columns, profile tables, Definition/membership tables, taxonomy nodes, or Caliper catalogue seeds.

**Forbidden design:** one giant JSON document as the sole Product Type Definition payload. Membership, validation overrides, and profiles MUST be separable structures (tables or clearly bounded documents), even if early waves implement a subset.

---

## 5. Initial caliper model (governed candidates)

### 5.1 Hierarchy placement

Using the non-duplicative example in §1.4:

- Engineering Domain: Dimensional Metrology
- Tool Family: Sliding Measuring Instruments
- Product Family: **Calipers** (governed candidate family)
- Product Types: §5.2 candidates

### 5.2 Proposed Product Types (governed candidates — not PT-W1 seeds)

| Product Type | Engineering function / geometry focus | PT-W1 seed? |
|--------------|----------------------------------------|-------------|
| General-purpose Caliper | Standard OD/ID/depth/step measurement geometry | **No** |
| Depth Caliper | Depth-primary measurement geometry | **No** |
| Internal Groove Caliper | Internal groove measurement geometry | **No** |
| External Groove Caliper | External groove measurement geometry | **No** |
| Disk-Brake Caliper | Disk-brake specialized measurement geometry | **No** |
| Specialty Caliper | Materially distinct specialty function/geometry that fails General-purpose + geometry-profile criteria | **No** — not activated/seeded until pilot evidence + steward review define its boundary |

**Norms:**

- PT-W1 **does not** seed catalogue Product Types.
- The six Caliper Product Types remain **proposed governed candidates**.
- Specialty Caliper is **not** activated or seeded until pilot evidence and steward review define its boundary.
- No Product assignment backfill occurs in PT-W1.
- This list is **not** a closed universal catalogue of all future types.

### 5.3 Readout Profile vocabulary (concept only until PT-W2+)

| Value | Meaning |
|-------|---------|
| `digital` | Electronic digital readout |
| `dial` | Dial indicator readout |
| `vernier` | Vernier scale readout |

**Normative deferral (closes KB-PT-00 open question #2):**

- PT-W1 **does not** add a readout column or profile table.
- PT-W1 is limited to Product Type core + nullable Product FK (§6.4).
- Readout persistence is designed in **PT-W2** or a dedicated profile sub-wave.
- KB-PT-01 / Cursor **MUST NOT** guess between a product column and an association table for readout.
- Digital/Dial/Vernier remain the approved **controlled vocabulary concept**, with physical persistence deferred.

### 5.4 Why Digital Caliper is insufficient as complete Product Type

- A **Depth Caliper** may be digital or vernier.
- A **Groove Caliper** may be digital or analog.
- DASQUA/INSIZE commercial “Digital / Dial / Vernier / Special” axes are **orthogonal** to engineering function/geometry.
- Modeling “Digital Caliper” alone as the Product Type collapses function differences and forces Product Type explosion for IP67, wireless, left-hand, jaw tips, etc.

**Norm:** Readout is orthogonal to Product Type. Variants such as IP67, wireless/Zigbee, data output, mini, plastic, left-hand, heavy-duty, carbide/ceramic jaws, round/rectangular depth bar are generally **attributes / capabilities / geometry / construction / profiles**, not separate Product Types (§3.3).

### 5.5 Long-jaw / special-jaw decision rule (deterministic)

| Condition | Classification |
|-----------|----------------|
| Instrument retains general-purpose OD/ID/depth/step function; jaw length/shape changes do **not** materially change required/forbidden/validation/comparison sets | **General-purpose Caliper** + Geometry Profile (and Construction Profile as needed) |
| Instrument’s measurement purpose/geometry changes such that required/forbidden/validation/comparison/evidence sets differ materially from General-purpose (§3.2) | **Distinct Product Type** (e.g. Depth, Groove, Disk-Brake, or Specialty) |

Title keywords alone are **insufficient** for assignment.

### 5.6 Accuracy vs resolution (metrology non-negotiable)

Accuracy and resolution are **distinct properties**.

Owner external evidence (INSIZE 1108): resolution 0.01 mm may coexist with accuracy ±0.02 mm or ±0.03 mm by model/range. Legacy JSONB values such as `دقت = 0.01` MAY actually represent resolution and **MUST NOT** be migrated as verified accuracy without evidence (§11–§12).

---

## 6. Product relationship

### 6.1 Normative relationship (chosen)

```text
products.product_type_id  →  product_types.id   (nullable FK, Wave 1)
```

### 6.2 Requirements

| Rule | Norm |
|------|------|
| Nullability | Initially **nullable** |
| PKE identity | Product keeps `products.id` as PKE identity (ADR-014) |
| Cardinality Wave 1 | **One primary** Product Type per Product |
| Unassigned | `product_type_id IS NULL` with explicit stewardship state supported |
| Ambiguous | Supported via ambiguity queue; MUST NOT force silent assignment |
| Category auto-assign | **Forbidden** — no automatic assignment from Category alone |
| Title-only heuristics | **Forbidden** without human review |
| Deletion | Product Types use **lifecycle status** rather than hard deletion |
| Orphans | Product Type deletion MUST NOT silently orphan Products |

### 6.3 Recommended FK deletion behavior

| Behavior | Recommendation |
|----------|----------------|
| Product Type row hard-delete | Prefer **RESTRICT** (omit `ondelete` / explicit restrict) so DB rejects delete while products still reference the type |
| Lifecycle | Prefer `draft` → `active` → `retired` on Product Type; retired types remain resolvable for history |
| App policy | Steward tools retire types; reassign or clear assignments explicitly before any exceptional hard-delete |

**Justification:** Matches established commerce pattern for `products.category_id` (no CASCADE; application-managed lifecycle) and prevents silent SET NULL loss of engineering classification. Restrictive deletion + lifecycle retirement is the Wave-1 default unless a later Board decision records a stronger pattern.

### 6.4 Minimum PT-W1 runtime contract (KB-PT-01 scope)

KB-PT-01 **MAY** proceed only after the mandatory Board clarification in ADR-015 / §20. Until that minute exists, KB-PT-01 is **governance-blocked**.

When unblocked, KB-PT-01 creates **only**:

#### `product_types`

| Concern | Norm |
|---------|------|
| Primary key | Use the **established repository model convention**; exact SQL PK type is recorded by KB-PT-01 after repository inspection — **do not invent** it in this documentation correction |
| `code` | Immutable unique code |
| `slug` | Unique slug when repository conventions support slugged admin entities |
| `name_fa` | Required FA display name |
| `name_en` | Nullable when translation is unavailable |
| `description` | Optional |
| `status` | Lifecycle: `draft` \| `active` \| `retired` |
| Timestamps | Follow repository conventions |
| Forbidden in PT-W1 | Product Type Definition payload; profile JSON; taxonomy-node duplication; hard-coded Caliper seed |

#### `products`

| Concern | Norm |
|---------|------|
| `product_type_id` | Nullable FK to `product_types` |
| Index | Indexed FK |
| Delete behavior | Restrictive (see §6.3) |
| Backfill | **None** |
| Category-triggered assignment | **Forbidden** |
| Public API exposure | **None** in PT-W1 unless explicitly required by an existing Accepted contract (default: omit) |

#### Admin authorization (early waves)

Until an Accepted ADR introduces Knowledge Steward:

- PT-W1 and PT-W2 admin mutations use the existing **super-admin** authorization pattern.
- This does **not** prevent a later narrower Knowledge Steward role.
- PT-W1 **MAY** omit mutation endpoints entirely if its implementation prompt is schema/model-only.

### 6.5 Taxonomy linkage timing

| Timing | Norm |
|--------|------|
| PT-W1 | Creates **no** `knowledge_taxonomy_nodes` (Prompt 13 has not run) |
| Aggregate root | Product Type is the primary first-class aggregate root |
| Prompt 13 | Later introduces governed taxonomy linkage for secondary/multi-dimensional classification |
| Identity rule | Future linkage **MUST** avoid duplicate independent Product Type identities |
| Bridge shape | Exact one-to-one bridge shape requires the **mandatory Board clarification** (ADR-015); owner direction alone cannot invent it |

---

## 7. Category relationship

### 7.1 Semantics

| Capability | Norm |
|------------|------|
| One Category containing multiple Product Types | **Supported** |
| One Product Type appearing in multiple commerce Categories | **Supported** when merchandising requires it |
| Category change auto-changing Product Type | **Forbidden** |
| Product Type change auto-changing Category | **Forbidden** |

### 7.2 Mapping table decision (Wave 1)

A separate `category_product_types` (or equivalent) advisory mapping is **deferred** for Wave 1.

| Option | Decision |
|--------|----------|
| Required in Wave 1 | **No** |
| Optional advisory mapping | **Deferred** (MAY be introduced in a later wave for merchandising hints) |
| Ownership of Product Type assignment | **Never** — assignment SoT is `products.product_type_id` (+ ambiguity queue), not Category mapping |

---

## 8. Product Type Definition lifecycle

### 8.1 States

| State | Meaning |
|-------|---------|
| `draft` | Editable working definition |
| `active` | Sole active definition for the Product Type |
| `retired` | Historical; retained for interpretation/traceability |

### 8.2 Rules

1. Only **one** `active` definition per Product Type at a time.
2. After activation, a Definition is **immutable** except by creating a **new version**.
3. Activation requires **reviewer** identity and **change reason**.
4. Retirement MUST NOT delete historical interpretation.
5. Facts and validation reports MUST be traceable to the Definition version used.
6. Definition changes MUST NOT silently rewrite Product values (JSONB or Facts).

### 8.3 Versioning

Use **integer version** (`1`, `2`, `3`, …) per Product Type for Definition rows in Wave 1, consistent with operational simplicity for overlay tables.

Semantic versioning (`MAJOR.MINOR.PATCH`) MAY label human-facing change notes but is **not** required as the primary DB key in Wave 1.

---

## 9. Attribute membership

### 9.1 Requiredness (normative)

| Value | Meaning |
|-------|---------|
| `required` | Must be present for validation/publication gates that depend on this Definition |
| `optional` | May be present |
| `conditional` | Required or applicable only when an applicability condition holds |
| `forbidden` | Must not be present for this Definition (+ profile conditions) |

### 9.2 Membership fields (conceptual)

| Field | Notes |
|-------|-------|
| Product Type Definition reference | Versioned definition id |
| Property Definition reference | Canonical property id/code — **no duplication** of canonical definition body |
| requiredness | `required` \| `optional` \| `conditional` \| `forbidden` |
| applicability condition | Machine-checkable condition (e.g. readout=dial) |
| type-specific validation overrides | Narrowing/overrides only; cannot invent a new property identity |
| public visibility default | Default public/non-public |
| filterable | Search/Filter Profile eligibility default |
| comparable | Comparison Profile eligibility default |
| display group | Presentation Profile |
| display order | Presentation Profile |
| evidence requirement override | Tightens (or documents) evidence expectation vs property default |

---

## 10. Validation model

### 10.1 Layering (order)

1. Canonical Property validation (datatype, unit, generic constraints)
2. Product Type Definition applicability (membership + requiredness)
3. Product Type-specific overrides
4. Cross-field rules
5. Evidence / publication gates

### 10.2 Illustrative rules (not yet governed definitions)

Unless promoted into governed Definition membership, the following are **illustrative only**:

- `battery_type` forbidden for non-powered readout profiles;
- `dial_graduation` forbidden unless readout=`dial`;
- `vernier_graduation` forbidden unless readout=`vernier`;
- `wireless_protocol` required when wireless capability is true;
- `transmission_distance` applicable only when wireless capability is true;
- IP rating allowed only when manufacturer evidence exists;
- accuracy and resolution remain distinct properties.

---

## 11. Legacy JSONB strategy

| Phase | Policy |
|-------|--------|
| **Phase 0** | Legacy JSONB unchanged; Product Type architecture introduced; **no dual-write** |
| **Phase 1** | Product Type assignment; validation MAY inspect legacy JSONB **read-only**; no rewrite required |
| **Phase 2** | Controlled mapping produces **candidates**; candidates are **not** verified Facts; ambiguous keys remain unresolved |
| **Phase 3** | Separate Board/owner-approved migration task MAY import verified values with evidence, idempotent batches, rollback, and revision history |

### 11.1 Prohibitions

- Bulk copying current JSONB into Facts
- Treating legacy key `دقت` as canonical accuracy without evidence
- Automatic mapping from `0.01` to accuracy
- Hidden dual-write keeping JSONB and Facts synchronized

---

## 12. Evidence and source policy

### 12.1 Source priority

1. Official manufacturer catalogue / datasheet / manual
2. Official distributor material
3. Verified internal source
4. Exploratory source

AI output and existing JSONB are **candidate sources**, not sufficient publication evidence for critical metrology Facts.

### 12.2 Critical metrology Fact retention

Every critical metrology Fact MUST retain:

- source artifact;
- page/table/section locator;
- source version/date;
- extraction actor;
- review actor.

---

## 13. API and administration impact (capability contract only)

Full endpoint implementation is **out of scope** for this SPEC. Future required capabilities:

### 13.1 Admin

- Product Type CRUD / lifecycle
- Definition drafting and activation
- Attribute membership management
- Product assignment
- Ambiguity queue
- Validation report
- Definition history

### 13.2 Public

- Resolved Product Type identity when approved for public display
- No internal definition/provenance leakage
- Public attributes based on active Definition and published Facts

### 13.3 Product create/update

- Category and Product Type are **separate fields**
- Changing Category MUST NOT silently replace Product Type
- Changing Product Type requires validation and explicit handling of incompatible values

---

## 14. Search, filter, comparison, SEO

| Concern | Norm |
|---------|------|
| Filters | Derive from Product Type Definition / Search Profile (strangler from Category templates) |
| Comparison | Allowed only for compatible Product Types or explicitly compatible comparison groups |
| SEO | MAY consume Product Type labels and SEO Profile; MUST NOT own engineering identity |
| SEO-driven typing | Product Type changes MUST NOT be driven by SEO wording |
| Category landings | MAY aggregate multiple Product Types |

As-built PLP filters currently derive from Category templates + JSONB paths. That is transitional and MUST strangler toward Definition/Search Profile ownership in later waves.

---

## 15. Migration and rollout waves

**Corrected sequencing (KB-PT-00A):** Property Definitions must exist before Attribute Membership. Product Type Definition/membership is **PT-W2**, after Prompt **11A**. Master KB prompt numbers **01–14 are not renumbered**.

| Wave / prompt | Name | Schema | Runtime | Backfill | Rollback boundary | Human checkpoint | Acceptance gate |
|---------------|------|--------|---------|----------|-------------------|------------------|-----------------|
| **PT-W0** | Canonical Product Type contract | None | None | None | Docs only | Owner review of this SPEC + ADR-015 | Docs Proposed; gates green; no runtime |
| **PT-W1** | Product Type core + nullable FK | `product_types` + nullable `products.product_type_id` only (§6.4) | Schema/model; optional super-admin mutations; **no** public API by default | **No** Product Type seed; **no** assignment backfill; **no** readout persistence | Drop FK/column/table | **Board clarification minute required before start** | Nullable FK; RESTRICT; no NOT NULL; no auto-assign |
| **KB-REMEDIATION-11A** (Prompt 11A) | Runtime Property Definitions + aliases + Units **only** | `knowledge_property_definitions`, `knowledge_property_aliases`, `knowledge_units` | Admin read + seed-import capabilities | Git seeds remain authoring SoT until import | Drop those three table families | Owner/property ownership review | **MUST NOT** create `knowledge_spec_templates` or `knowledge_template_properties` |
| **PT-W2** | Product Type Definitions + Attribute Memberships | Definition + membership tables | Admin draft/activate (super-admin until Steward ADR) | No silent value rewrite | Drop new tables; Product Type rows may remain | Definition model review | Requires 11A Property Definitions; one-active-definition rule |
| **PT-W3** | Product assignment + ambiguity queue | Queue/state as needed | Admin assignment UI/API | Manual reviewed assignments only | Clear assignments; retire queue rows | Pilot assignment review | No Category-only auto-assign |
| **PT-W4** | Read-only validation of legacy `products.specifications` | None beyond prior | Validation reports | Read-only inspect JSONB | Disable validator | Report review | No JSONB mutation |
| **KB-REMEDIATION-12** (Prompt 12) | Facts + revisions | Fact + revision tables (A4) | Facts runtime | No bulk JSONB→Facts | Drop fact tables | PT-W2 ownership approved | Inherits §12.1 Prompt 12 gate |
| **KB-REMEDIATION-13** (Prompt 13) | Evidence + taxonomy + classification | Evidence + taxonomy + CLASSIFIED_AS (A5) | Secondary taxonomy linkage | No silent CLASSIFIED_AS flood | Drop overlay tables; never drop `categories` | Board-clarified bridge shape | Product Type remains primary; CLASSIFIED_AS secondary |
| **PT-W6** | Controlled knowledge-population pilot | None beyond prior | Pilot writes only | Small reviewed set | Revert pilot Facts/assignments | Pilot evidence review | INSIZE pilot constraints held |
| **PT-W7** | Separate legacy migration/cutover decision | Per separate approved task | Optional cutover | Verified-only import | Documented rollback | Board/owner migration approval | No hidden dual-write |

**Removed / renamed:** former undifferentiated “PT-W5 Property/Facts/Evidence” blob is replaced by explicit **11A → PT-W2 → 12 → 13** sequencing.

---

## 16. Initial pilot

| Field | Value |
|-------|-------|
| Brand | INSIZE |
| Candidate scope | General-purpose calipers; initially digital-readout products with confirmed official catalogue evidence |
| Constraints | Small reviewed set; no broad catalogue migration; no title-only assignment; no unsupported series inference; official evidence required; ambiguous 1103/1106/1115-series products remain unverified when official evidence unavailable |
| Outputs | Product Type assignment; Readout Profile; Product Type Definition V1; initial canonical properties; source/evidence map; legacy-key conflict report; validation report |
| Forbidden | Production bulk write |

---

## 17. Non-goals

- No replacement of `products.id`
- No graph database
- No second commerce taxonomy / Category DAG
- No immediate `NOT NULL` on `product_type_id`
- No automatic Category→Type assignment
- No bulk JSONB migration
- No JSONB↔Facts dual-write
- No full AI publishing
- No redesign of price/inventory
- No implementation in tasks KB-PT-00 / KB-PT-00A
- No PT-W1 readout persistence, Product Type catalogue seed, or assignment backfill
- No Prompt 11A creation of Category-owned `knowledge_spec_templates` / `knowledge_template_properties`
- No Board minute fabrication; no Accepted Canon claim

---

## 18. Acceptance criteria (Given / When / Then)

1. **Given** one commerce Category, **when** multiple Product Types are assigned to products in that Category, **then** the model remains valid and Category still owns only merchandising placement.
2. **Given** one Product Type, **when** products of that type appear in multiple Categories, **then** engineering classification remains the Product Type assignment and Categories remain independent.
3. **Given** a newly migrated schema at PT-W1, **when** no assignment has occurred, **then** `products.product_type_id` MAY be NULL and no Product Type rows were required by seed.
4. **Given** an ambiguous product, **when** steward review cannot determine type, **then** the product remains unassigned or queued as ambiguous and MUST NOT receive a silent Category-derived type.
5. **Given** a Depth Caliper with digital readout and a Depth Caliper with vernier readout, **when** classified (after readout persistence exists in PT-W2+), **then** both share Product Type Depth Caliper and differ by Readout Profile vocabulary.
6. **Given** an active Definition that marks an attribute `forbidden`, **when** validation runs, **then** presence of that attribute fails validation for that Definition version.
7. **Given** an active Definition V1, **when** stewards need a membership change, **then** they MUST activate a new Definition version rather than mutate V1 in place.
8. **Given** Phase 0–1 policy, **when** Product Type architecture and assignments are introduced, **then** `products.specifications` JSONB is not mutated by Product Type writers.
9. **Given** resolution `0.01` and accuracy `±0.02` evidence, **when** mapping candidates are produced, **then** systems MUST keep accuracy and resolution as distinct properties and MUST NOT treat legacy `دقت=0.01` as verified accuracy without evidence.
10. **Given** Product Type assignment, **when** any knowledge join is made, **then** PKE identity remains `products.id` (ADR-014) and Product Type does not replace it.
11. **Given** this SPEC and ADR-015, **when** status is inspected, **then** both remain Proposed and Architecture Board acceptance is not claimed.
12. **Given** Prompt 11A prerequisites unmet, **when** Property Dictionary runtime work is attempted, **then** work MUST halt per Master KB §12.1.
13. **Given** Prompt 11A executes, **when** deliverables are inspected, **then** `knowledge_spec_templates` and `knowledge_template_properties` are absent from Prompt 11A scope.
14. **Given** no Architecture Board clarification minute for Hybrid vs `PRODUCT_CLASSIFIED_AS`, **when** KB-PT-01 runtime schema work is attempted, **then** work is governance-blocked.
15. **Given** hierarchy examples, **when** Tool Family and Product Family labels are inspected, **then** they are non-duplicative (Sliding Measuring Instruments ≠ Calipers) unless an explicit taxonomy decision says otherwise.

---

## 19. Compatibility with Accepted Canon and Master KB

| Authority | Relationship |
|-----------|--------------|
| ADR-013 | Postgres remains SoR; no graph DB; no dual-write authorization |
| ADR-014 | `products.id` remains PKE identity; Product Type classifies, does not replace |
| SPEC-industrial-taxonomy-model | Category remains single commerce tree; Hybrid primary FK **extends/conflicts** with CLASSIFIED_AS-centric wording — **Board clarification mandatory** before KB-PT-01 (ADR-015) |
| SPEC-property-dictionary-system | Attribute Registry owns canonical properties (Prompt 11A); Product Type Definition owns membership/applicability (PT-W2) |
| SPEC-master-knowledge-base-remediation | Amended for 11A→PT-W2→12/13 sequencing (§12.1) |

---

## 20. Open questions (remaining after KB-PT-00A)

1. **Board clarification content (mandatory before KB-PT-01):** exact minute wording for Hybrid primary FK vs secondary `PRODUCT_CLASSIFIED_AS`, including the one-to-one bridge shape — **owner direction alone is insufficient** to supersede Accepted Canon.
2. **Specialty Caliper activation boundary:** closed criteria after pilot evidence + steward review (candidate remains inactive until then).
3. **Readout persistence shape (PT-W2+ only):** column vs association table — deliberately **not** decided in PT-W1/KB-PT-01.

**Closed by KB-PT-00A:** PT-W1 readout ambiguity; Admin role for early waves (super-admin); hierarchy example duplication; Prompt 11 vs membership ordering.

---

## 21. Document control

| Field | Value |
|-------|-------|
| Document lifecycle status | **Proposed** |
| Version | **0.1.1** |
| Owner implementation direction | Recorded 2026-08-02 (KB-PT-00); final owner-review corrections KB-PT-00A |
| Architecture Board acceptance | **Not granted** |
| Canonical authority | **Not Accepted Canon** |
| KB-PT-01 status | **Governance-blocked** until Architecture Board minute (or equivalent repository-approved Canon amendment) clarifies Hybrid model |
| Next documentation/governance step | Owner review + Board clarification |
| Next implementation wave (after Board clarification) | **KB-PT-01** — Product Type core table + nullable Product FK only |

---

### 21.1 Final owner-review corrections log (KB-PT-00A)

| # | Correction |
|---|------------|
| 1 | Sequencing: 11A Property Definitions before PT-W2 Attribute Membership |
| 2 | Prompt 11A scope excludes Category-owned templates |
| 3 | Prompt 12/13 gated on PT-W2 Definition/membership ownership |
| 4 | Board clarification mandatory before KB-PT-01 |
| 5 | Non-duplicative hierarchy examples |
| 6 | PT-W1 has no readout persistence |
| 7 | PT-W1 has no Product Type seed / no assignment backfill |
| 8 | Minimum PT-W1 runtime contract recorded; PK type deferred to inspection |
| 9 | Taxonomy linkage deferred to Prompt 13; no PT-W1 taxonomy nodes |
| 10 | Early-wave admin = super-admin until Steward ADR |

---

*End of SPEC-canonical-product-type-model.*
