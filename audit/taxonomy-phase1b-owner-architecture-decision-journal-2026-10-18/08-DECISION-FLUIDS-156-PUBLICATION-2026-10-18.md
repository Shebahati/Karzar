# Owner Architecture Decision — FLUIDS-156-PUBLICATION

| Field | Value |
|-------|-------|
| **Journal entry** | `OWNER-ARCH-DECISION-005` |
| **DECISION_ID** | `FLUIDS-156-PUBLICATION` |
| **DECISION_DATE** | 2026-10-18 |
| **DECISION_TYPE** | `CONDITIONAL_STRUCTURAL_APPROVAL` |
| **Legacy category** | `156` — Industrial Oil |
| **Proposed commerce identity** | `KZ.CAT.FLUIDS_INDUSTRIAL_OIL` under `KZ.CAT.BUYER_FLUIDS` |
| **Protected product IDs** | 27 |
| **B2 link** | group `FLUIDS-156-PUBLICATION` (name ≠ publication authorization) |
| **Gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |

## Approved (structural only)

- Preserve `KZ.CAT.FLUIDS_INDUSTRIAL_OIL` as the proposed specialized commerce identity.
- Preserve all **27** existing industrial-oil product IDs.
- Maintain architecture separation between legacy category **155** and proposed category **156**.
- Protect the cohort from blanket removal or unintended reassignment.

## Explicitly NOT approved

- **Actual publication** of the category (runtime go-live).
- Final Persian display name.
- SEO title, H1, slug, URL, or redirects.
- Product-level `APPLY` or category migration.
- Any production deployment.

## B2 snapshot policy

Frozen B2 register still shows `PENDING` for `FLUIDS-156-PUBLICATION`; this journal entry is authoritative for conditional structural acceptance only.