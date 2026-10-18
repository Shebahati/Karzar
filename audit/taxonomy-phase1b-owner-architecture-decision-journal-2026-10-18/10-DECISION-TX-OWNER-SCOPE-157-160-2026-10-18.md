# Owner Architecture Decision — TX-OWNER-SCOPE-157-160

| Field | Value |
|-------|-------|
| **Journal entry** | `OWNER-ARCH-DECISION-007` |
| **DECISION_ID** | `TX-OWNER-SCOPE-157-160` |
| **DECISION_DATE** | 2026-10-18 |
| **DECISION_TYPE** | `STRUCTURAL_ARCHITECTURE_APPROVAL` |
| **Legacy categories** | **157** · **158** · **159** · **160** (hand tools / woodworking) |
| **TX-OWNER-001 cohort** | 262 product IDs |
| **B2 link** | group `TX-OWNER-SCOPE-157-160` |
| **Gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |

## Approved structural direction

- Exclude categories **157, 158, 159, 160** from the future seven-root specialized commerce architecture.
- Record these identities as **DEPRECATED** in **target design only** (not production mutation).
Target design codes:
- `KZ.CAT.DEPRECATED_TX_OWNER_HAND_TOOLS_157`
- `KZ.CAT.DEPRECATED_TX_OWNER_HAND_TOOLS_158`
- `KZ.CAT.DEPRECATED_TX_OWNER_WOODWORKING_159`
- `KZ.CAT.DEPRECATED_TX_OWNER_WOODWORKING_160`

## TX-OWNER-001 preservation (immutable prior journals)

- **`audit/taxonomy-phase1b-tx-owner-001-owner-decision-package/`** — do not modify prior Owner authorization batches.
- **151** `APPROVE_CATALOG_EXIT` — documentary authorization only, **not** APPLY.
- **111** `REQUEST_MORE_EVIDENCE` — still open and protected.
- **Total scope:** exactly **262** product IDs.
- Do **not** change any individual product authorization.

## Explicitly NOT approved

- Blanket deletion, automatic category retirement, product deletion.
- Product reassignment, redirect deployment, or HTTP 410.
- `CATEGORY_APPLY`, SEO deploy, production deployment.
- Approval of other pending B2 decision groups.

## Future production

Any production action requires separate exact-product evidence, prerequisite validation, and explicit Owner execution authorization.

## B2 snapshot policy

Frozen B2 register still shows `PENDING` for `TX-OWNER-SCOPE-157-160`; this journal entry is authoritative.