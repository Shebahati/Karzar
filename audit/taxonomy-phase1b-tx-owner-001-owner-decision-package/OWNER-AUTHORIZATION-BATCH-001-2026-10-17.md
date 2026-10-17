# TX-OWNER-001 — Owner decision, Batch 001 (seven M7 SKUs)

Status: **OWNER DECISION RECORDED — NO APPLY AUTHORIZATION**  
Owner decision date: **2026-10-17**; exact chat-message UTC time is not independently available and has not been invented.  
Provenance: Owner's explicit instruction in the conversation approving `APPROVE_CATALOG_EXIT` **only for the target Karzar catalog** for product IDs `5139, 5140, 5174, 5175, 5176, 5177, 5178`, with explicit exclusion of APPLY and Production mutation. This file preserves that authorization as a separate batch record, not an alteration of the generated 262-row pending template.

## Exact decision set

| Product ID | SKU | Owner decision | OEM source ID |
| --- | --- | --- | --- |
| 5139 | NC4233Q | APPROVE_CATALOG_EXIT | OEM-M7-NC4233Q |
| 5140 | NC4233QH | APPROVE_CATALOG_EXIT | OEM-M7-NC4233QH |
| 5174 | PA201 | APPROVE_CATALOG_EXIT | OEM-M7-PA201 |
| 5175 | PA203N | APPROVE_CATALOG_EXIT | OEM-M7-PA203N |
| 5176 | PA211 | APPROVE_CATALOG_EXIT | OEM-M7-PA211 |
| 5177 | PA301 | APPROVE_CATALOG_EXIT | OEM-M7-PA301 |
| 5178 | PA301V | APPROVE_CATALOG_EXIT | OEM-M7-PA301V |

Machine-readable source: `OWNER-AUTHORIZATION-BATCH-001-2026-10-17.csv`.

## Decision scope and immutable inputs

- Source: PR #500 merged at `206e6f53be3dca8232790c9b4e5a7be7188143a7` (reviewed HEAD `d17cebdd8224b15e88999b48af3e0ead7c0a51ee`).
- PR #499 semantic review SHA256: `a3590236eb7e0e2e58bc4bc17e2bce7c588a62f7e07c8b2c4bf0adb8b4ec8e12`.
- Historical census SHA256: `ebd19943e4e86c238a3419a2dcbb0dac7ee3c6dca8041308247bfd5e35c121f3` (2026-10-15T09:34:39Z).
- All seven historical PR #499 proposals: `NEEDS_MORE_EVIDENCE`; all seven post-research PR #500 proposals: `CATALOG_EXIT_CANDIDATE`, supported by exact-model OEM pages in `04-OEM-TECHNICAL-SOURCE-REGISTER.csv`.
- All *other* product decisions remain pending, including product 2915 and 3238. The global proposed distribution 249 / 11 / 1 / 1 is not an Owner approval tally.

## Strict negative authorization

```text
TARGET_CATALOG_EXIT_DECISION_FOR_EXACT_SEVEN=APPROVED
GIT_PR_MERGE=NOT_AUTOMATIC
PRODUCTION_APPLY=NO
PRODUCT_DELETE=NO
PRODUCT_DISABLE=NO
CATEGORY_DELETE_OR_DEPRECATE_APPLY=NO
PRODUCT_REHOME=NO
STOCK_OR_PRICE_CHANGE=NO
HESABFA_MUTATION=NO
DEPLOY=NO
OTHER_PRODUCT_APPROVAL=NO
```

No DB, application runtime, integration, master taxonomy manifest, original generator, or Owner's template is changed by this evidence-only record. Actual future catalog changes require a separate, explicit and scoped Owner APPLY authorization with current preflight and rollback.