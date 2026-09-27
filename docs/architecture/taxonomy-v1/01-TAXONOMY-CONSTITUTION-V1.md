# Karzar Taxonomy Constitution V1

**Status:** Proposed design (Phase 1A)  
**Evidence classes used:** `STANDARD-BACKED` · `OEM-BACKED` · `ENGINEERING-INFERENCE` · `KARZAR-GOVERNANCE-DECISION`

---

## 0. Purpose and scope

This Constitution freezes the **scientific classification law** for Karzar. Two qualified engineers classifying the same industrial product SHOULD reach the same conceptual result when applying the tests herein.

It does **not** redesign the live 138-node Commerce Category tree (Phase 1B).

Central separation (normative):

```text
Commerce Category
≠ Product Type
≠ Property
≠ Property Value
≠ Application
≠ Industry
≠ Technical Classification
≠ Brand
≠ Trade Name
≠ Synonym
≠ Megamenu Group
```

---

## 1. Entity catalog (normative)

For each entity: Definition · Purpose · Cardinality · Identity · Parent · Naming · Examples · Counterexamples · MUST NOT · When to create · When NOT to create.

### 1.1 Industrial Domain

| Field | Rule |
|-------|------|
| **Definition** | Broad, long-lived engineering pillar grouping many Product Families. |
| **Purpose** | Knowledge navigation, stewardship ownership, content architecture. |
| **Cardinality** | Few (≈5–12). Product: 0..1 primary Domain when classified. |
| **Identity** | Stable code `KZ.DOM.*` (+ opaque id when schema exists). |
| **Parent** | Null or single root `KZ.DOM.ROOT`. No brand/interface parents. |
| **Naming** | Engineering domain names (FA+EN); not merchandising slogans. |
| **Examples** | Metrology & Inspection; Cutting Tools; Toolholding; Workholding & Fixturing. |
| **Counterexamples** | “BT Holders”; “Digital Tools”; “ZCC”; “CNC Measurement” as Domain. |
| **MUST NOT** | Encode material, interface, brand, actuation, readout. |
| **Create when** | New long-lived industrial pillar with distinct stewardship + families. |
| **NOT create when** | Temporary campaign, brand, single family, or property cluster. |

**Target Domains for Phase 1B (Steward freeze 2026-09-27):**

| # | Domain (EN) | Domain (FA) | Status |
|---|-------------|-------------|--------|
| 1 | Metrology & Inspection | اندازه‌گیری و بازرسی | RECOMMENDED — frozen target |
| 2 | Cutting Tools | ابزارهای برشی | RECOMMENDED — frozen target |
| 3 | Toolholding | ابزارگیر | RECOMMENDED — frozen target |
| 4 | Workholding & Fixturing | گیرش قطعه و فیکسچر | RECOMMENDED — frozen target |
| 5 | Industrial Machines & Equipment | ماشین‌آلات و تجهیزات صنعتی | RECOMMENDED — frozen target |
| 6 | Thread Repair & Thread Inserts | تعمیر رزوه و اینسرت‌های رزوه | RECOMMENDED — frozen target |
| 7 | Metalworking Fluids & Lubricants | سیالات فلزکاری و روانکارها | RECOMMENDED — frozen target |

| Candidate | Status | Reason |
|-----------|--------|--------|
| Workshop / Hand Tools (ابزارهای کارگاهی و دستی) | **REJECTED — OWNER SCOPE DECISION** (`TX-OWNER-001`) | Outside Karzar catalog scope; no target Domain/L1; no replacement catch-all |
| Holding & Fixturing (merge tool+work) | REJECTED as Domain merge | Distinct engineering concerns; may share megamenu |
| Brand domains | REJECTED | Brand ≠ Domain |
| General Tools / Miscellaneous / سایر / ابزار عمومی | **REJECTED** | Forbidden replacement catch-alls (`TX-OWNER-001`) |

**Owner scope rule (`TX-OWNER-001`):** Products/categories whose genuine semantic scope is Workshop Tools, Hand Tools, General Hand Tools, or Woodworking Tools → Category `DEPRECATE/REMOVE`, Product `CATALOG_EXIT`. Rehome forbidden by default. Do **not** confuse legitimate industrial accessories (toolholding/workholding/cutting/metrology/thread repair/fluids/machines) with workshop/hand tools — analyze descendants/products, not only parent names.

### 1.2 Product Family

| Field | Rule |
|-------|------|
| **Definition** | Ontological “kind of tool/instrument” grouping under a Domain; may nest (Family → Subfamily). |
| **Purpose** | Organize Product Types; search/browse knowledge; optional content hubs. |
| **Cardinality** | Product is **not** assigned Family directly as primary identity; Family is inferred via Product Type membership. |
| **Identity** | `KZ.FAM.*` |
| **Parent** | Domain or broader Family. |
| **Naming** | Singular or established collective engineering class (“Caliper”, “Micrometer”, “Insert”). |
| **Examples** | Calipers; Micrometers; Indexable Inserts; End Mills; Twist Drills; Machine Vises. |
| **Counterexamples** | “HSS”; “Digital”; “BT40”. |
| **MUST NOT** | Own product-level Facts; replace Product Type; equal Commerce L1. |
| **Create when** | Multiple Product Types share coherent engineering neighborhood. |
| **NOT create when** | Only one Product Type forever and no knowledge need — may still create for navigation clarity. |

**Resolutions (KARZAR-GOVERNANCE-DECISION + ENGINEERING-INFERENCE):**

| Concept | Level |
|---------|-------|
| Caliper | **Family** (`KZ.FAM.CALIPER`); Product Types under it (e.g. GEN_CALIPER, BLADE_CALIPER) |
| Micrometer | **Family** |
| Insert (indexable cutting item) | **Family** |
| Drill | **Family** (solid + indexable may be subfamilies) |
| End Mill | **Family** |
| Toolholder | **Family** (or subfamilies by holding principle) |

Family **MAY** be public/SEO only if Board authorizes a hub class (ADR-010 / UD-04). Default: **not** SEO hub.

Family does **not** own Product Type Definitions; Product Type does.

### 1.3 Knowledge Category

**STEWARD-APPROVED AMENDMENT (2026-09-27)**

Accepted SPEC currently describes:

```text
Domain → Family → Knowledge Category → Product Type
```

**Normative target hierarchy (Steward-approved):**

```text
Domain
→ Family
→ optional nested Family
→ Product Type
```

`Knowledge Category` is **NOT** a mandatory hierarchy level. It MUST NOT be required for classification completeness.

| Field | Rule |
|-------|------|
| **Definition (legacy/optional)** | Intermediate organizational node between Family and Product Type. |
| **Verdict** | **Not mandatory** — Steward-approved. Prefer nested Family. |
| **If retained** | Optional organizational concept only if a future use case genuinely requires it. |

Accepted SPEC text is **not** edited in place here; formal Board amendment of the Accepted document remains pending. See `11-PHASE-1A-DECISIONS.md` D8.

### 1.4 Product Type

| Field | Rule |
|-------|------|
| **Definition** | The engineering class answering: **What fundamentally IS this product?** Shares a core property schema and working principle. |
| **Purpose** | Primary engineering classification; owns versioned Definition (attribute membership, requiredness, validation). |
| **Cardinality** | Product: **exactly 0 or 1** primary (`products.product_type_id`). Unassigned allowed during migration. |
| **Identity** | Published immutable `code` (e.g. `GEN_CALIPER` / `KZ.PT.*`) + internal DB surrogate (`id`). Opaque UUID/ULID is a **future optional** enhancement — **not** required for Phase 1B or initial Commerce migration. |
| **Parent** | Knowledge membership under Family (bridge), not Commerce Category parent. |
| **Naming** | Singular engineering class; no brand; no stuffed synonyms; no material/interface-only names. |
| **Examples** | General-purpose Caliper; Outside Micrometer; Turning Insert; Square End Mill; Indexable Drill; Machine Vise; Wire Thread Insert. |
| **Counterexamples** | Digital Caliper; Carbide Drill; BT Holder; U-Drill 3D; HELICOIL (as type name). |
| **MUST NOT** | Encode brand, series, size, stock, price, country, pack qty alone. |
| **Create when** | PTST-1 → `NEW_PRODUCT_TYPE` (see `02-PRODUCT-TYPE-BOUNDARY-RULES.md`). |
| **NOT create when** | Distinction is a Property Value, Application, Interface size, or marketing synonym. |

Full split/property tests: document `02`.

### 1.5 Commerce Category

| Field | Rule |
|-------|------|
| **Definition** | Buyer-facing merchandising node in the storefront tree (`categories`, depth ≤ 3). |
| **Purpose** | Navigation, commercial discovery, SEO hubs `/categories/{slug}`, purchase-oriented grouping. |
| **Cardinality** | Product: exactly one `category_id` when assigned (as-built NOT NULL historically; nullable schema exists). Attach to **selectable leaf** (depth 2|3). |
| **Identity** | Today: integer PK only (**gap**). Required: immutable `category_code` (`KZ.CAT.*`) — see `04-STABLE-IDENTITY-CONTRACT.md`. |
| **Parent** | Single parent; max depth 3; L1 roots for megamenu projection. |
| **Naming** | Market-intelligible FA; synonyms not stuffed into name. |
| **Examples** | انواع کولیس; اینسرت تراش CNC; کولت BT… (as **merchandising** projection). |
| **Counterexamples** | Treating Category as Product Type SoR; using Category ID as import semantic code without mapping table. |
| **MUST NOT** | Be the permanent engineering SoR (ADR-015). |
| **Create when** | CCT-1 → `KEEP_AS_CATEGORY`. |
| **NOT create when** | Facet/filter suffices; pure synonym; unstable marketing whim. |

Commerce **MAY** project Property distinctions (HSS Drills, Digital Calipers, BT Holders) **without** creating Product Types — provided Product Type remains engineering truth.

### 1.6 Property Definition

| Field | Rule |
|-------|------|
| **Definition** | Canonical characteristic applicable to one or more Product Types (Property Dictionary). |
| **Purpose** | Facts, filters, comparison, validation. |
| **Cardinality** | Many per Product Type Definition via memberships. |
| **Identity** | `definition_id` / `key` (as-built Property Dictionary). |
| **Parent** | None (dictionary); applicability via PT Definition membership. |
| **Examples** | `measurement_range`, `resolution`, `material`, `readout_type`, `taper_interface`, `flute_count`. |
| **MUST NOT** | Duplicate Product Type identity; free-text chaos without datatype. |

### 1.7 Property Value

| Field | Rule |
|-------|------|
| **Definition** | Concrete value of a Property on a Product (Fact) or allowed enum member. |
| **Purpose** | Instance description; filter options. |
| **Identity** | Value list codes when enumerated; typed literals otherwise. |
| **Examples** | `digital`; `carbide`; `BT40`; `3` (flutes). |
| **MUST NOT** | Become a Product Type solely because the market shops by that value. |

### 1.8 Application

| Field | Rule |
|-------|------|
| **Definition** | **What is this used to do?** Cross-cutting use context. |
| **Purpose** | Secondary classification; content; discovery. |
| **Cardinality** | 0..N per product. |
| **Identity** | `KZ.APP.*` |
| **Examples** | Quality Control; CNC In-Process Inspection; Calibration. |
| **MUST NOT** | Replace Product Type when the “application” is actually the product’s engineering function (e.g. Turning Insert’s turning identity). |

**Process vs Application:** Manufacturing process names (turning/milling) may appear in Product Type identity for cutting items **and** as Application tags for instruments used in those cells. Distinguish via PTST-1 / PBT-1.

### 1.9 Industry

| Field | Rule |
|-------|------|
| **Definition** | Sector where the product is used. |
| **Cardinality** | 0..N; never sole Product Type identity. |
| **Identity** | `KZ.IND.*` |
| **Examples** | Automotive; Aerospace; Machine Building. |
| **Exceptions** | None that create Product Types from industry alone. |

### 1.10 Technical Classification

| Field | Rule |
|-------|------|
| **Definition** | Reusable engineering grouping **not reducible** to a single product-specific property/value pair without losing structure. |
| **Default** | Prefer Property (`material=carbide`, `taper_interface=BT40`). |
| **Allowed** | Multi-axis standard families, accuracy-class systems with coupled constraints, measurement-principle groups used across Families. |
| **Forbidden dump** | Anything that is clearly `property=value`. |
| **Identity** | `KZ.TECH.*` |

### 1.11 Brand

| Field | Rule |
|-------|------|
| **Definition** | Commercial brand entity (`brands` table). |
| **Purpose** | Facet, Brand Hub SEO (`/brands/{slug}`), trust signals. |
| **MUST NOT** | Be Domain/Family/Product Type. |

### 1.12 Manufacturer / OEM Series

| Field | Rule |
|-------|------|
| **Definition** | OEM series/model family (e.g. INSIZE 1108). |
| **Purpose** | Compatibility, content, search synonyms. |
| **Storage** | Property / series Fact / relationship — **not** Product Type. |

### 1.13 Standard / Norm reference

| Field | Rule |
|-------|------|
| **Definition** | Citation of ISO/DIN/ASME/… applicable to the type or instance. |
| **Purpose** | Evidence, compliance claims, crosswalk. |
| **Property** | Often `standard_ref`; crosswalk table for concept mapping. |

### 1.14 Synonym

| Field | Rule |
|-------|------|
| **Definition** | Alternate label for a concept (language-dependent). |
| **Purpose** | Search, import resolution, UI alias. |
| **MUST NOT** | Appear stuffed inside canonical `name_fa`/`name_en`. |
| **No separate ID required** if attached to parent concept (ETIM-inspired). |

### 1.15 Trade Name / Trademark

| Field | Rule |
|-------|------|
| **Definition** | Registered or market trade designation. |
| **Purpose** | Synonym + brand association; never default scientific Product Type name. |
| **Example** | HELICOIL® → synonym of Wire Thread Insert; brand Böllhoff. |

### 1.16–1.18 Relationships (graph, not taxonomy)

Prefer edges over forcing accessories into the Category tree:

| Relation | Meaning |
|----------|---------|
| `ACCESSORY_OF` | Optional adjunct |
| `COMPATIBLE_WITH` | Interface/fit compatibility |
| `REQUIRES` | Hard dependency |
| `REPLACEMENT_FOR` / `SUCCESSOR_OF` | Supersession |
| `CONSUMABLE_FOR` | Consumable linkage |
| `PART_OF` | Kit/system membership |

Examples: Pull Stud ↔ Toolholder; Insert ↔ Tool body; Helicoil tap ↔ Wire Thread Insert system.

### 1.19 Megamenu Group

| Field | Rule |
|-------|------|
| **Definition** | Presentation grouping of L1 Commerce roots (`megamenu_nav_groups`). |
| **Purpose** | Storefront IA only. |
| **MUST NOT** | Define ontology; create Product Types; replace Domains. |
| **Phase 0B evidence** | 6 groups; 15/15 L1 exactly once — healthy presentation layer. |

---

## 2. Decision matrix

| Concept | Primary purpose | Product assigned directly? | Hierarchical? | Multi-value? | Own stable ID? | SEO hub by default? |
|---------|-----------------|---------------------------:|--------------:|-------------:|---------------:|--------------------:|
| Domain | Knowledge pillar | No (via PT bridge) | Yes | No (1 primary) | Yes | No |
| Family | Ontological neighborhood | No | Yes (nest OK) | No | Yes | No |
| Knowledge Category | *(optional; not mandatory)* | No | Yes | No | Yes if kept | No |
| Product Type | Engineering identity | **Yes (0..1)** | Via Family bridge | No | Yes (`code`) | No |
| Commerce Category | Merchandising / SEO | **Yes (1)** | Yes ≤3 | No | **Required (`code`) — missing today** | **Yes** (`/categories/{slug}`) |
| Property | Characteristic | Via Facts | No | N/A | Yes (`definition_id`/`key`) | No |
| Application | Use context | Yes secondary | Optional | **Yes** | Yes | Board-gated |
| Industry | Sector | Yes secondary | Optional | **Yes** | Yes | Board-gated |
| Technical Class | Non-trivial engineering group | Yes secondary | Optional | Yes | Yes | No |
| Brand | Commercial make | Yes (`brand_id`) | No | No | Yes (brand id/slug) | Brand hubs |
| Synonym | Alternate label | No | No | Yes per concept | No | No |

---

## 3. One primary Product Type rule

When classified, a Product **MUST** have exactly **one** primary Product Type (`products.product_type_id`).

Hybrid products (combo instruments, drill-tap tools):

1. Choose the **dominant engineering identity** (function customer buys).
2. Represent secondary capabilities as Application / Property / relationship.
3. If two identities are equally fundamental → `NEEDS_DOMAIN_REVIEW` (steward ticket); do not silently dual-type.

**Evidence:** ADR-015 Hybrid; ETIM one class per product; KARZAR-GOVERNANCE-DECISION.

---

## 4. Null / unknown semantics (conceptual)

| Token | Meaning |
|-------|---------|
| `UNKNOWN` | Value exists in reality but Karzar does not know it |
| `NOT_PROVIDED` | Source did not supply; not yet researched |
| `NOT_APPLICABLE` | Property forbidden/irrelevant for this Product Type |
| `NOT_VERIFIED` | Asserted without sufficient evidence |
| `CONFLICTING_EVIDENCE` | Sources disagree |

These MUST NOT all collapse to SQL NULL at the **conceptual** layer. Schema mapping is deferred (Phase later).

---

## 5. Authority hierarchy (domain-sensitive)

Default priority:

1. Applicable specialist international standard (e.g. ISO 13399 for cutting items)
2. Applicable general product-data standard principles (ECLASS/ETIM **structure**)
3. OEM technical documentation
4. Established engineering terminology
5. Cross-industry classification labels
6. Major manufacturer technical consensus
7. Market / Iranian trade vocabulary
8. Existing Karzar Commerce Category labels

**Override:** For cutting-tool geometry/identity, ISO 13399 concepts outrank generic ECLASS class labels. For metrology instruments, specialist metrology norms + OEM manuals outrank merchandising trees.

Every exception records: decision · rationale · authority · evidence · reviewer · date (`TCR-1`).

---

## 6. Versioning & deprecation (summary)

- **Rename / move:** identity unchanged.
- **Semantic redefinition:** usually **new** identity + deprecate old.
- **Split / merge:** new identities; mapping table required.
- **Deprecation:** no ID reuse; keep replacement pointer; SEO redirect if public URL.
- Historic Categories **33 / 34** MUST be representable as deprecated codes without relying on integer PK meaning.

Details: `04-STABLE-IDENTITY-CONTRACT.md`.

---

## 7. Governance roles (conceptual)

| Role | Responsibility |
|------|----------------|
| Taxonomy Steward | Constitution, Domains/Families, cross-domain conflicts |
| Domain Steward | Families/Types within a Domain |
| Property Steward | Dictionary keys, datatypes, units |
| SEO Reviewer | Hub/redirect impact |
| Engineering Reviewer | PTST-1 / schema fitness |
| Data Migration Reviewer | Import + product-count impact |

Future mutation gate (minimum): semantic review · impact analysis · redirect · import · PT · property · affected product count · migration plan · rollback plan.
