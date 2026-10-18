# INSIZE 1944 / 3639 — precise media source review
Date: 2026-10-18. Status: SOURCE_DISCOVERY_COMPLETE / BINARY_VALIDATION_PENDING / NO_PRODUCTION_WRITE.

## Owner-confirmed availability
Owner confirmed both products are physically available on 2026-10-18. This is a confirmation of availability, NOT of numeric stock count, active flags, or current production prices. No mutation to Hesabfa or catalogue undertaken by this source review.

## Product ID 1944
- Site SKU: `3203-1506`. Historical 2026-09-30 catalogue row: six outside micrometers, 0–150 mm; 2026-10-13 identity/source mapping associates family with `3203-1506A`.
- Manufacturer official present-day 3203 series: https://www.insize.com/verniermicrometers/3203.html ; official PDF https://www.insize.com/PDF/3203.pdf explicitly lists `3203-1506A (Set)`, 0–150 mm, six instruments: 3203-25A/50A/75A/100A/125A/150A in blow-mould case.
- Matching SKU-specific merchant media candidate (not yet downloaded/pixel-verified): https://www.cutwel.co.uk/0-150mm-metric-outside-micrometer-set-3203-series-insize-3203-1506a ; merchant indexed primary image URL https://www.cutwel.co.uk/media/catalog/product/3/2/3203-INSIZE-METRIC-SET-1_1_37.jpg .
- Additional matching variant product photos: https://www.mmc.net.br/produto/micrometro-externo-insize-0-a-150mm-x-0-01mm-jogo-com-6-pcs-3203-1506a-5307 .
- Iranian product listing https://partineh.com/p/87525 expressly says reproduction of its content is only for non-commercial use with attribution; DO NOT reuse its image commercially without permission.
- Do NOT substitute catalog pictures of `3203-1004A` (4 instruments) or `3203-3006A` (150–300 mm) for this 6-instrument 0–150 mm product.
- Need visually confirm stock box is 3203-1506 vs 3203-1506A equivalent, and exact six-item layout.

## Product ID 3639
- Stored site SKU: `S3-2824`; intended official manufacturer order: **`2824-S3`**. Do not rename site SKU via media work.
- Official manufacturer product page https://www.insize.com/boregauges/2824.html lists `2824-S3`: 18–160 mm, dial indicator version. Official operation instruction https://m.insize.com/upfiles/sms/MN-2824-E%20V1.pdf labels `2824-S3` packaging, with three gauges: 18–35, 35–60, 50–160 mm (dial 2308-10FA). No substitute `2824-S160` or digital `2724-S3`.
- SKU-specific merchant gallery: https://www.cutwel.co.uk/18-160mm-bore-gauge-set-series-3-piece-2824-series-insize-2824-s3 ; indexed primary image candidate (not downloaded or pixel-verified) https://www.cutwel.co.uk/media/catalog/product/2/8/2824-INSIZE-SET-1_1.jpg .
- Additional exact-SKU merchant gallery https://wallersindustrialonline.com/products/insize-bore-gauge-set396 and https://www.insz.hu/merooras-furatmerok/analog-merooras-furatmero-3-reszes-keszlet-18-160-0-01-mm-insize/ .
- Historical commercial snapshot 2026-10-13: original_price=10 (invalid), base_price=53,400,000; source mapping NOT_FOUND / price-clear hold. Availability confirmation does NOT validate this historical price.

## Media acceptance / legal / production gate
1. Before attachment, fetch original image bytes from authorized manufacturer/reseller channel and verify HTTP 200, image mime, resolution, integrity hash, no watermarks, no irrelevant overlay, correct complete kit and actual physical stock packaging. Direct download from discovery environment did not succeed; DO NOT claim image files are already prepared.
2. Obtain supplier/manufacturer reuse permission for commercial storefront use; merchant gallery photos are not presumed freely licensed.
3. Use a real hero product image and accurate alt text per exact product. Avoid AI-generated products and wrong variants.
4. Read-only production product/image/price/stock preflight must confirm IDs, current values and source applicability; image upload and 15% price updates require distinct authorized, auditable production APPLY. No live actions in this PR.

## 2026-10-18 visual source cross-check
- Rendered page 1 of the manufacturer's 3203 PDF. It lists 3203-1506A in the table, but the two case photos on that page are *explicitly labelled* 3203-1004A and 3203-3006A. Neither image is evidence for 3203-1506A; never crop either as the hero for product 1944.
- The Cutwel 3203-1506A page has a contradictory generic attribute ("Number of Measuring Heads: 4") even though the exact SKU is a **six-piece micrometer kit**. Its primary media candidate remains unapproved pending direct visual identity check.
- Official manufacturer 2824 page distinguishes analog 2824-S3 from 2824-S160 and digital 2724-S3. Product 3639 hero must show the **three-piece 18–160 mm analog kit**.
- Official and reseller photography is copyright-protected absent license. Preferred acquisition: have the owner photograph the actual two stocked boxes/kits, or obtain original image assets plus written storefront-use permission directly from the authorized INSIZE supplier.

## Current release gates (2026-10-18)
- PR #529 at `fc9e4893b723fd26aaff0fca98d5faead3ed690e`: Frontend CI (including admin-panel typecheck/lint/tests), Backend CI, CI Workflow Lint, Collaborator Scope Gate all SUCCESS. Frontend storefront and storefront-e2e were classifier-skipped; do not misrepresent them as executed.
- Images: candidate source pages found; no authenticated binary asset ingested yet, no license verified. Gate: BLOCKED.
- Stock: owner confirms available for both on 2026-10-18, no numeric count represented. Gate: OWNER_CONFIRMED.
- Prices: no current, approved pre-discount price for either product as of this review. Historic 36,724,800 (1944) and 53,400,000 (3639) toman are NOT current approval; do not calculate/apply production sale prices from them. 3639's historic original_price=10 must be explicitly inspected and corrected from approved data. Gate: BLOCKED.
- Production: no direct live DB/VPS access in this workflow. Need operator READ-ONLY snapshot for these IDs (ID, exact SKU, is_active, is_available, deleted_at, base_price, original_price, image count/URLs, updated_at and public storefront response). Gate: PENDING.
- No merge, deploy, image upload, price write, availability flip, SKU rename or Hesabfa side effect until the remaining gates pass and scoped APPLY/rollback is approved.
