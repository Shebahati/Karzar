# Owner Architecture Decision — MACHINE-ACCESSORIES-163-164

| Field | Value |
|-------|-------|
| **Journal entry** | `OWNER-ARCH-DECISION-006` |
| **DECISION_ID** | `MACHINE-ACCESSORIES-163-164` |
| **DECISION_DATE** | 2026-10-18 |
| **DECISION_TYPE** | `CONDITIONAL_STRUCTURAL_APPROVAL` |
| **Legacy categories** | `163` (hub) · `164` (tapping accessories) |
| **Staging hub** | `KZ.CAT.TRANSITIONAL_MACHINE_ACCESSORIES_HUB_163` |
| **Category 164 products** | 80 (PRODUCT_LEVEL_REQUIRED — execution blocked) |
| **MACHINES root** | `KZ.CAT.BUYER_MACHINES` |
| **B2 link** | group `MACHINE-ACCESSORIES-163-164` |
| **Gate** | `IR-MARKET-NAMING-SEO` (mandatory) |

## Approved direction

- Keep category **163** as **TRANSITIONAL** during migration planning.
- Preserve all **80** existing products under category **164**.
- Require exact per-product technical evidence before determining final destination.
- Design specialized destination leaves within the **MACHINES** architecture (`KZ.CAT.BUYER_MACHINES`), based on actual product identity.
- Do **not** create another generic catch-all category as a substitute for decomposition.

## Execution block

- The **80** `PRODUCT_LEVEL_REQUIRED` records remain blocked from execution.

## Explicitly NOT approved

- `CATEGORY_APPLY`, product reassignment, SEO deploy, production mutation.
- Approval of other pending B2 decision groups.

## B2 snapshot policy

Frozen B2 register still shows `PENDING` for `MACHINE-ACCESSORIES-163-164`; this journal entry is authoritative.