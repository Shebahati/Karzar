# TX-OWNER-001 — Owner decision Batch 005 (four evidence requests)

**Owner attestation date:** 2026-10-18; exact chat event time is not available in the audit source and no UTC timestamp is invented. Explicit Owner confirmation in chat was in response to the proposal of `REQUEST_MORE_EVIDENCE` for **exactly Product IDs 3008, 3009, 5227, 5301**. This authorization concerns evidence requests only, not research proposals, catalog exit, exceptions, rehome, title changes or APPLY.

Source: merged PR #508, merge SHA `dbaa9a1713b49d0c78d87f1cad96f12e3e5f4a12`. The authoritative independent four-row decision ledger is `OWNER-AUTHORIZATION-BATCH-005-2026-10-18.csv`. Historical PR499 and postresearch agent proposals are preserved separately; the 262-row proposed decision sheet and prior Batches 001–004 are immutable inputs.

| Product ID | Karzar SKU | Evidence still needed |
| --- | --- | --- |
| 3008 | 3104 | Brandless parallel clamp: physical photo, jaw opening/bar length, manufacturer/article where available, woodworking vs machine Workholding use; **do not presume Groz** |
| 3009 | 3106 | Groz saw arbor: physical photo, shank interface and dimensions, saw bore, packaging/invoice and exact Groz article; distributor family pages are not proof of exact identity; `KZ.DOM.TOOLHOLDING` remains **UNPROVEN** |
| 5227 | QE98L | Actual stock/nameplate photo and exact model: distributor near-model QE-98L references cannot verify the physical Karzar unit |
| 5301 | SY-2001M | Photo/nameplate/invoice: distinguish SY-2001M 360° rotating adaptor from SY-2002M regulator+adaptor; the existing catalog title mismatch is documented, **not corrected** |

```text
OWNER_DECISION_EXACT_FOUR=REQUEST_MORE_EVIDENCE
OWNER_EVIDENCE_REQUEST_RECORDED_NO_APPLY=YES
CATALOG_EXIT_APPROVAL=NO
INDUSTRIAL_EXCEPTION_APPROVAL=NO
REHOME_APPROVAL=NO
TITLE_EDIT_AUTHORIZATION=NO
PRODUCTION_MUTATION=NO
PRODUCT_OR_CATEGORY_DELETE_DISABLE=NO
PRICE_STOCK_HESABFA_MUTATION=NO
MANIFEST_REWRITE=NO
DEPLOYMENT=NO
AUTO_MERGE=NO
OTHER_OWNER_DECISIONS=UNCHANGED
```

These four products remain excluded from catalog-exit/rehome execution candidate sets without new SKU-specific evidence, an additional **separate explicit Owner disposition**, and a distinct APPLY authorization. The remaining 15 P0 products have **no Owner decision** from this batch. Categories 154 and 156 (27 protected oils) are untouched.
