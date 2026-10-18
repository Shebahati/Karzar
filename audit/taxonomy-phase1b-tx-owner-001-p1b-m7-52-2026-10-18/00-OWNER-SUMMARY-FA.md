# TX-OWNER-001 — P1B, 52 Mighty Seven SKU-specific research matrix

**Status:** RESEARCH_EVIDENCE_ONLY, NOT_OWNER_DECISIONS. Base merged PR #512 `c253470c12f1447a116224c72640b807270482ed`. Frozen partition P1 68 = P1A 16 + P1B 52. Exactly 52 rows here preserve IDs, SKU, original title/family and historical heuristic candidate.

## واقعی‌سازی طبقه‌بندی
Research cohorts by physical function: 1 drive adapter, 9 air ratchet/kit, 9 riveting, 8 surface preparation, 9 air drilling, 4 cutting/chisel, 8 nailer/stapler/caulking, 4 maintenance/cleaning = **52**. The original family label is not product identity. `5211 / QB48111`: OEM model page confirms a 100×110 mm air jitterbug sander, not a clamp, although historic family is `CLAMPS_VICES`. `5165 / NE0405-KIT`: official OEM page calls it an air ratchet wrench, notwithstanding historic SAW_ACCESSORIES and potentially overstated kit wording. `5300 / SX2101` is an OEM air twister cleaning gun; do not interpret catalog title as automatically a generic high-pressure water washer.

## Evidence strength, not blanket OEM verification
A manufacturer product page was checked specifically for `NE-0405-KIT` (`/product/109`), `QB-48111` (`/product/260`) and `SX-2101` (`/product/568`). An OEM air-ratchet index (`/product_list/3`) and air-sander index (`/product_list/10`) support **category/model-token hypotheses**, not the identity of physical stock. The other source IDs are bounded review placeholders, with URLs blank when not verified in this pass. For all 52, the exact physical Karzar stock is unverified and title-only rows do not claim exact OEM verification.

Variant and class fences: QA511A vs OEM QA-511, QA611A vs QA-611 A/B, QA633QA vs QA-633Q A/B; QD291 vs OEM QD-291N; QP317 vs QP-317X; QE933/QE935/QE936 descriptive geometry/reverse/key-chuck claims need per-model checks; PA/PB riveter accessory types and kit contents may differ. `5131 ME011N` has no independently established exact OEM model source. **No suffix, punctuation, model variant, or physical warehouse item may be silently normalized or claimed verified.** Exact OEM article links, product labels, pack or invoice and OEM specification are prerequisites to stronger claims.

## Research conclusion
Each row conservatively recommends **`REQUEST_MORE_EVIDENCE` as an agent option**, not an Owner-authorized request. This is a research gate, NOT a finding that all 52 must exit or belong in any of the seven approved domains. Target-domain fit is `UNASSESSED_REQUIRES_INDIVIDUAL_SEVEN_DOMAIN_POLICY_REVIEW`, even where an OEM markets the tool for metalworking or factory use. Later individual reviews can change the research recommendation on verified exact evidence, but cannot rewrite historical immutable files.

No overlap with the 41 decisions in Owner Batches 001–006. Owner status unchanged: 22 documentary exits + 19 requests + 221 undecided = 262.

```text
OWNER_BATCH_007=NOT_CREATED
OWNER_DECISION_FOR_ALL_52=NONE
AUTO_APPROVAL=NO
CATALOG_EXIT_OR_EXCEPTION_APPROVAL=NO
APPLY=NO
CATEGORY_PRODUCT_TITLE_MANIFEST_PRODUCTION_HESABFA_MUTATION=NO
DELETE_DISABLE_REHOME_DEPLOY=NO
CAT154_PROTECTED=YES
CAT156_27_OILS_PROTECTED=YES
AUTO_MERGE=NO
```
