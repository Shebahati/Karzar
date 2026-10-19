# 10 — Owner decision sheet

**Overall status:** `READY_FOR_OWNER_VISUAL_REVIEW`

| Hero | Verdict | Notes |
|------|---------|-------|
| H01 Special Offers | PASS_WITH_CORRECTION | Delivery fix restores 3840 desktop / 2880 mobile masters |
| H02 Measuring Tools | PASS_WITH_CORRECTION | Same; strong export detail |
| H03 Inserts | PASS_WITH_CORRECTION | Delivery fixed; export more compressed than H01–H02 — monitor fine insert edges |
| H04 End Mills | PASS_WITH_CORRECTION | Delivery fixed; export mid-weight |
| H05 Industrial Machines | PASS_WITH_CORRECTION | Delivery fixed; export mid-weight |

**Not** `SOURCE_QUALITY_BLOCKER` for any hero: masters contain real detail at native resolution; primary defect was **delivery pipeline**, not missing 4K pixels.

Optional follow-up (owner-approved export only): re-export H03–H05 WebP at higher quality (see `07_EXPORT_COMPARISON/`).

## Acceptance gate table

| Hero | Original defect | Root cause | Correction | Desktop QA | Mobile QA | Verdict |
|------|-----------------|------------|------------|------------|-----------|---------|
| H01 | Soft on Retina desktop | Optimizer 1920px cap + re-encode | `unoptimized` static WebP | 3840×2160 `naturalWidth` @ 1920×1080@2 | 2880 mobile @ ≤1023 | PASS_WITH_CORRECTION |
| H02 | Soft on Retina desktop | Same | Same | Evidence in `05_BEFORE_AFTER_DESKTOP/` | `06_BEFORE_AFTER_MOBILE/` | PASS_WITH_CORRECTION |
| H03 | Soft + slightly mushy tools | Delivery + heavier export | Delivery fix | Same | Same | PASS_WITH_CORRECTION |
| H04 | Soft on Retina | Delivery | Delivery fix | Same | Same | PASS_WITH_CORRECTION |
| H05 | Soft on Retina | Delivery | Delivery fix | Same | Same | PASS_WITH_CORRECTION |

**Owner visual sign-off required** — do not treat this audit as substitute for human acceptance.
