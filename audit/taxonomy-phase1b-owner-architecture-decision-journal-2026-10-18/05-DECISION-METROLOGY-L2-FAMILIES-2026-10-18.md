# Owner Architecture Decision — METROLOGY-L2-FAMILIES

| Field | Value |
|-------|-------|
| **Journal entry** | `OWNER-ARCH-DECISION-002` |
| **DECISION_ID** | `METROLOGY-L2-FAMILIES` |
| **DECISION_DATE** | 2026-10-18 |
| **DECISION_TYPE** | `STRUCTURAL_ARCHITECTURE_APPROVAL` |
| **B2 link** | `audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18/` → group `METROLOGY-L2-FAMILIES` |
| **Naming gate** | `IR-MARKET-NAMING-SEO` (display/SEO/URL not approved) |

## Owner statement (FA)

«با همین سه تا موافقم.»

## Approved scope (structural)

Exactly three L2 families under the Metrology commerce root, preserving B1 identities:
- `KZ.CAT.METROLOGY_FAMILY_PRECISION` (parent `KZ.CAT.BUYER_METROLOGY`)
- `KZ.CAT.METROLOGY_FAMILY_CNC` (parent `KZ.CAT.BUYER_METROLOGY`)
- `KZ.CAT.METROLOGY_FAMILY_LABORATORY` (parent `KZ.CAT.BUYER_METROLOGY`)

## Explicitly NOT approved

- Final display names, SEO titles, H1, URLs, slugs (IR-MARKET-NAMING-SEO).
- Product-level category mapping or reassignment.
- `CATEGORY_APPLY`, production deploy, SEO deploy.

## B2 snapshot policy

Frozen B2 register still shows `PENDING` for `METROLOGY-L2-FAMILIES`; this journal entry is authoritative.