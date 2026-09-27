# Stable Identity Contract

**Status:** Proposed design (Phase 1A) — Steward sequencing approved 2026-09-27  
**Phase 0B fact:** Commerce Category `STABLE_SEMANTIC_ID = MISSING`; Product Type `code`, Knowledge `node_id`, Property `definition_id` exist.

---

## 1. Chosen model — Hybrid (Wave 1)

**Decision (D10) + Steward sequencing (Gate 8 APPROVED FOR THIS SEQUENCING):**

| Layer | Role | Mutability |
|-------|------|------------|
| **Internal DB surrogate** | Runtime row identity (`categories.id`, `product_types.id`, …) | Immutable as PK; never used as semantic import key |
| **Published code** | Immutable published semantic identity (`KZ.CAT.*`, `KZ.PT.*` / grandfathered `GEN_CALIPER`, …) | **Immutable after publication**; wrong codes → deprecate + replace, never rename-in-place |
| **Labels** (`name_fa`/`name_en`) | Display | Mutable |
| **Slug** | URL convenience | Mutable with redirect; **not** identity |
| **Parent path** | Hierarchy | Mutable; **not** identity |

### Wave 1 (required for Commerce migration)

```text
categories.id
= internal DB surrogate

categories.code / KZ.CAT.*
= immutable published semantic identity
```

`KZ.CAT.*` is the **required** immutable published semantic identity for Commerce Categories.

### Future optional enhancement

```text
opaque UUID/ULID
```

may later become a deeper immutable object identity if justified. It is **NOT** required before Phase 1B or the initial Commerce taxonomy migration. Do **not** treat UUID/ULID introduction as a Phase 1B prerequisite.

**Rationale:**

- ECLASS IRDI and ETIM EC/EF codes prove language-independent published IDs work in industry (**STANDARD-BACKED** principles).
- Wave-1 published codes close the Commerce semantic gap without blocking design/migration on UUID schema work.
- Hybrid matches as-built direction (`product_types.code`, `node_id`, `definition_id`).

**KARZAR-GOVERNANCE-DECISION:** Treat published **codes** (`KZ.CAT.*` / `KZ.PT.*`) as the external stable semantic identity; integer PKs remain internal only.

---

## 2. Code namespaces

| Entity | Pattern | Example |
|--------|---------|---------|
| Domain | `KZ.DOM.<TOKEN>` | `KZ.DOM.METROLOGY` |
| Family | `KZ.FAM.<TOKEN>` | `KZ.FAM.CALIPER` |
| Product Type | `KZ.PT.<TOKEN>` or legacy `GEN_CALIPER` | Prefer `KZ.PT.*` for **new** types; legacy codes grandfathered immutable |
| Commerce Category | `KZ.CAT.<TOKEN>` | `KZ.CAT.CALIPERS` |
| Application | `KZ.APP.<TOKEN>` | `KZ.APP.QC` |
| Industry | `KZ.IND.<TOKEN>` | `KZ.IND.AUTOMOTIVE` |
| Technical Class | `KZ.TECH.<TOKEN>` | `KZ.TECH.TAPER_BT` |
| Property | existing `definition_id` / `key` | `measurement_range` |

**Token rules:** `UPPER_SNAKE` ASCII; no Persian; no brand tokens; max 64 chars; registry uniqueness global within namespace.

---

## 3. Commerce Category identity — approved sequencing

**Do NOT implement schema in Phase 1A / 1A.1.**

Required sequencing (Steward-approved):

```text
Phase 1B
Design KZ.CAT.* for all live target categories
        ↓
Freeze Current → Target mapping manifest
        ↓
Later schema migration:
categories.code nullable + UNIQUE
        ↓
Backfill codes
        ↓
Validate completeness / uniqueness
        ↓
Make code mandatory for active categories
        ↓
Refactor importers:
semantic code → runtime DB id
        ↓
CI forbids new bare numeric category semantic dependencies
```

**Until then:**

- Document mapping tables for imports (code → live id).
- Forbid new hard-coded integer semantic dependencies in importers (CI proposal).
- Represent deleted 33/34 as deprecated codes in a registry, not “magic numbers”.

---

## 4. Compatibility with as-built

| As-built | Constitution role | Status |
|----------|-------------------|--------|
| `product_types.id` | Internal surrogate | Keep |
| `product_types.code` | Published PT identity | **SUPPORTED** — treat as immutable |
| `product_types.slug` | URL/display | Mutable with care |
| `knowledge_taxonomy_nodes.node_id` | Published knowledge identity | **SUPPORTED** (runtime empty) |
| `knowledge_property_definitions.definition_id` / `key` | Property identity | **SUPPORTED** |
| `categories.id` | Internal surrogate only | **Drift risk** if used semantically |
| `categories.slug` | SEO path | Not identity |
| `megamenu_nav_groups.slug` | Presentation identity | OK for groups |

---

## 5. Versioning operations

| Change | Identity | Action |
|--------|----------|--------|
| Rename label | Unchanged | Update names/synonyms |
| Move parent | Unchanged | Update parent_id / bridge |
| Semantic redefinition | **New** identity | Deprecate old |
| Split | New identities | Map products |
| Merge | Survivor kept; others deprecated with `replaced_by` | Mapping required |
| Deprecate | Kept forever | `status=deprecated`, replacement, reason, date |

**No identifier reuse — ever.**

---

## 6. External crosswalk fields (design)

```text
karzar_concept_id   # published code (Wave 1) or opaque id (future optional)
scheme              # ECLASS | ETIM | ISO13399 | OEM | OTHER
scheme_version
external_identifier
external_label
relation            # EXACT | NARROWER_THAN | BROADER_THAN | RELATED | CANDIDATE
evidence_source
verified_at
notes
```

SKOS-like relations are intentional. No licensed bulk dictionaries stored.
