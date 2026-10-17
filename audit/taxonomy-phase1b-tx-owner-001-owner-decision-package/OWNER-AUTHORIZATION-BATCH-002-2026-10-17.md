# TX-OWNER-001 — Owner decision, Batch 002 (two M7 die grinders)

**Status:** OWNER DECISION RECORDED — NO APPLY AUTHORIZATION  
**Owner decision date:** 2026-10-17 (date only; exact UTC message time is unavailable and not inferred).  
**Provenance:** Owner explicitly approved exit of the two products presented immediately before their response, 5194 QA210A and 5195 QA211A, **only from the target Karzar catalog**, subject to the same no-APPLY / no-Production scope as Batch 001.

| Product ID | SKU | Owner decision | OEM source |
| --- | --- | --- | --- |
| 5194 | QA210A | APPROVE_CATALOG_EXIT | OEM-M7-158 — https://www.mighty-seven.com/product/158 |
| 5195 | QA211A | APPROVE_CATALOG_EXIT | OEM-M7-159 — https://www.mighty-seven.com/product/159 |

Machine-readable record: `OWNER-AUTHORIZATION-BATCH-002-2026-10-17.csv`.

## Scope and evidence

- Original historical PR #499 and post-research PR #500 proposals for these products: `CATALOG_EXIT_CANDIDATE`, evidence `OEM_DOCUMENTED`.
- Both are documented as handheld pneumatic die grinders, not target-scoped Toolholding products merely because they have collets.
- PR #500 reviewed HEAD: `d17cebdd8224b15e88999b48af3e0ead7c0a51ee`; merge: `206e6f53be3dca8232790c9b4e5a7be7188143a7`.
- Batch 001 is distinct, previously merged in PR #501 at `9fbbe886f10baacea6899cf2030bec9a8150cded`. No changes to Batch 001 or the generated 262-row pending template.

## Strict negative authorization

```text
TARGET_CATALOG_EXIT_DECISION_FOR_EXACT_TWO=APPROVED
PRODUCTION_APPLY=NO
PRODUCT_DELETE=NO
PRODUCT_DISABLE=NO
CATEGORY_DELETE_OR_DEPRECATE_APPLY=NO
PRODUCT_REHOME=NO
STOCK_OR_PRICE_CHANGE=NO
HESABFA_MUTATION=NO
DEPLOY=NO
GIT_PR_MERGE=NOT_AUTOMATIC
OTHER_PRODUCT_APPROVAL=NO
```

This documentation-only decision does not edit the database, runtime, integrations, taxonomy master manifest, or pending proposal generator. Any later action requires a separately scoped Owner APPLY authorization, fresh preflight, and rollback plan.
