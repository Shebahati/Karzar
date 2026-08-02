# ADR-015 — Product Type as the Engineering Classification Source of Truth

## Status
Accepted

### Board Acceptance (ADR-015 Hybrid Clarification)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۱۱ (2026-08-02) |
| **Board** | Karzar Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | [`../../../aods/90-governance/BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION.md`](../../../aods/90-governance/BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION.md) |
| **Meeting** | `AB-ADR-015-2026-08-02` |
| **Ballot** | Option **A** — Accept Hybrid clarification |
| **Conditions** | None beyond the normative constraints recorded in the minute |
| **Scope** | Wave-1 primary engineering classification = nullable `products.product_type_id`; `PRODUCT_CLASSIFIED_AS` remains secondary/multi-dimensional taxonomy mechanism; no duplicate Product Type identities; PKE = `products.id`; Category commerce-only; no graph DB; no dual-write; no bulk JSONB migration; no Category→Type auto-assign; no assignment backfill; Prompt 13 owns taxonomy bridge. |

## Date
2026-08-02

## Deciders
Architecture Board (Mohammad Shebahati) · Platform Architect / Knowledge Architect (prior Proposed authorship)

## Context

Karzar Accepted Canon already separates **commerce Category** (merchandising) from **knowledge classification** (Tool Class / Product Type via industrial taxonomy and `PRODUCT_CLASSIFIED_AS`). As-built runtime still uses Category as the practical specification-template proxy:

- `products.category_id` is required; no `product_type` field exists;
- Category owns `spec_template_key`; template bodies live in code;
- Property Dictionary, Facts, and industrial taxonomy tables are absent;
- `products.specifications` JSONB remains the operational specifications store;
- Wave-1 PKE identity is `products.id` (ADR-014).

Owner implementation direction (not Board acceptance) requires Product Type to become an **independent first-class engineering concept** and the **engineering-classification source of truth**, without replacing Category, without replacing `products.id`, without a graph database, and without authorizing JSONB↔Facts dual-write or bulk JSONB migration.

External catalogue evidence summaries (INSIZE / DASQUA) show that readout technology (digital/dial/vernier) is orthogonal to measurement function/geometry, and that treating readout or commercial variants as Product Types causes Product Type explosion.

Related contracts: `SPEC-canonical-product-type-model.md` (Proposed) · `SPEC-master-knowledge-base-remediation.md` (Proposed, amended for sequencing) · ADR-013 · ADR-014.

## Decision Drivers

- Category MUST remain commerce/navigation only
- Specification applicability/validation MUST ultimately derive from Product Type Definition
- Product Type MUST NOT be only a label table
- Product Type MUST NOT become a God Object
- Deterministic product-level validation and efficient FK access for Wave 1
- Preserve ADR-013 (Postgres overlay; no dual-write authorization) and ADR-014 (`products.id` PKE)
- Avoid Product Type explosion; keep readout/profiles orthogonal
- Safe nullable introduction; no automatic Category→Type assignment

## Considered Options

### Option A — Keep Category as Product Type proxy

Continue using Category (+ `spec_template_key`) as the permanent engineering classification and template owner.

**Pros:** Matches as-built; zero new schema.  
**Cons:** Contradicts Accepted Canon separation and owner direction; couples merchandising moves to engineering meaning; blocks correct validation ownership.  
**Decision:** **Reject.**

### Option B — Only generic taxonomy assignments (no direct Product FK)

Represent Product Type solely as taxonomy nodes + `PRODUCT_CLASSIFIED_AS` / assignment rows, with no `products.product_type_id`.

**Pros:** Aligns closely with Accepted industrial taxonomy wording; flexible multi-label future.  
**Cons:** Weaker deterministic primary classification for Wave-1 validation; less efficient product-level access; easier to leave primary type ambiguous; does not satisfy owner requirement for a first-class Product Type aggregate root with direct product relationship.  
**Decision:** **Reject for Wave-1 primary classification.** Taxonomy assignments remain valuable for secondary/engineering-taxonomy participation.

### Option C — Dedicated Product Type table with direct nullable Product FK only

Introduce `product_types` + nullable `products.product_type_id`, without taxonomy participation.

**Pros:** Clear aggregate root; efficient FK; nullable rollout.  
**Cons:** Risks forking from Accepted multi-dimensional taxonomy; secondary classifications harder later.  
**Decision:** Incomplete alone — absorb into Hybrid.

### Option D — Hybrid model (Chosen)

- Product Type is a **first-class entity** (aggregate root);
- Product Type **participates** in the engineering taxonomy (Tool Class / family dimensions);
- Product has a **direct primary** nullable `products.product_type_id` FK;
- Secondary classifications remain taxonomy assignments (`PRODUCT_CLASSIFIED_AS` / assignment table) when needed;
- Product Type Definition (versioned) owns attribute membership and validation applicability;
- Attribute Registry / Property Dictionary owns canonical property definitions;
- Bounded profiles (readout, geometry, protection, connectivity, construction, presentation, search/filter, comparison, knowledge, SEO) are referenced, not absorbed into a God Object.

**Pros:** Satisfies owner direction; preserves Category boundary; preserves taxonomy participation; enables deterministic validation; nullable safe rollout.  
**Cons:** Requires sequencing amendment before Master KB Prompts 11–13; Board must later reconcile Accepted taxonomy prose with the direct-FK primary path.  
**Decision:** **Select as normative architecture.**

## Decision

1. **Product Type MUST become the engineering-classification source of truth** for applicability, requiredness, forbiddenness, validation, and engineering comparison compatibility.
2. **Category MUST remain** commerce navigation / merchandising / storefront grouping only and MUST NOT remain the permanent Product Type substitute.
3. **Wave-1 primary relationship MUST be** nullable `products.product_type_id` → Product Type, with one primary type per product; unassigned and ambiguous states supported.
4. **No automatic assignment** from Category alone; no title-only assignment without review.
5. **Product Type Definition MUST be versioned** (`draft` / `active` / `retired`); only one active definition per Product Type; immutable after activation except via new version.
6. **Attribute membership requiredness MUST use** `required` | `optional` | `conditional` | `forbidden`.
7. **Readout (digital/dial/vernier) MUST be modeled as an orthogonal profile**, not as the complete Product Type.
8. **`products.id` remains** Wave-1 PKE identity (ADR-014). Product Type classifies; it does not replace Product identity.
9. **No graph database.** PostgreSQL remains system of record (ADR-013).
10. **No JSONB↔Facts dual-write** and **no bulk legacy JSONB→Facts migration** are authorized by this ADR (ADR-013 Decision 4 preserved).
11. **Product Type deletion MUST NOT silently orphan products**; prefer lifecycle retirement + restrictive FK delete behavior.
12. This ADR status is **Accepted** per Board minute `AB-ADR-015-2026-08-02` (Option A). Implementation still requires normal Alembic/PR process; this ADR alone does not ship migrations.
13. **KB-PT-01 is unblocked** for Product Type core table + nullable Product FK after this minute is present on `main`. Later waves remain gated per Master KB §12.1 and SPEC-canonical-product-type-model §15.

## Consequences

### Positive

- Unblocks correct ownership of specification applicability away from Category templates
- Enables safe nullable schema introduction (PT-W1) without forcing backfill — **after** Board clarification
- Prevents Product Type explosion by forcing orthogonality of readout/variants
- Aligns Master KB Property/Facts work behind corrected 11A → PT-W2 → 12/13 gates

### Negative / residual

- As-built Category template filters must strangler over multiple waves
- Additional admin stewardship surfaces (assignment, ambiguity queue, definition activation)
- Exact Product Type ↔ taxonomy-node bridge schema remains for Prompt 13 (must preserve same-identity rule)

## Migration

Follow `SPEC-canonical-product-type-model.md` §15 corrected sequence. Board clarification minute `AB-ADR-015-2026-08-02` is **recorded** (Option A).

1. PT-W0 contract — done
2. Board clarification minute — **Accepted** (this ADR)
3. **KB-PT-01 / PT-W1** Product Type core + nullable FK only (next implementation wave)
4. KB-REMEDIATION-11A Property Definitions + aliases + Units only
5. PT-W2 Definitions + Attribute Memberships
6. PT-W3 assignment + ambiguity
7. PT-W4 read-only JSONB validation
8. KB-REMEDIATION-12 Facts
9. KB-REMEDIATION-13 Evidence + taxonomy + CLASSIFIED_AS (bridge without duplicate identities)
10. PT-W6 pilot → PT-W7 optional cutover

Legacy JSONB remains until a separately approved Phase 3 cutover task.

## Security / integrity implications

- Restrictive FK behavior prevents silent classification loss
- Definition activation requires reviewer + change reason
- Public APIs MUST NOT leak definition provenance/internal stewardship fields
- Validation and publication gates remain evidence-aware for critical metrology
- No dual-write path that could desynchronize commerce JSONB and Facts invisibly

## Relationship to ADR-013

Preserves Postgres overlay storage, forbids graph engine introduction, and does **not** authorize JSONB→Facts dual-write. Product Type tables are additional Postgres overlay/commerce-adjacent schema under the same storage doctrine.

## Relationship to ADR-014

Does **not** change PKE identity. `products.id` remains the Wave-1 join key. `product_type_id` is a classification FK on the same product row, not a new public product identity namespace.

## Relationship to Category

Category and Product Type are independent. Category changes must not rewrite Product Type; Product Type changes must not rewrite Category. Optional Category↔Product Type advisory mapping is deferred and must never own assignment.

## Relationship to Property Dictionary and Facts

Property Dictionary owns canonical property definitions (**Prompt 11A** creates definitions/aliases/units only). Product Type Definition owns membership and applicability (**PT-W2**, after 11A). Facts store instance values on the PKE (`products.id`) in Prompt 12. Templates that today hang from Category/`spec_template_key` MUST strangler toward Product Type Definition ownership — **not** toward new Category-owned `knowledge_spec_templates` / `knowledge_template_properties` in Prompt 11A.

## No-dual-write requirement

This ADR MUST NOT be interpreted as authorizing writers that update JSONB and Facts together, bulk JSONB→Facts projectors, or dropping JSONB.

## Rollback / reversal boundary

- PT-W0 docs can be superseded without schema rollback
- PT-W1 can roll back by dropping nullable FK/column/table if no dependent Definitions/Facts rely on it
- After Facts publish against Definition versions, rollback requires retaining historical Definition rows for interpretation; hard-deleting active classification history is forbidden without an explicit Board-approved migration plan

## Open questions

1. Specialty Caliper activation boundary after pilot evidence
2. Readout persistence shape in PT-W2+ (explicitly **not** a PT-W1/KB-PT-01 decision)
3. Exact one-to-one Product Type ↔ taxonomy-node bridge schema — deferred to Prompt 13; must obey same-identity / no-duplicate rules from this Accepted clarification

**Closed by Board minute AB-ADR-015-2026-08-02 (Option A):** Hybrid primary FK vs secondary `PRODUCT_CLASSIFIED_AS`; PKE identity; Category boundary; no graph DB; no dual-write; no bulk JSONB migration; no Category→Type auto-assign; no assignment backfill.

**Closed by KB-PT-00A:** whether Board clarification is optional (it is not); PT-W1 readout persistence guess; early-wave admin role (super-admin until Steward ADR).

## Related

- Board minute: `aods/90-governance/BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION.md` (**Accepted**)
- `SPEC-canonical-product-type-model.md` (Proposed v0.1.1)
- `SPEC-master-knowledge-base-remediation.md` (Proposed; Product Type sequencing amendment v0.4.1+)
- ADR-013 · ADR-014
- `SPEC-industrial-taxonomy-model.md` · `SPEC-property-dictionary-system.md` · `SPEC-product-knowledge-entity-model.md`
- Tasks KB-PT-00 · KB-PT-00A · KB-PT-00B

### Amendment note (KB-PT-00A)

Dated 2026-08-02. Status was **Proposed**. Added mandatory Board clarification gate, corrected Property/membership sequencing, and PT-W1 scope limits.

### Amendment note (KB-PT-00B)

Dated 2026-08-02. Board minute completed with human-supplied fields. Status **Accepted** (Option A). Canon Lock row required. KB-PT-01 unblocked after merge to `main`.
