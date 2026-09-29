# Product Naming v1 — Audit Summary

**Mode:** READ-ONLY / APPLY disabled
**Engine:** `karzar_product_naming_v1`
**Snapshot products:** 1368
**product_type_governed:** always `False` (not in public API) → RENAME_SAFE confidence ≤ MEDIUM

## State census

| State | Count | Share |
|-------|------:|------:|
| `HOLD_MISSING_PRODUCT_TYPE` | 771 | 56.4% |
| `RENAME_SAFE` | 508 | 37.1% |
| `HOLD_MISSING_VARIANT_ATTRIBUTE` | 85 | 6.2% |
| `HOLD_IDENTITY_CONFLICT` | 3 | 0.2% |
| `HOLD_MISSING_MANUFACTURER_CODE` | 1 | 0.1% |

## Confidence (RENAME_SAFE / EXACT)

| Confidence | Count |
|------------|------:|
| `none` | 860 |
| `medium` | 255 |
| `low` | 253 |

## Length stats

- Current names: n=1368 min=10 median=50 max=81 avg=49.8
- Proposed names: n=508 min=28 median=44 max=55 avg=43.8

## SEO impact

- `meta_title` blank: **682** (49.9%)
- SERP title would change on rename (blank meta + different proposed): **280**

## Brands in snapshot

- INSIZE | اینسایز: 643
- TERMA | ترما: 181
- ZCC.CT | زد سی‌سی: 175
- ASTPOWER | ای اس تی پاور: 143
- Mitutoyo | میتوتویو: 111
- SAN OU | سانو: 62
- Dasqua | داسکوا: 53

## Profiles selected

- `generic.v1`: 771
- `metrology.micrometer.v1`: 229
- `metrology.caliper.v1`: 176
- `cutting.turning_insert.v1`: 129
- `workholding.chuck.v1`: 31
- `toolholding.holder.v1`: 23
- `cutting.solid_tool.v1`: 9

## Collisions

- Duplicate proposed_name groups: **0**
- Same brand+manufacturer_code groups: **1**
  - ASTPOWER / `TU-DR230 ASTPOWER` → ids [3411, 3409]

## Example proposals / holds

### pilot_1108-150
- id/sku: `1785` / `1108-150`
- brand: INSIZE | اینسایز
- current: کولیس دیجیتال 15سانت اینسایز مدل 1108-150
- proposed: کولیس دیجیتال اینسایز کد 1108-150، 0–150 میلی‌متر
- state/confidence: `RENAME_SAFE` / `medium`
- profile / PT: `metrology.caliper.v1` / کولیس دیجیتال
- OEM code: `1108-150` (evidence: specs.official_model)

### pilot_1108-200
- id/sku: `1786` / `1108-200`
- brand: INSIZE | اینسایز
- current: کولیس دیجیتال 20سانت اینسایز مدل 1108-200
- proposed: کولیس دیجیتال اینسایز کد 1108-200، 0–200 میلی‌متر
- state/confidence: `RENAME_SAFE` / `medium`
- profile / PT: `metrology.caliper.v1` / کولیس دیجیتال
- OEM code: `1108-200` (evidence: specs.official_model)

### pilot_1108-300
- id/sku: `1787` / `1108-300`
- brand: INSIZE | اینسایز
- current: کولیس دیجیتال 30سانت اینسایز مدل 1108-300
- proposed: کولیس دیجیتال اینسایز کد 1108-300، 0–300 میلی‌متر
- state/confidence: `RENAME_SAFE` / `medium`
- profile / PT: `metrology.caliper.v1` / کولیس دیجیتال
- OEM code: `1108-300` (evidence: specs.official_model)

### zcc_insert
- id/sku: `7268` / `ZCC-WCMX030208R-53-YBG205`
- brand: ZCC.CT | زد سی‌سی
- current: الماس سوراخکاری ZCC مدل WCMX030208R-53 YBG205
- proposed: اینسرت تراشکاری ZCC.CT کد WCMX030208R-53 YBG205
- state/confidence: `RENAME_SAFE` / `medium`
- profile / PT: `cutting.turning_insert.v1` / اینسرت تراشکاری
- OEM code: `WCMX030208R-53 YBG205` (evidence: name_label)

### zcc_holder
- id/sku: `7285` / `ZCC-PTTNL2525M22`
- brand: ZCC.CT | زد سی‌سی
- current: هلدر رو تراش ZCC مدل PTTNL2525M22 برای الماس TN▢▢22
- proposed: هلدر تراش ZCC.CT کد PTTNL2525M22
- state/confidence: `RENAME_SAFE` / `medium`
- profile / PT: `toolholding.holder.v1` / هلدر تراش
- OEM code: `PTTNL2525M22` (evidence: specs.model)

### san_ou_chuck
- id/sku: `4370` / `SO-13539`
- brand: SAN OU | سانو
- current: سه نظام آچاری مته قدرت باال J2106H B10 (0.6-6MM) سانو (SAN OU)
- proposed: سه‌نظام منظم سانو کد SO-13539، 6 میلی‌متر
- state/confidence: `RENAME_SAFE` / `low`
- profile / PT: `workholding.chuck.v1` / سه‌نظام منظم
- OEM code: `SO-13539` (evidence: sku_as_candidate)

### mitutoyo
- id/sku: `2411` / `938882`
- brand: Mitutoyo | میتوتویو
- current: باتری میتوتویو مدل 938882
- proposed: —
- state/confidence: `HOLD_MISSING_PRODUCT_TYPE` / `none`
- profile / PT: `generic.v1` / —
- OEM code: `938882` (evidence: name_label)

### dasqua
- id/sku: `1701` / `8203-0010`
- brand: Dasqua | داسکوا
- current: سختی‌سنج شور داسکوا 0-100mm کد 8203-0010
- proposed: —
- state/confidence: `HOLD_MISSING_PRODUCT_TYPE` / `none`
- profile / PT: `generic.v1` / —
- OEM code: `8203-0010` (evidence: name_label)

### terma
- id/sku: `4692` / `IB210N-100`
- brand: TERMA | ترما
- current: ساعت اندیکاتور کورس 10سانت ترما (TERMA) مدل IB210N-100
- proposed: —
- state/confidence: `HOLD_MISSING_PRODUCT_TYPE` / `none`
- profile / PT: `generic.v1` / —
- OEM code: `IB210N-100` (evidence: name_label)

### astpower
- id/sku: `6587` / `AST-COR305P`
- brand: ASTPOWER | ای اس تی پاور
- current: مدل AST-COR305P
- proposed: —
- state/confidence: `HOLD_MISSING_PRODUCT_TYPE` / `none`
- profile / PT: `generic.v1` / —
- OEM code: `AST-COR305P` (evidence: name_label)

### missing_pt
- id/sku: `7275` / `ZCC-ZSD05-400-XP40-SP11-02`
- brand: ZCC.CT | زد سی‌سی
- current: مته الماس خور ZCC مدل ZSD05-400-XP40-SP11-02
- proposed: —
- state/confidence: `HOLD_MISSING_PRODUCT_TYPE` / `none`
- profile / PT: `generic.v1` / —
- OEM code: `ZSD05-400-XP40-SP11-02` (evidence: specs.model)

### identity_conflict
- id/sku: `1871` / `1530-300`
- brand: INSIZE | اینسایز
- current: کولیس دیجیتال اینسایز (Insize) 30 سانتی متر داخل و خارج سنج مدل 300-1530
- proposed: —
- state/confidence: `HOLD_IDENTITY_CONFLICT` / `none`
- profile / PT: `metrology.caliper.v1` / کولیس دیجیتال
- OEM code: `` (evidence: conflict)

### manual_review
_no example captured_

## Blockers for APPLY

1. `product_type_id` not exposed on public ProductDetail — all PT matches are provisional terminology.
2. No first-class `products.manufacturer_code` column (see SCHEMA_IDENTITY_REVIEW.md).
3. HOLD counts must be cleared or overridden before any rename wave.
4. Brand display governance incomplete (ASTPOWER + non-live brands NEEDS_GOVERNANCE).
5. This script never enables APPLY — Phase 0/1 audit only.

## Artifact paths

- `audit/product-naming-v1/PRODUCT_NAMING_CENSUS.csv`
- `audit/product-naming-v1/PRODUCT_NAMING_PROPOSALS.csv`
- `audit/product-naming-v1/PRODUCT_NAMING_HOLDS.csv`
- `audit/product-naming-v1/SEO_IMPACT_REPORT.csv`
- `audit/product-naming-v1/PRODUCT_NAMING_SUMMARY.md`
- `audit/product-naming-v1/BRAND_DISPLAY_REGISTRY.csv`
- `audit/product-naming-v1/PRODUCT_TYPE_NAMING_PROFILES.csv`
- `audit/product-naming-v1/NAMING_TERMINOLOGY_REGISTRY.csv`
- `audit/product-naming-v1/PRODUCT_NAME_WRITERS.md`
- `audit/product-naming-v1/SCHEMA_IDENTITY_REVIEW.md`
