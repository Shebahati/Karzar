# TX-OWNER-001 — Low-confidence 176 risk triage (Owner review; no decisions)

**Status:** READY_FOR_OWNER_REVIEW_EVIDENCE_ONLY. Source: merged PR #506 main `47118146a8561ff3eb93bc1f24b2ccc2976d869a`. The 176-row source is **a subset of** the frozen 262-product decision sheet and of the **240 pending exit proposals**, not an additional 176 products. All 176 are unique, original proposal `CATALOG_EXIT_CANDIDATE`, confidence basis `HEURISTIC`, and not included in the four already-recorded Owner decision batches (9 approved exit + 13 evidence requests). The other 64 of 240 pending exit proposals are outside this risk register.

## Review order, not outcome

| Research queue | Count | Why |
| --- | ---: | --- |
| P0 — boundary check | 19 | Product title suggests possible overlap with Metrology, Cutting/Toolholding, Workholding, industrial equipment or pneumatic-system components. **This is NOT an industrial exception recommendation.** |
| P1 — heterogeneous / labeling check | 68 | Mixed heuristic families, punches and saw-related items or conspicuous mis-bucketing; read exact titles and individual SKU. |
| P2 — standard SKU review | 89 | Remaining plausible general workshop/hand/pneumatic items. Still require exact SKU-specific evidence and individual Owner decisions before exit. |
| **Total** | **176** | 19 + 68 + 89 |

The 19 P0 exact IDs: `3008, 3009, 3010, 3184, 5227, 5259, 5260, 5261, 5267, 5268, 5285, 5287, 5289, 5295, 5296, 5297, 5298, 5301, 5302`. These are investigation targets, **not** approvals.

**Critical:** Source family codes are unsafe proxies for physical product identity: `CLAMPS_VICES` contains sanding machine ID 5211, while `HAND_TOOLS_PLIERS_WRENCH` includes M7 pneumatic screwdrivers/air hammers. `OTHER_WORKSHOP_HEURISTIC` combines many unrelated products. Neither family nor the presence of `CNC`, a collet, a gauge or a regulator is sufficient to establish one of the seven target domains. No wholesale approvals for an entire family.

## Execution order

1. **P0 next:** exact manufacturer-page and technical-use research for 19 IDs. Record exact SKU match vs family/near-model reference, competing interpretations, photo/dimensions/spec evidence, confidence and Owner options. Any unresolved exact identity stays `REQUEST_MORE_EVIDENCE` recommendation, not automatically recorded.
2. P1: split mixed categories into real technical subcohorts; assess each physical SKU and review context.
3. P2: exact-model evidence for nominally general workshop items; group research may save effort, but Owner decisions remain SKU-specific.
4. Then reconcile the 64 pending exit proposals outside the low-confidence register in a separate scope.

## Safety

This audit only reorders research. It does not change `05-PROPOSED-DECISION-SHEET-262.csv`, the historical 262-row template, four Owner journals, taxonomy master manifest, category state or Production. No Owner decision, catalog exit, industrial exception, rehome, APPLY, deployment, price/stock or Hesabfa mutation. Category 154 and all 27 oils under 156 remain protected.
