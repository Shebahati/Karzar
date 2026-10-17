# TX-OWNER-001 — Owner decision Batch 003: additional evidence requested

**Decision date:** 2026-10-17 (exact message UTC time unavailable; not invented).  
**Decision provenance:** Owner explicitly confirmed `REQUEST_MORE_EVIDENCE` for exactly Product IDs **2915** (internal Karzar SKU 2064) and **3238** (internal Karzar SKU 4457), following merged PR #503, commit `d7ab530cd4e1cd302742f798f4fd81bd7912d6c8`.

| Product ID | Owner decision | Required proof |
| --- | --- | --- |
| 2915 | REQUEST_MORE_EVIDENCE | Actual product photo, dimensions/material or grade, Groz manufacturer article on packaging/invoice; distinguish metalworking lathe blade from woodworking plane blade |
| 3238 | REQUEST_MORE_EVIDENCE | Actual product photo, dimensions/load rating, Groz article on packaging/invoice; distinguish machinist setup jack (MJ/01 class) from general hydraulic jack |

Machine-readable companion: `OWNER-AUTHORIZATION-BATCH-003-2026-10-17.csv`.

**Identity caution:** Internal SKUs 2064 and 4457 are not verified Groz article numbers. Product ID 3238 with internal SKU 4457 must not be confused with unrelated product ID 4457.

**Resulting decision fence:** Both products are pending evidence; neither catalog exit nor industrial exception/rehome is approved. Exclude exactly 2915 and 3238 from any future exit/rehome execution candidate sets until fresh SKU-specific evidence and a separate explicit Owner disposition/authorization. The original generated 262-row journal is a historical PENDING template and is not overwritten by this separately recorded decision.

```text
PRODUCTION_APPLY=NO
PRODUCT_OR_CATEGORY_DELETE=NO
PRODUCT_DISABLE=NO
CATEGORY_REHOME=NO
HESABFA_MUTATION=NO
MANIFEST_REWRITE=NO
DEPLOY=NO
OTHER_PRODUCTS_OWNER_DECISION_CHANGE=NO
PR_MERGE=MANUAL_OWNER_ONLY
```

This batch records an evidence request, not approval to perform any catalog operation. Previously merged owner batches 001/002 remain unchanged.
