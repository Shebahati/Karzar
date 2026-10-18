# TX-OWNER-001 — P1A: Groz/Chagan exact-SKU investigation (16)

**STATUS:** RESEARCH_EVIDENCE_ONLY / READY_FOR_OWNER_REVIEW. Based on main at merged PR #511 `6cfbf3c0375ac0c039e63c2c488064e70a179b5a`.

## Fail-closed scope
Frozen PR #507 risk register: 176 = P0 19 + P1 68 + P2 89. No P1 overlap with recorded Owner decisions Batches 001–006 (41 distinct IDs). This PR partitions exactly P1 68 into **P1A 16 Groz/Chagan** and **P1B 52 M7** by exact Product ID and retains original family, SKU, title, PR499 heuristic proposal and priority in `01-P1-68-EXACT-SUBCOHORT-PARTITION.csv`. It examines only these 16: `3007, 3220, 3221, 3222, 3223, 3224, 3225, 3226, 3227, 3228, 3229, 3230, 3231, 3232, 3233, 3234`. No Owner decision.

## Evidence summary
The OEM Groz catalogue documents classes for hand saws, hollow punches, centre/automatic/pin punches and stamps, but **no verified match** from internal Karzar SKU to exact Groz manufacturer article or actual physical stock for these 16. No Groz source can validate Chagan file ID 3220. All 16 receive research-only `REQUEST_MORE_EVIDENCE` options, not approved Owner requests; `approved_domain_fit=NOT_ESTABLISHED`. This does not prejudge final catalog exit or exception.

**Priority evidence gaps:** 3222 and 3223 share the same junior saw title but have separate internal SKUs; do not equate them. 3224 could be fret/coping/piercing saw. 3225 and 3226 are separate hollow punches of unknown diameters. 3227 punch set contents unverified. 3228 and 3230 heavy-duty punch set/single are distinct. 3231 and 3232 pin punch versus set differ. 3233 claims 27 letter stamps and 3234 claims nine letters: check pack contents; **do not silently relabel nine-piece letter stamp set as number stamps**. Industrial use or steel-working application does not itself prove membership in an approved seven-domain category; general hand/workshop tools remain out of domain.

Source classifications are family/category references ONLY and never exact Karzar SKU proof. See `02-P1A-16-PRODUCT-TECHNICAL-EVIDENCE.csv` and `03-P1A-SOURCE-REGISTER.csv`. Primary proof still required: physical photo, marking, dimensions, packaging or invoice, exact maker article, and application details. The separate P1B 52 require their own research, not a batch outcome.

## Governance
```text
OWNER_DECISION=NONE
OWNER_BATCH_007_CREATED=NO
APPROVE_CATALOG_EXIT=NO
APPROVE_INDUSTRIAL_EXCEPTION=NO
REQUEST_MORE_EVIDENCE_RECORDED_AS_OWNER=NO
PRODUCT_CATEGORY_TITLE_MANIFEST_MUTATION=NO
APPLY_PRODUCTION_HESABFA_STOCK_PRICE_DEPLOY=NO
PROTECTED_CAT_154_AND_CAT_156_27_OILS=UNCHANGED
AUTO_MERGE=NO
```
Previously recorded totals remain 22 documentary exit approvals + 19 Owner evidence requests + 221 pending = 262. Only an explicit later Owner decision for exact IDs can establish new authorizations.
