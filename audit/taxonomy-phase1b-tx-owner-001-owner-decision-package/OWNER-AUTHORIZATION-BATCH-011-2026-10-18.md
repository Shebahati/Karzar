# TX-OWNER-001 — Owner Authorization Batch 011 (documentary evidence requests only)

**Owner attestation:** explicit in-chat approval on 2026-10-18 for REQUEST_MORE_EVIDENCE on exactly the final 31 P1 IDs. The event's exact UTC clock time was not available; preserve date-only precision. Source: merged PR #521 exact P1 60 matrix blob `6b4f0b53b5809334ca1edbdc16bdd2c2c2dffdf5`; comparison base after merged Batch 010 PR #528 merge `43fb6aea157b8c169dc521931ff2473ddb09cfac`.

## Exact 31 owner evidence requests

- Groz/Chagan exact article, pack and dimensions, 16 IDs: `3007,3220,3221,3222,3223,3224,3225,3226,3227,3228,3229,3230,3231,3232,3233,3234`.
- M7 unresolved suffix, variant or pack, 6 IDs: `5190,5201,5202,5203,5217,5232`.
- M7 index/snippet or individual OEM page fetch incomplete and physical SKU unverified, 9 IDs: `5166,5169,5218,5222,5226,5269,5270,5283,5294`.

All **31** decisions are `REQUEST_MORE_EVIDENCE` only. No additional documentary exit, industrial exception, rehome or title correction is approved. Individual precise gates, original historical SKU/title, maker evidence limitations and pending variant/article issues are maintained in the new journal. HTTP 502/fetch failure is not negative OEM evidence. Manufacturer family/index/near-model evidence is not proof of a precise physical Karzar unit.

## Full frozen-cohort reconciliation

Batches 001–010: **231 distinct IDs = 151 documentary target-catalog exits + 80 owner evidence requests**. These 31 are distinct and not in any past Owner journal. **After this PR merges:** frozen cohort 262 = **151 documentary exit decisions + 111 evidence requests + 0 without a recorded Owner decision**. That is complete initial Owner triage, **NOT** resolution of 111 evidence cases or Production catalog migration. Before merge main remains 151 + 80 + 31. A further evidence collection / decision workflow is needed for the 111 requests. Protected category 154 and 27 oils under category 156 remain untouched.

```text
BATCH_011_DECISIONS=31
DOCUMENTARY_EXIT_APPROVALS=0
OWNER_EVIDENCE_REQUESTS=31
APPLY_AUTHORIZED=NO
CATALOG_EXIT_EXECUTION_DELETE_DISABLE_REHOME=NO
INDUSTRIAL_EXCEPTION_APPROVED=NO
TITLE_CATEGORY_PRODUCT_MANIFEST_MUTATION=NO
PRODUCTION_HESABFA_STOCK_PRICE_DEPLOYMENT=NO
AUTO_MERGE=NO
```

Merging records the expressly selected Owner evidence requests only and is not consent for any operational mutation.
