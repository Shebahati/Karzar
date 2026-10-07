# PHASE 3B1 — OWNER DECISION PACK

Status: **READY_FOR_OWNER_POLICY_DECISION** (proposal only — no policy apply).

Wave 3B scope: **132** rows. Safe title-only governance fixes: **0**.

Principle: do not hide taxonomy problems inside broader naming labels.

## D-DIVIDER-01 — DIVIDER (9 rows)

**Problem:** OEM headings are INSIDE/OUTSIDE SPRING CALIPERS; current PT DIVIDER may misrepresent spring calipers

- **Option A:** Split into INSIDE_SPRING_CALIPER + OUTSIDE_SPRING_CALIPER (+ optional STRAIGHT)
- **Option B:** Keep DIVIDER + mandatory identity qualifier (داخل/خارج/مستقیم)
- **Option C:** Reassign all to SPRING_CALIPER umbrella with qualifier
- **Recommended:** A
- **Why:** OEM headings are authoritative functional families; qualifier-only risks taxonomy debt
- **Semantic risk:** HIGH if unified under generic پرگار
- **Future data work:** PT create/reassign + title policy + length variant
- **Immediate unlock:** 0
- **Next blocker:** PRODUCT_TYPE_SPLIT

## D-TAPER-01 — TAPER_GAUGE (9 rows)

**Problem:** Mix of TAPER GAUGES (gap), TAPER BORE GAUGES, and sets

- **Option A:** Split GAP_TAPER_GAUGE vs TAPER_BORE_GAUGE; sets as accessory/set PT
- **Option B:** Keep TAPER_GAUGE + qualifier (گپ/مخروطی/ست)
- **Option C:** Defer all until full OEM page extraction
- **Recommended:** A
- **Why:** OEM headings differ; گیج مخروطی would mislabel gap gauges
- **Semantic risk:** HIGH if single title
- **Future data work:** PT split + range facts
- **Immediate unlock:** 0
- **Next blocker:** PRODUCT_TYPE_SPLIT

## D-STRAIGHT-01 — STRAIGHT_EDGE (1 rows)

**Problem:** OEM evidence insufficient for 4700-200; terminology ambiguous

- **Option A:** خط‌کش مویی (pending exact OEM page)
- **Option B:** خط‌کش لبه‌چاقویی / knife-edge straightedge
- **Option C:** Hold until 108A/B page proof
- **Recommended:** C
- **Why:** Current name alone is not authority
- **Semantic risk:** MEDIUM
- **Future data work:** OEM extraction then title approve
- **Immediate unlock:** 0
- **Next blocker:** SOURCE_EVIDENCE_REQUIRED

## D-LEVEL-01 — LEVEL (16 rows)

**Problem:** Conventional, digital, laser, inclinometer mixed under LEVEL

- **Option A:** Reassign laser/digital/inclinometer out; residual LEVEL uses body_length
- **Option B:** Keep all under LEVEL with free-text subtype qualifier
- **Option C:** Full freeze until OEM page audit complete
- **Recommended:** A
- **Why:** measurement_range is invalid for body length; laser ≠ frame level
- **Semantic risk:** HIGH
- **Future data work:** PT reassignment + body_length property governance
- **Immediate unlock:** 0
- **Next blocker:** PRODUCT_TYPE_REVIEW

## D-DLEVEL-01 — DIGITAL_LEVEL (3 rows)

**Problem:** 4910-* slope meters vs 2199-1 multi-function meter

- **Option A:** Keep 4910-* as DIGITAL_LEVEL with body_length; reassign 2199-1
- **Option B:** Merge into LEVEL with digital qualifier
- **Option C:** Hold all three for source review
- **Recommended:** A
- **Why:** OEM heading DIGITAL LEVELS AND SLOPE METERS supports 4910; 2199 is multi-function
- **Semantic risk:** MEDIUM
- **Future data work:** body_length facts; PT review for 2199-1
- **Immediate unlock:** 0
- **Next blocker:** MISSING_VARIANT_FACT

## D-PLATE-01 — SURFACE_PLATE (6 rows)

**Problem:** Buyer identity is L×W×thickness (and grade), not scalar measurement_range

- **Option A:** Approve variant policy on new plate_dimensions property (L×W×T)
- **Option B:** Use length_only as temporary variant (rejected scientifically)
- **Option C:** Hold until property dictionary adds plate_dimensions
- **Recommended:** A
- **Why:** OEM granite plates are dimensional; scalar range is wrong
- **Semantic risk:** LOW once property exists
- **Future data work:** NEW_PROPERTY_REQUIRED then facts
- **Immediate unlock:** 0
- **Next blocker:** NEW_PROPERTY_REQUIRED

## D-VISE-01 — PRECISION_VISE (3 rows)

**Problem:** 0–67/87/102 must be confirmed as jaw opening capacity from OEM

- **Option A:** Variant = jaw_opening_capacity_mm after OEM confirm
- **Option B:** Variant = jaw_width_mm
- **Option C:** Hold pending catalog extraction
- **Recommended:** C_until_OEM_then_A
- **Why:** Numeric pattern alone is forbidden authority
- **Semantic risk:** MEDIUM if wrong dimension chosen
- **Future data work:** OEM page + property membership
- **Immediate unlock:** 0
- **Next blocker:** SOURCE_EVIDENCE_REQUIRED

## D-VBLOCK-01 — V_BLOCK (3 rows)

**Problem:** Weak OEM; one legacy name lacks identity; dimensions vs diameter range unclear

- **Option A:** Block dimensions (L×W×H) for sourced rows; hold 6890-702
- **Option B:** Workpiece diameter range as variant
- **Option C:** Hold all three for source
- **Recommended:** A
- **Why:** Do not weaken policy for all three because one row lacks evidence
- **Semantic risk:** MEDIUM
- **Future data work:** OEM extraction; possible NEW_PROPERTY for dimensions
- **Immediate unlock:** 0
- **Next blocker:** SOURCE_EVIDENCE_REQUIRED

## D-GENCAL-01 — GEN_CALIPER (65 rows)

**Problem:** Generic PT label; long-jaw / digital / vernier subfamilies under one code

- **Option A:** Keep GEN_CALIPER; canonical کولیس + required identity qualifiers; split LONG_JAW later
- **Option B:** Immediate PT split: LONG_JAW_CALIPER + keep residual GEN_CALIPER with qualifiers
- **Option C:** Map rows into existing specific PTs where OEM proves (none of HOOK/POINT here)
- **Recommended:** B
- **Why:** Approving کولیس alone hides taxonomy; OEM headings already distinguish long-jaw
- **Semantic risk:** HIGH if SAFE title-only
- **Future data work:** PT governance then measurement_range facts
- **Immediate unlock:** 0
- **Next blocker:** PRODUCT_TYPE_SPLIT

## D-BORE-01 — BORE_GAUGE (16 rows)

**Problem:** 3127-300 is three-point internal micrometer; residual bore gauges need one synonym-free title

- **Option A:** Reassign 3127-300 to INSIDE_MICROMETER; title residual as گیج داخل سیلندر
- **Option B:** Broad title covering micrometers + bore gauges (rejected)
- **Option C:** Hold all until OEM page closure
- **Recommended:** A
- **Why:** OEM heading DIGITAL TWO POINTS/THREE POINTS INTERNAL MICROMETERS is decisive
- **Semantic risk:** HIGH if one slash title
- **Future data work:** PT reassignment + measurement_range facts
- **Immediate unlock:** 0
- **Next blocker:** PRODUCT_TYPE_REVIEW

## D-OPTICAL-01 — OPTICAL_EDGE_FINDER (1 rows)

**Problem:** DIRECT_UNLOCK candidate lacks EXACT OEM identity

- **Option A:** Approve مرکزیاب نوری after EXACT OEM page proof
- **Option B:** Hold indefinitely until registry upgrade
- **Option C:** Reclassify product type if OEM proves non-optical
- **Recommended:** B_until_exact_then_A
- **Why:** Do not inflate direct unlock; Product.name is not authority
- **Semantic risk:** MEDIUM
- **Future data work:** OEM 108A/B extraction for 6566-2
- **Immediate unlock:** 0
- **Next blocker:** SOURCE_EVIDENCE_REQUIRED

