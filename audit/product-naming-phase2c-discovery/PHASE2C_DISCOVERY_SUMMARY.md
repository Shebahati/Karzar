# Phase 2C Discovery Summary

> **Coverage: STALE_STATUS_MASTER_PARTIAL** — not a live SQL export.
> Live full-catalog manufacturer_code census is **BLOCKED** (see `LIVE_EXPORT_BLOCKER.json`).
> `BACKFILL_EXACT=0` is intentional without Tier 1–3 evidence registry.

- Source: `audit/product-status-2026-09-24/KARZAR_PRODUCT_STATUS_MASTER_2026-09-24.csv`
- Source SHA256: `73535d856d302a8941c34846e131da72b906d9485978e9e695f7c5051bf2262e`
- Rows (non-deleted): **6536**
- Reconciliation: **PASS**
- Collision groups: **5**
- Reversed-code conflicts: **2707**

## Primary classification

- BACKFILL_EXACT: 0
- MANUAL_REVIEW: 0
- HOLD_WEAK_EVIDENCE: 3821
- HOLD_IDENTITY_CONFLICT: 2707
- HOLD_MISSING: 0
- HOLD_BRAND_AMBIGUOUS: 0
- HOLD_DUPLICATE_IDENTITY: 8
- REVIEW_EXISTING_CANONICAL: 0

## Top brands by product count

- ASTPOWER | ای اس تی پاور: products=975 weak=508 conflict=465 dup=2
- INSIZE | اینسایز: products=872 weak=258 conflict=614 dup=0
- Dasqua | داسکوا: products=727 weak=727 conflict=0 dup=0
- ZCC.CT | زد سی‌سی: products=583 weak=0 conflict=583 dup=0
- TIGER TEC | تایگرتک: products=517 weak=517 conflict=0 dup=0
- YOWAX | یواکس: products=353 weak=0 conflict=353 dup=0
- Chumpower | چام‌پاور: products=347 weak=347 conflict=0 dup=0
- SAN OU | سانو: products=317 weak=266 conflict=51 dup=0
- TERMA | ترما: products=312 weak=312 conflict=0 dup=0
- Mitutoyo | میتوتویو: products=304 weak=91 conflict=211 dup=2
- [NO BRAND]: products=295 weak=294 conflict=1 dup=0
- ASIMETO | آسیمتو: products=235 weak=234 conflict=1 dup=0
- ET | ای تی: products=227 weak=0 conflict=227 dup=0
- Mighty Seven | مایتی سون: products=182 weak=11 conflict=171 dup=0
- Groz | گروز: products=127 weak=127 conflict=0 dup=0

## Identity collisions (brand + candidate)

- ASTPOWER / `TU-DR230 ASTPOWER` → n=2 ids=3409|3411
- MITUTOYO / `103-147` → n=2 ids=2182|2353
- MITUTOYO / `147-103` → n=2 ids=2182|2353
- SHAMS / `M16*1.5 — بسته ۱۰۰ عددی برند شمس(SHAMS)` → n=2 ids=4171|4172
- SHAMS / `M6*1 برند شمس(SHAMS)` → n=2 ids=4177|4184

## Safety

- manufacturer_code writes: **0**
- Product.name writes: **0**
- `--apply`: rejected
- Phase 2D/2E: **not started**

## Next requirement for authoritative 2C

1. Place agent on private worker `hp-g2-450` (or provide SSH to VPS).
2. Export live non-deleted products CSV with `manufacturer_code` + PT fields.
3. Hash Tier 1–3 OEM source files under Product and Data Complete.
4. Re-run discovery with `--products-csv` + `--evidence-registry`.

