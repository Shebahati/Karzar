# Owner Architecture Decision — ACCESSORIES-154-DECOMPOSE

| Field | Value |
|-------|-------|
| **Journal entry** | `OWNER-ARCH-DECISION-003` |
| **DECISION_ID** | `ACCESSORIES-154-DECOMPOSE` |
| **DECISION_DATE** | 2026-10-18 |
| **DECISION_TYPE** | `CONDITIONAL_STRUCTURAL_APPROVAL` |
| **Legacy category** | `154` — Industrial Accessories |
| **Staging code** | `KZ.CAT.TRANSITIONAL_INDUSTRIAL_ACCESSORIES_HUB_154` |
| **Descendant product IDs** | 289 (census graph) |
| **B2 link** | group `ACCESSORIES-154-DECOMPOSE` |
| **Gate** | `IR-MARKET-NAMING-SEO` (mandatory) |

## Approved architecture

- Preserve category **154** as **TRANSITIONAL** during migration planning.
- Account for all **289** descendant live product IDs.
- Design domain-specific destinations from technical identity and evidence.
- Preserve protected subtrees/cohorts (including industrial oils under FLUIDS).
- No blanket deletion or automatic product reassignment.
- Retire legacy navigation only after validated migration, SEO review, and separate Owner execution approval.

## Explicitly NOT approved

- Production mutation, category deletion, product reassignment, redirects, `CATEGORY_APPLY`.

## B2 snapshot policy

Frozen B2 register still shows `PENDING` for `ACCESSORIES-154-DECOMPOSE`; this journal entry is authoritative.