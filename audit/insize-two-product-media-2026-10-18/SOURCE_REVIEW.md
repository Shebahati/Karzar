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
- Prices: SUPERSEDED BY OWNER APPROVAL later on 2026-10-18. Owner confirmed 47,100,000 toman (1944) and 53,400,000 toman (3639) as ordinary prices; sale targets at 15% are 40,035,000 and 45,390,000 toman respectively. See OWNER_PRICE_SCOPED_APPLY.md. Production prices remain unchanged pending preflight/media and scoped APPLY; 3639 historic original_price=10 remains a live-inspection blocker.
- Production: no direct live DB/VPS access in this workflow. Need operator READ-ONLY snapshot for these IDs (ID, exact SKU, is_active, is_available, deleted_at, base_price, original_price, image count/URLs, updated_at and public storefront response). Gate: PENDING.
- No merge, deploy, image upload, price write, availability flip, SKU rename or Hesabfa side effect until the remaining gates pass and scoped APPLY/rollback is approved.

## Exact-SKU web photo shortlist — 2026-10-18 (reference links, not uploaded files)

- Product 1944 / stored SKU 3203-1506 / manufacturer variant 3203-1506A:
  - Exact six-piece merchant page: https://mytools.co.nz/products/insize-micrometer-ext-set-0-150-x001mm
  - Page-linked 1000px candidate: https://mytools.co.nz/cdn/shop/files/75da86510101769587cf205f30d0d432_f8a22e28-8ab5-42f2-b54a-d7edb50140e5.jpg?v=1754347448&width=1000
  - Alternate page-linked photo: https://mytools.co.nz/cdn/shop/files/ef079ae14ca0c9461b71baa234d1fce1.jpg?v=1754347448&width=1000
  - Exact SKU seller page with indexed main image: https://www.cutwel.co.uk/0-150mm-metric-outside-micrometer-set-3203-series-insize-3203-1506a
  - Avoid manufacturer 3203 PDF case photos labelled 1004A and 3006A.
- Product 3639 / stored SKU S3-2824 / official variant 2824-S3:
  - Exact 3-piece dial bore gauge merchant page: https://www.cutwel.co.uk/18-160mm-bore-gauge-set-series-3-piece-2824-series-insize-2824-s3
  - Current page-indexed main image: https://www.cutwel.co.uk/media/catalog/product/2/8/2824-INSIZE-SET-1_1_1.jpg
  - Backup exact-code product gallery explicitly describing the green case: https://organametrisis.gr/en/products/2824-s3-kylindrometra-set-3-temaxiwn-18-160-mm
  - Manufacturer catalogue matches packaging with code 2824-S3; do not substitute 2824-S160 or digital 2724-S3.
- Selection: these are exact-SKU source-page leads and direct-image URLs where indexed. The remote media hosts refused direct binary retrieval in this environment. Therefore no byte-size, hash, image-dimension, storefront permission, or production upload is claimed. Obtain/use original assets via an authorized supplier/manufacturer channel. Do not hotlink external merchant CDNs into the live product gallery.

## Actual user-provided binary review — 2026-10-18

Owner uploaded `karzar_insize_media_20261018.tar.gz` (manifest + two Cutwel-source
1600x1600 WebP images). The SHA-256 of both images **matches** the
download manifest; both files decode successfully. Owner explicitly attested
commercial-use rights.

- ID 1944 / 3203-1506 / OEM 3203-1506A: source
  `1944_cutwel.webp`, SHA-256
  `21012d0be4dc8cbdbd7bb9cd94bf2c08e1bb35a3672cdb6fd741c576dc60f80f`.
  **REJECTED** by actual pixel review: opened case visibly contains FOUR
  micrometers, not the owner's SIX-piece 0–150 mm kit. Exact product page
  title is not sufficient proof of the photo. DO NOT PUBLISH this binary
  for ID 1944. Replacement exact-SKU lead:
  https://partineh.com/p/87525 ; indexed original photo URL:
  https://partineh.com/upload/images/2023/%D8%B3%D8%AA-%D9%85%DB%8C%DA%A9%D8%B1%D9%88%D9%85%D8%AA%D8%B1-%D8%A7%DB%8C%D9%86%D8%B3%D8%A7%DB%8C%D8%B2-%D9%85%D8%AF%D9%84-1506-3203.jpg .
  Its actual bytes not yet retrieved/reviewed.
- ID 3639 / S3-2824 / OEM 2824-S3:
  `3639_cutwel_main.webp`, SHA-256
  `db18cd1a9b181bcd70297ca574f96afc37af7598a698c13100c71aff425479fc`.
  **VISUALLY ACCEPTED**: photo contains fitted case, three analog dial bore
  gauge assemblies and accessories, matching the 18–160 mm three-piece set.
  Original source bytes preserved for a 1600x1600 WebP hero; a 640x640 WebP
  thumbnail derived without retouching. Output package for user:
  `karzar_insize_verified_media_20261018.zip` (local chat artifact, not
  uploaded to repository/server).

This review does not authorize database APPLY, deployment, or account sync.

## Final second-source uploaded image review — 2026-10-18 (supersedes prior ID 1944 media hold)

Owner uploaded `insize-1944.tar.gz`, containing two working exact-SKU
Rubutek files. Both decode successfully and passed image-integrity
inspection:
- `photo1.png`: 750x750 RGBA (fully opaque), SHA-256
  `20a113b88fc75833ced2a98f0617099565864e98bfcb69ec25350562e63a744f`.
  Actual pixel inspection reveals **six micrometers** in the open green kit.
  This is visually consistent with the owner's six-piece 0–150 mm kit.
  Source: https://www.rubutek.com/image/cache/catalog/product-07/3203-1506A-750x750.png
- `photo2.jpg`: 750x750 JPEG, SHA-256
  `802650d6f859d19856b23ce87fd85c1b4d7abed3d3858db8640462578bc5edb7`.
  A source reference table identifies `3203-1506A`, 0–150 mm, with
  components 3203-25A/50A/75A/100A/125A/150A; **not** selected as public hero.

Prepared production-ready media locally, without upscaling or object alteration:
- ID 1944 `1944_3203-1506A_hero.webp` 750x750, SHA-256
  `a459bd11a045aeb430944d59015ec401fa481a0162a2cad31724c3d4099f33bd`;
  thumbnail 480x480 SHA-256
  `318ff65f95a1906ba71afabe01a8c26b8cb3bd77fd44ccb5dc18bec407199609`.
- ID 3639 `3639_S3-2824_hero.webp` 1600x1600, SHA-256
  `db18cd1a9b181bcd70297ca574f96afc37af7598a698c13100c71aff425479fc`;
  thumbnail 640x640 SHA-256
  `ff087c4fe9a0663807fe3d4c530ec3a1586d5c1fb3e44d1c33d9df5a9a4af7d9`.

The two-product local archive `karzar_insize_media_final_20261018.zip` passed
archive CRC and SHA-256 verification (archive SHA-256
`52394c679c3af6a4deebc7ac9b2b5598dbbdecfc68872ff18e9831e9468abf35`);
it includes only selected hero/thumb assets, original ID 1944 source, exact-SKU
reference table, README and JSON provenance manifest. The **rejected four-piece
Cutwel image is NOT in this archive**. Owner attested commercial-use rights.
**MEDIA_READY_LOCAL_BOTH / PRODUCTION_IMAGE_UPLOAD=NO / DB_MUTATION=NO**.
