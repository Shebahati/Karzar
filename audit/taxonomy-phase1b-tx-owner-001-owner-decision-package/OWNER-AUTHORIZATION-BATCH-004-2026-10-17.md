# TX-OWNER-001 — Owner decision Batch 004: 11 evidence requests

**Owner decision date:** 2026-10-17 (date only; exact UTC message time unavailable and not invented).  
**Provenance:** Owner explicitly authorized `REQUEST_MORE_EVIDENCE` for **exactly** Product IDs `3090, 3091, 3093, 3095, 3096, 3097, 3098, 3099, 3101, 5146, 5147` in the conversation, expressly prohibiting catalog exit, industrial exception, rehome, APPLY, or Production mutation. Research source: merged PR #505, merge commit `9dbd49bd06914f2cb87c1c0feca42609d96f4c4a`.

The independent eleven-row source of record is `OWNER-AUTHORIZATION-BATCH-004-2026-10-17.csv`. This is an Owner **evidence request**, not approval of any candidate exit or exception; the original generated 262-row pending proposal/template is not overwritten.

## Required evidence

- **Exactly nine category-160 grooving/finishing IDs:** 3090 (3865), 3091 (3866), 3093 (3868), 3095 (3870), 3096 (3871), 3097 (3872), 3098 (3873), 3099 (3874), 3101 (3876). Require actual product images, brand, shank/cutter dimensions, geometry, grade/material and packaging/invoice/manufacturer article to distinguish woodworking router bits from metalworking cutting tools. Neither “CNC” in the title nor category assignment proves material/application or manufacturer identity.
- **Exactly two category-158 M7 IDs:** 5146 (NC4277), 5147 (NC4299). Require engraved model/nameplate photos, original manufacturer article or importer invoice. OEM pages for Q-suffix NC-4277Q and NC-4299Q are *not* exact matches to the unsuffixed Karzar entries without direct proof.

## Binding negative authorization

```text
OWNER_DECISION_FOR_EXACT_ELEVEN=REQUEST_MORE_EVIDENCE
EXACT_OEM_IDENTITY=UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH
EXIT_APPROVAL=NO
INDUSTRIAL_EXCEPTION_APPROVAL=NO
REHOME_APPROVAL=NO
PRODUCTION_APPLY=NO
PRODUCT_OR_CATEGORY_DELETE=NO
PRODUCT_DISABLE=NO
STOCK_OR_PRICE_CHANGE=NO
HESABFA_MUTATION=NO
DEPLOY=NO
TAXONOMY_MASTER_MANIFEST_REWRITE=NO
OTHER_PRODUCT_OWNER_DECISIONS=UNCHANGED
GIT_PR_MERGE=MANUAL_OWNER_ONLY
```

The 11 exact IDs are excluded from future catalog-exit or rehome execution candidate sets until additional SKU-specific evidence and a **separate explicit Owner decision and APPLY authorization**. This decision does not change original research matrices, history, or Batches 001–003. Categories 154 and 156, including 27 protected industrial oil products, are out of scope.
