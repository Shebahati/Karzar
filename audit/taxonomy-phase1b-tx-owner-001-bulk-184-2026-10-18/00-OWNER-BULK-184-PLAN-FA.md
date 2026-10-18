# TX-OWNER-001 — Bulk 184 pending exact-SKU research queue (NO OWNER DECISIONS)

Source frozen 262: merged PR #499 exact owner queue blob `e0d1dd1b0ab80b1a4b7b92c8a2ddbe43dca36cc3`; risk triage 176 blob `59820895a792639a12b2447d476530dfa7e55285`; merged PR #521 P1 remaining-60 blob `6b4f0b53b5809334ca1edbdc16bdd2c2c2dffdf5`. Main after merged Batch 008 PR #523: `396a4e3d6fe9cf220b5a07bacffaea42767146fb`.

Subtract all **78 unique** Owner decisions in Batches 001–008 (50 documentary exits, 28 evidence requests) from 262, yielding **184 distinct undecided IDs**, each once, no overlap. This is a **big-batch RESEARCH QUEUE, not new owner approval**. Prior 28 evidence-request cases are a separate follow-up register, not silently added to these 184. Historical source census is not live Production attestation.

## Exactly partitioned research lanes
| Lane | IDs | Review gate |
| --- | ---: | --- |
| P1 exact Groz/Chagan/M7 identity & variants | 31 | Preserve specific exact-article/physical unit/variant gates from merged #521 |
| P2 M7 impact sockets / impact wrenches | 32 | Identify tool versus socket sets and SKU-specific variants; no automatic Toolholding |
| P2 M7 grinders / sanders | 20 | Verify individual models, cutting-tool consumable vs handheld machine distinction |
| P2 M7 pneumatic screwdrivers / hammers plus Groz | 32 | Avoid legacy HAND_TOOLS_PLIERS_WRENCH as proof of identity; explicit exact OEM or actual-unit check |
| P2 air blow guns | 5 | Individual model/nozzle variants; no fluids or industrial-machine assumption |
| Outside 176 BladeKat wood/CNC router | 25 | Verify wood/MDF vs metal substrate; CNC token alone is NOT Cutting eligibility |
| Outside 176 other woodworking | 34 | Verify hand planes/blades, Chagan family and actual wood application per SKU |
| Outside 176 CP-GRAT deburrers | 4 | Distinguish handle, blades and set; manual deburring is not automatically industrial Cutting |
| Outside 176 M7 QK112N air chisel kit | 1 | Verify exact OEM kit and application; no blanket pneumatic industrial exception |
| **Total** | **184** | |

## Faster without lowering evidence quality
Use **parallel family-level source retrieval** once per maker/family and exact row-level OEM article/variant mapping, not one PR per SKU. First complete P1 31 and outside-176 woodworking 64 in large documentation packages, then P2 89 across above four families. For Owner consideration produce one consolidated decision sheet in bounded batches only after evidence review. Any uncertain SKU gets a concrete `REQUEST_MORE_EVIDENCE` *agent option*, never a fabricated Owner decision. Do not promote original PR499 heuristic into OEM verification. Each row retains original title/SKU, historical proposal, research lane, evidence limit and next evidence request. The 28 already-requested evidence cases remain separate.

No automatic APPLY or category/product/name/manifest changes. Protected category 154 / 27 industrial oils under 156 untouched. Seven charter domains only, no Workshop/General/Industrial Accessories catchall. Merging this PR alone never authorizes dispositions or Production changes.

```text
NEW_OWNER_DECISIONS=0
RESEARCH_IDS=184
AUTHORITATIVE_PRIOR_DECISIONS=78
APPLY=NO
CATALOG_EXIT_EXECUTION_DELETE_DISABLE_REHOME=NO
INDUSTRIAL_EXCEPTION_APPROVAL=NO
PRODUCT_TITLE_CATEGORY_MANIFEST_CHANGE=NO
PRODUCTION_HESABFA_STOCK_PRICE_DEPLOY=NO
AUTO_MERGE=NO
```
