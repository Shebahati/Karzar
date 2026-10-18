# Owner Architecture Decision — MIXED-CHUCKS-116-118

| Field | Value |
|-------|-------|
| **Journal entry** | `OWNER-ARCH-DECISION-008` |
| **DECISION_ID** | `MIXED-CHUCKS-116-118` |
| **DECISION_DATE** | 2026-10-18 |
| **DECISION_TYPE** | `CONDITIONAL_STRUCTURAL_APPROVAL` |
| **Legacy categories** | **116** · **117** · **118** |
| **PRODUCT_LEVEL_REQUIRED total** | 611 |
| **Workholding root** | `KZ.CAT.BUYER_WORKHOLDING` |
| **B2 link** | group `MIXED-CHUCKS-116-118` |
| **Gate** | `IR-MARKET-NAMING-SEO` (mandatory for display/landing/URL) |

## Approved direction (structural only)

- Separate **chucks** from **chuck accessories** based on actual technical product identity.
- Preserve **611** `PRODUCT_LEVEL_REQUIRED` records:
- Category **116**: 571
- Category **117**: 40
- Category **118**: 0
- Keep legacy categories in **STAGING/HOLD** until validated migration prerequisites are satisfied.
- Require per-product evidence and explicit destination review.
- Do **not** delete category **118** merely because its decomposition cohort is zero.
- Do **not** introduce another generic mixed catch-all destination.

Staging identities (target design):
- `KZ.CAT.STAGING_LATHE_CHUCK_MIXED_116`
- `KZ.CAT.STAGING_FOUR_JAW_MIXED_117`
- `KZ.CAT.STAGING_TWO_JAW_MIXED_118`

## Explicitly NOT approved

- Product reassignment, category mutation, deletion.
- SEO deployment, `CATEGORY_APPLY`, production deployment.
- Approval of other pending B2 decision groups.

## B2 snapshot policy

Frozen B2 register still shows `PENDING` for `MIXED-CHUCKS-116-118`; this journal entry is authoritative.