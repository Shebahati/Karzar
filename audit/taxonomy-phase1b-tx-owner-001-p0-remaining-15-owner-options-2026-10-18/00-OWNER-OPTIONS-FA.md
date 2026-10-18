# TX-OWNER-001 — Remaining 15 P0: Owner options only

**Status:** READY_FOR_OWNER_REVIEW_OPTIONS_ONLY. Starting main: PR #509 merge `da44d254296cd7a6453d0e9e2259cdd68fc529da`. This is NOT Owner Batch 006 and contains no authorized decision.

The merged PR #508 matrix has 19 P0 Product IDs. Owner Batch 005 explicitly recorded REQUEST_MORE_EVIDENCE for exactly 3008, 3009, 5227, 5301. The exact complement of 15 is represented by `01-REMAINING-15-OWNER-OPTIONS.csv`, preserving SKU/title/agent proposal and original evidence match classes, with `owner_decision` blank.

## Proposed option — thirteen exact M7 catalog-model references (not physical stock attestation)

| Product ID | Karzar SKU | OEM-described class |
| --- | --- | --- |
| 5259 | SB201 | Digital tyre inflator |
| 5260 | SB423 | Analogue tyre inflator |
| 5261 | SB710 | Tyre inflator / pressure gauge |
| 5267 | SG101 | Air-tool lubrication kit |
| 5268 | SG400 | 400 cc pneumatic grease dispensing gun; check SG-400C if mixed stock |
| 5285 | SP102 | Tool spring balancer, 0.6–1.5 kg |
| 5287 | SP104 | Tool spring balancer, 1.5–3 kg |
| 5289 | SP105 | Tool spring balancer, 3–5 kg |
| 5295 | SV1360 | Filter/regulator air preparation |
| 5296 | SV2220 | FRL air preparation |
| 5297 | SV2380 | FRL air preparation |
| 5298 | SW12 | Mini in-line lubricator |
| 5302 | SZ212A | Air-tool inlet regulator |

Each of these thirteen has `EXACT_OEM_ARTICLE_MATCH` to a manufacturer **catalog reference**, and the merged evidence-gap register marks the remaining gaps non-blocking for a documentary Owner choice. No claim of direct inspection of actual Karzar inventory. **Proposed option for individual Owner consideration:** `APPROVE_CATALOG_EXIT` as target-catalog disposition **only**. Alternatives for every ID: `REQUEST_MORE_EVIDENCE` or `DEFER_DECISION`. Research proposal is not authorization and any actual disposition requires explicit Owner approval of the exact IDs and a separate APPLY authorization; it is never a product delete/disable/rehome.

## Separate Groz lane — two family-level, unresolved entries

- **3010 / SKU 3109:** Groz WD/* wheel-dresser family, no exact manufacturer article mapping or observed physical unit. Proposed Owner option: `REQUEST_MORE_EVIDENCE`; alternative `REJECT_EXIT_REQUEST_EXCEPTION_REVIEW` or `DEFER_DECISION`. Need WD stamped article/size, photo, invoice and actual use. Do not infer a cutting-tool domain merely because a Groz page path says cutting-tools.
- **3184 / SKU 4318:** Groz engineer's hand scraper ES/* for precise fitting, but unknown variant/article and no demonstrated fit to any approved seven-domain code. Proposed Owner option: `REQUEST_MORE_EVIDENCE`; alternatively `REJECT_EXIT_REQUEST_EXCEPTION_REVIEW` if Owner wants a separately governed precision fitting policy review, or `DEFER_DECISION`. Request tool photo, geometry (flat/half round/triangular), length and original article. No automatic industrial exception or generic "industrial hand tools" category.

## Decision boundary and reconciliation

Exact 15 Product IDs: `3010, 3184, 5259, 5260, 5261, 5267, 5268, 5285, 5287, 5289, 5295, 5296, 5297, 5298, 5302`. These are the complement of Owner Batch 005's four in PR #508 P0 nineteen; no overlap with Batches 001–005. Their historical and post-research proposals are all CATALOG_EXIT_CANDIDATE, not Owner decisions. Four Batch 005 requests remain unchanged. Existing global Owner counts remain 9 documentary exits approved, 17 requests for more evidence, and 236 pending (262 total), **until** a separate explicit Owner decision and ledger PR.

```text
OWNER_DECISION_ALL_15=PENDING
AUTHORIZATION_STATUS=OPTIONS_ONLY_NOT_OWNER_APPROVED
OWNER_BATCH_006_CREATED=NO
PRODUCT_EXIT_APPLY=NO
INDUSTRIAL_EXCEPTION_APPROVAL=NO
REHOME=NO
PRODUCT_OR_CATEGORY_DELETE_DISABLE=NO
CATALOG_OR_TITLE_MODIFICATION=NO
PRODUCTION_HESABFA_PRICE_STOCK_MANIFEST_MUTATION=NO
DEPLOY=NO
AUTO_MERGE=NO
PROTECTED_CAT_154_AND_CAT_156_27_OILS=UNCHANGED
```
