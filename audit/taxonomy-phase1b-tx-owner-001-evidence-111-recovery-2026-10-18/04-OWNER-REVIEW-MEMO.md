# TX-OWNER-001 — Owner review memo (111 evidence recovery)

**Status:** `READY_FOR_OWNER_REVIEW` — research-only; no APPLY; Owner disposition remains `REQUEST_MORE_EVIDENCE` for all 111 SKUs.

## Source inventory (honest scope)
- **42** rows in `02-SOURCE-REGISTER.csv` (re-indexed prior audit sources + supplemental Groz category pass).
- **36** rows carry a URL; **6** are explicitly `PRIOR_INDEXED_REFERENCE_NO_URL` (not live recoveries).
- Provenance mix: `{"INDEPENDENT_DISTRIBUTOR": 2, "OFFICIAL_MANUFACTURER_SOURCE": 4, "MANUFACTURER_FAMILY_OR_INDEX": 12, "OFFICIAL_INDIVIDUAL_PRODUCT_PAGE": 13, "PRIOR_INDEXED_REFERENCE_NO_URL": 6, "GENERAL_MARKET_APPLICATION_COMPARATOR": 5}`
- HTTP transport probes (when enabled) indicate reachability only — **not** verified model-content concordance with Karzar stock.

## A. Exact OEM documentary evidence recovered (model/page — not physical stock)
Rows with `exact_oem_documentary_recovered=YES`: **1** of 111.

## B. Partial or family-level evidence
Rows with `partial_or_family_evidence=YES`: **49**.

## C. Conflicting evidence documented
Rows with `conflicting_evidence_flag=YES`: **27**.

## D. Physical-stock evidence still required
Rows with `physical_stock_evidence_required=YES`: **111**.

## E. Remote research unresolved
Rows with `remote_research_unresolved=YES`: **56**.

## Recovery status distribution
```json
{
  "REMOTE_RESEARCH_UNRESOLVED": 56,
  "PARTIAL_OR_FAMILY_LEVEL_EVIDENCE": 27,
  "CONFLICTING_EVIDENCE_DOCUMENTED": 27,
  "EXACT_OEM_MODEL_DOCUMENTARY": 1
}
```

## Register identity (Git blob vs raw digest)
- Git blob SHA-1 (canonical): `bb723a79314314edc080c80c79616f3478e94082`
- Raw file SHA-256: `da51a45ad4a7c6f34ed52a94ad169c7e2a1bc5dee0051d8afca20ef2811d2953`
- Attestation: **MATCH_CANONICAL_GIT_BLOB**

## Safety (unchanged)
- 151 documentary `APPROVE_CATALOG_EXIT` rows and Owner journals 001–011 are immutable inputs.
- Category **154** and **27** industrial oils under **156** remain protected.
- `PRODUCTION_MUTATION=NO` — no catalog, Hesabfa, deploy, or Owner auto-approval.
