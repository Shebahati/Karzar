# PROMPT 126 RESULT — INSIZE SKU Identity / Suffix Resolution Audit

**STATUS:** COMPLETE (READ-ONLY)  
**VERDICT:** READY_TO_SCALE_SPECIALTY_INGESTION  
**DATE:** 2026-09-26  
**MODE:** Read-only forensic data audit — no Live mutation

## BASELINE (live verified)

| Field | Value |
|------|--------|
| Main SHA | `76ef7b254396e4c742c634d4c81837d5eacaa4f8` |
| Deployed SHA | `76ef7b254396e4c742c634d4c81837d5eacaa4f8` |
| Alembic | `s2t3u4v5w6x7` |
| Plane / Freeze | live / true |
| GEN_CALIPER | 72 |
| DEPTH_GAUGE | 4 |
| INTERNAL_GROOVE_CALIPER | 5 |
| Facts / Published / Links / Revisions | 243 / 243 / 243 / 486 |
| Product Types | 3 |
| Governed products | 81 |
| Waves 001–007 | Published |

## HOLD UNIVERSE

**Total:** 14 products (Prompt 121 HOLD rows still ungoverned)

| Family | SKUs |
|--------|------|
| INTERNAL_GROOVE_CALIPER | 1120-150, 1120-200, 1120-300 |
| INTERNAL_POINT_CALIPER | 1121-150 |
| EXTERNAL_GROOVE_CALIPER | 1185-150, 1187-150 |
| INSIDE_KNIFE_EDGE_CALIPER | 1123-150, 1123-300 |
| TUBE_THICKNESS_CALIPER | 1161-150 |
| POINT_CALIPER | 1183-150 |
| OFFSET_CALIPER | 1186-150, 1186-200, 1186-300 |
| BLADE_CALIPER | 1188-150 |

All 14: `product_type_id=NULL`, Facts=0, Wave membership=0.

## IDENTITY RESULTS (product-level)

| Class | Count | Products |
|-------|------:|----------|
| RESOLVED_EXACT | 1 (from HOLD) + 4 already-exact ready | HOLD: **1123-300**; Ready: 1122-300, 1169-150, 1530-300, 1530-500 |
| RESOLVED_EQUIVALENT_FACTS | 13 | all other HOLDs |
| TRUE_HOLD (`HOLD_MULTIPLE_FACT_SETS` unresolved) | **0** | — |
| SOURCE_CONFLICT | **0** | — |

Excluded multi-fact OEM variants (B/*1/P) are listed in the matrix as `HOLD_MULTIPLE_FACT_SETS_EXCLUDED_VARIANT` — they are not live DB products.

## INTERNAL_GROOVE 1120

### 1120-150 (1795)
- **Candidates (OEM):** 1120-150A, 150AWL, 150B, 1501, 1501WL, 150P
- **Image:** IDENTIFYING — beam mark **≥22mm**; buttons include **SET**; no wireless module visible
- **Exclusions:** B (50–150 ±0.06), 1501 (35–150 ±0.06), P/Type C (different buttons; no SET)
- **Remaining:** A / AWL — identical V1 triad **22–150 / 0.01 / ±0.04**
- **Classification:** RESOLVED_EQUIVALENT_FACTS
- **Safe to ingest V1:** **YES**
- **Reason:** After positive exclusions, all remaining plausible variants share INTERNAL_GROOVE PT + identical required Facts; A vs AWL is wireless-only

### 1120-200 (1796)
- **Candidates:** 200A, 200AWL, 200B, 2001, 2001WL
- **Image:** ABSENT
- **Legacy:** accuracy ±0.04 + buttons include **set** → Type A class; excludes B/*1
- **Remaining:** A / AWL — triad **25–200 / 0.01 / ±0.04**
- **Classification:** RESOLVED_EQUIVALENT_FACTS
- **Safe to ingest V1:** **YES**

### 1120-300 (1797)
- **Candidates:** 300A, 300AWL, 300B, 3001, 3001WL
- **Image:** ABSENT
- **Legacy dims:** L=410, b=15, c=16, d=50, e=1.5 — UNIQUE_MATCH Type A geometry (excludes B/*1)
- **Remaining:** A / AWL — triad **30–300 / 0.01 / ±0.05**
- **Classification:** RESOLVED_EQUIVALENT_FACTS
- **Safe to ingest V1:** **YES**

## OTHER HOLD RESULTS

| SKU | ID | Family | Candidates | Fact equivalence | Classification | Safe V1 |
|-----|---:|--------|------------|-----------------|----------------|---------|
| 1121-150 | 1799 | INTERNAL_POINT | A/AWL (B/*1 excluded by image **+24mm** + acc) | 24–150 / 0.01 / ±0.04 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1185-150 | 1835 | EXTERNAL_GROOVE | A/AWL only | 0–150 / 0.01 / ±0.04 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1187-150 | 1839 | EXTERNAL_GROOVE (neck) | A/AWL only | 0–150 / 0.01 / ±0.04 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1123-150 | 1801 | INSIDE_KNIFE_EDGE | A/AWL only | 15–150 / 0.01 / ±0.05 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1123-300 | 1802 | INSIDE_KNIFE_EDGE | **300A sole** | 24–300 / 0.01 / ±0.06 | **RESOLVED_EXACT** | YES |
| 1161-150 | 1827 | TUBE_THICKNESS | A/AWL only | 0–150 / 0.01 / ±0.05 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1183-150 | 1834 | POINT | A/AWL only | 0–150 / 0.01 / ±0.03 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1186-150 | 1836 | OFFSET | A/AWL only | 0–150 / 0.01 / ±0.04 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1186-200 | 1837 | OFFSET | A/AWL only | 0–200 / 0.01 / ±0.04 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1186-300 | 1838 | OFFSET | A/AWL only | 0–300 / 0.01 / ±0.05 | RESOLVED_EQUIVALENT_FACTS | YES |
| 1188-150 | 1840 | BLADE | A/AWL only | 0–150 / 0.01 / ±0.03 | RESOLVED_EQUIVALENT_FACTS | YES |

Notes:
- Do **not** collapse EQUIVALENT into EXACT — DB SKU remains bare; evidence locator should cite preferred non-WL OEM code (usually `*A`).
- 1188 image is NON_DIAGNOSTIC for A vs AWL (and visually ambiguous for blade geometry); OEM page still governs family.

## EXACT READY (not yet governed)

| SKU | ID | Product Type | OEM Facts | Blocker |
|-----|---:|--------------|-----------|---------|
| 1122-300 | 1800 | HOOK_CALIPER | 4–300 / 0.01 / ±0.04 · pdf79 | none (identity exact) |
| 1169-150 | 1828 | POINT_CALIPER | 0–150 / 0.01 / ±0.03 · pdf71 | none |
| 1530-300 | 1871 | INTERCHANGEABLE_POINT_CALIPER | 0–300 / 0.01 / ±0.06 · pdf61 | none |
| 1530-500 | 1872 | INTERCHANGEABLE_POINT_CALIPER | 0–500 / 0.01 / ±0.08 · pdf61 | none |
| 1123-300 | 1802 | INSIDE_KNIFE_EDGE_CALIPER | 24–300 / 0.01 / ±0.06 · pdf73 | sole OEM `1123-300A` |

## FACT-SAFE BUT IDENTITY-UNRESOLVED

All 13 EQUIVALENT_FACTS HOLDs above.

**Why safe for V1:** every remaining plausible OEM variant shares (1) same proposed Product Type, (2) identical measurement_range/resolution/accuracy, (3) OEM page Resolution 0.01 digital. Suffix residual is wireless (WL/AWL) or (for 1120-150 historically) IP features already excluded.

**Why not EXACT:** DB SKU string ≠ single OEM code; do not rewrite SKU.

## TRUE HOLD

**None** remaining for required V1 triad after evidence filters.

Blocking evidence that *would* be required if filters were unavailable: printed model suffix, wireless module confirmation, or Type B vs A jaw photo for 1120/1121.

## IDENTITY ARCHITECTURE

| Question | Answer |
|----------|--------|
| Persistent mapping needed now? | **NO** (not blocking) |
| Recommended mechanism | Keep decisions in audit/planning artifacts + cite preferred OEM `model` in Evidence locator; optionally later add `product_source_identity` / OEM-alias table when volume ≫ tens |
| Why sufficient | Fact Evidence already stores OEM row locator; identity *decision* for EQUIVALENT cases is a governance/provenance note, not a new Fact path |
| Identity vs Fact provenance | Distinct: identity = “DB product ↔ OEM commercial variant”; Fact = “value ↔ OEM table cell”. Evidence link alone does not record why A was preferred over AWL — document in wave `change_reason` / audit matrix |

## NEXT INGESTION ORDER

1. **INTERCHANGEABLE_POINT_CALIPER** PT + wave — 2 EXACT (1530-300/500)
2. **HOOK_CALIPER** PT + wave — 1 EXACT (1122-300)
3. **POINT_CALIPER** PT + wave — 1 EXACT (1169-150) [+ later 1183 EQUIVALENT]
4. **INTERNAL_GROOVE Wave008** — 3 FACT_SAFE (1120-150/200/300) under EQUIVALENT policy
5. **INSIDE_KNIFE_EDGE_CALIPER** PT — 1123-300 EXACT + 1123-150 EQUIVALENT
6. **INTERNAL_POINT_CALIPER** PT — 1121-150 EQUIVALENT
7. **EXTERNAL_GROOVE_CALIPER** PT — 1185/1187 EQUIVALENT
8. **OFFSET_CALIPER** PT — 1186-150/200/300 EQUIVALENT
9. **TUBE_THICKNESS_CALIPER** PT — 1161-150 EQUIVALENT
10. **BLADE_CALIPER** PT — 1188-150 EQUIVALENT

Each new PT: Definition V1 = triad only; expected Facts = 3 × cohort size; no new dictionary/migration/code.

## ARTIFACTS

- `audit/insize-phase8/SKU_IDENTITY_MATRIX.csv`
- `audit/insize-phase8/SUFFIX_SEMANTICS.md`
- `audit/insize-phase8/READY_SPECIALTY_PRODUCTS.csv`
- `audit/insize-phase8/PROMPT_126_RESULT.md`

## WRITES

DB / API / JSONB / Deploy / Migration / Code: **NONE**

## VERDICT

**READY_TO_SCALE_SPECIALTY_INGESTION**

STOP. Do not mutate any product. Do not create Product Types or Waves.
