# Owner Architecture Decision — FLUIDS-155-FACET-NAV

| Field | Value |
|-------|-------|
| **Journal entry** | `OWNER-ARCH-DECISION-004` |
| **DECISION_ID** | `FLUIDS-155-FACET-NAV` |
| **DECISION_DATE** | 2026-10-18 |
| **DECISION_TYPE** | `STRUCTURAL_ARCHITECTURE_APPROVAL` |
| **Legacy category 155** | Lubricants facet — `KZ.CAT.TRANSITIONAL_LUBRICANTS_FACET_155` |
| **Proposed leaf 156** | `KZ.CAT.FLUIDS_INDUSTRIAL_OIL` under `KZ.CAT.BUYER_FLUIDS` |
| **Protected product IDs** | 27 (category 156 cohort) |
| **B2 link** | group `FLUIDS-155-FACET-NAV` |
| **Gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |

## Approved structural direction

- Industrial oils belong under the **FLUIDS** commerce root (`KZ.CAT.BUYER_FLUIDS`).
- Category **156** remains the proposed specialized industrial-oil leaf (`KZ.CAT.FLUIDS_INDUSTRIAL_OIL`).
- Preserve all **27** protected product IDs.
- Category **155** must **not** become an independently selectable commerce landing page in the target design.
- Preserve existing numeric category **155** identity and importer compatibility until separate Owner execution approval.

## Explicitly NOT approved / not implied

- **`FLUIDS-156-PUBLICATION`** — publication of category 156 is a separate pending Owner decision.
- Display names, SEO titles, H1, URLs, slugs (`IR-MARKET-NAMING-SEO`).
- Production mutation, product reassignment, redirects, `CATEGORY_APPLY`.

## B2 snapshot policy

Frozen B2 register still shows `PENDING` for `FLUIDS-155-FACET-NAV`; this journal entry is authoritative.