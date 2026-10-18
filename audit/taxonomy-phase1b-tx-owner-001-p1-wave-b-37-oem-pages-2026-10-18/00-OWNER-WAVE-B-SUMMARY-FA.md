# TX-OWNER-001 — P1 Wave B 37 OEM model evidence reconciliation

**Evidence only, no new Owner decisions.** Base merged PR #519 `b13c817d262fb9d4981f073bdd22327ebe71fe26`, from frozen remaining-60 matrix blob `2498b2e0527ca1986040133ec8f011c41d4248e7`. Exactly 37 M7 previously index-token-only rows and none of 23 Wave A or 49 Owner-decided product IDs.

## OEM evidence scope and limitations

28 exact individual manufacturer product pages successfully retrieved, 2 exact-model search results whose linked individual pages could not be fetched (NE251R, QE633), 7 exact manufacturer index-token rows whose linked pages could not be retrieved (NE432, QE324, QE936, SJ1650T, SJ1830F, SO10T, SU9040). A failed page fetch is **not** an OEM exact page verification, and a listed model is **not** a physical Karzar inventory attestation. The exact IDs, URLs and bounded status appear per SKU in the two CSV documents. Distinct model examples: PA9048 is a riveter **adaptor** not the tool itself; PB9006P/PB9010P are rivet-nut adaptors; NE4901 is an **impact** air ratchet; QE936 OEM index says keyed straight drill while Karzar reversible claim remains unverified; SJCN65 vs official SJ-CN65 punctuation is not automatic stock identity. Pneumatic, riveting, shearing and use in factories do not automatically qualify a handheld tool for one of seven target industrial domains. Lubrication kit SO10T is not automatically Metalworking Fluids & Lubricants, caulking guns are not fluids.

Exact product ID, original title, historical research proposal, prior evidence tier, updated bounded tier and remaining physical-identity/variant gates preserved. All 37 owner_decision fields blank; all 37 agent `REQUEST_MORE_EVIDENCE_RESEARCH_ONLY` notes are NOT Owner decisions. **No Batch 008 is created**. Official totals unchanged: 26 documentary exits, 23 Owner evidence requests and 213 undecided = 262. Cat 154 and 27 industrial oils under 156 untouched.

```text
RESEARCH_ROWS=37
FETCHED_EXACT_OEM_INDIVIDUAL_PAGES=28
EXACT_SEARCH_SNIPPET_WITH_FAILED_PAGE_FETCH=2
OEM_INDEX_TOKEN_WITH_FAILED_PAGE_FETCH=7
PHYSICAL_KARZAR_STOCK_VERIFIED=0
NEW_OWNER_DECISION=0
APPLY_DELETE_DISABLE_REHOME_INDUSTRIAL_EXCEPTION=NO
PRODUCT_CATEGORY_TITLE_MANIFEST_PRODUCTION_HESABFA_STOCK_PRICE_DEPLOY=NO
AUTO_MERGE=NO
```
