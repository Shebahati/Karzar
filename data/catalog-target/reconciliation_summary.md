# Target Catalog Reconciliation (READ-ONLY)

PRODUCTION MUTATION: **ZERO**. APPLY was not run and this tool has no apply path.

- Baseline SHA: `00266efd95efd4227350cc94ba8c27143e79d9da`
- Generated at: `2026-09-06T10:39:47.545212+00:00`
- DB evidence: **NON-LIVE / SNAPSHOT / UNAVAILABLE** (`unavailable`) — no_live_db_and_no_full_catalog_snapshot; refusing data/imports/*_products.csv (PDF parse, not site state) and image-only active-product extracts
- Current products observed: **0**
- Target SKUs: **0**

## A. Target source completeness
- Discovered files: 0
- Unparsed files: 0
- Unavailable registry sources: 26
- Duplicate-tree copies skipped: 0
- Duplicate source SKUs (identity collapsed, REVIEW): 0

## B. Current-site evidence completeness
- Kind: `unavailable` — **NON-LIVE / SNAPSHOT / UNAVAILABLE**
- Note: no_live_db_and_no_full_catalog_snapshot; refusing data/imports/*_products.csv (PDF parse, not site state) and image-only active-product extracts
- Current products observed: **0**

A and B are independent. A real Target manifest can exist without live site evidence.

## Target SKUs per brand
- (none — no authoritative product-scope files were available)

## Reconciliation counts
- KEEP: 0
- UPDATE: 0
- CREATE: 0
- DEACTIVATE: 0
- REVIEW: 0

## INSIZE
- Target SKU count: 0
- Unique SKU count: 0
- Exact matches to distributor workbook: 0
- Distributor rows seen (price/inventory join only): 0
- Universe expanded from distributor: False
- Unmatched target SKUs: 0
- (none)
- Duplicate matches: 0
- (none)
- Ambiguous matches: 0
- (none)
- Available + positive price: 0
- (none)
- Available + missing/zero price: 0
- (none)
- Unavailable + positive price: 0
- (none)
- Commerce-ready: 0
- (none)
- Unresolved identities: 0
- (none)

## Other findings (examples, not exhaustive)
- Duplicate current SKUs: 0
- (none)
- Duplicate target SKUs: 0
- (none)
- Cross-brand SKU collisions: 0
- (none)
- Active non-target products: 0
- (none)
- Target missing from current site: 0
- (none)
- Target with no valid price: 0
- (none)
- Target with no valid public image: 0
- (none)
- Category problems: 0
- (none)
- is_available=true with missing/non-positive price: 0
- (none)

## Unavailable authoritative sources
- `KARZAR_TARGET_SOURCE_DIR`: source_root_unset_or_missing
- `insize.product_list`: source_root_unavailable
- `insize.distributor`: source_root_unavailable
- `insize.catalog`: source_root_unavailable
- `terma.price_list`: source_root_unavailable
- `terma.catalog`: source_root_unavailable
- `dasqua.price_list`: source_root_unavailable
- `dasqua.catalog`: source_root_unavailable
- `guanglu.price_list`: source_root_unavailable
- `mitutoyo.catalog`: source_root_unavailable
- `dcoil.price_list`: source_root_unavailable
- `shams.catalog`: source_root_unavailable
- `ASTPOWER/chuck`: source_root_unavailable
- `ASTPOWER/tool_grinder`: source_root_unavailable
- `ASTPOWER/tailstock_rotary`: source_root_unavailable
- `ASTPOWER/magnetic_drill`: source_root_unavailable
- `ASTPOWER/et_taps`: source_root_unavailable
- `ASTPOWER/pneumatic_tapping`: source_root_unavailable
- `ASTPOWER/cutting_fluid`: source_root_unavailable
- `ASTPOWER/tapping_collets`: source_root_unavailable
- `ASTPOWER/automatic_tapping`: source_root_unavailable
- `ASTPOWER/electric_tapping`: source_root_unavailable
- `ASTPOWER/multi_spindle`: source_root_unavailable
- `ASTPOWER/magnetic_drill_hole_saws`: source_root_unavailable
- `ASTPOWER/utex_drills`: source_root_unavailable
- `ASTPOWER/spade_drills`: source_root_unavailable

## Unparsed sources
- (none)

## Parse failures / source conflicts
- (none)

## Existing tooling (do not delete in this task)
- `scripts/reconcile_prices_availability.py` — **unsafe_for_new_catalog_authority**: Global rule: positive base_price => is_available for ALL live products; price lists treated as membership.
- `scripts/import_price_lists.py` — **unsafe_for_new_catalog_authority**: Hardcoded developer Price dir; APPLY writes DB; price lists do not define Target membership.
- `scripts/insize_price_update.py` — **legacy**: Strips trailing letters (A/S) for matching; API writer; not Target-universe aware.
- `scripts/insize_sales_activation.py (PR #266, unmerged)` — **reusable_pieces_unsafe_as_authority**: Reusable: conservative normalize_sku, stdlib xlsx, rial/10, exact match, apply gates. Unsafe as Target authority: 10-SKU pilot allowlist must not define membership; APPLY exists.
- `scripts/azarsanat_import.py` — **legacy**: Placeholder 10_000_000 prices; infers brands/families beyond the approved AST folder set.
- `scripts/enrich_insize_from_shopmill.py` — **reusable**: Content-only enrichment; must not be used as product-scope membership.
- `data/imports/insize_products.csv / all_products.csv` — **legacy**: PDF price-list parse (~342 INSIZE rows). Not the approved ~872 product-list universe.
- `scripts/seed_products_from_csv.py` — **unsafe_for_new_catalog_authority**: Creates products from CSV; this task forbids CREATE/DELETE mutation.

## Storefront readiness
- `target_member`, `commerce_ready`, and `media_ready` are independent.
- `STOREFRONT_HIDE_IMAGELESS_PRODUCTS` defaults True: public catalog hides products without a valid non-placeholder image (`app/utils/public_catalog.py`).
- Images were not fabricated.

## APPLY readiness
- **Not ready.** This node is reconciliation/audit only.
- Future deactivation of out-of-scope products must be `is_active = false`, never DELETE.
- REVIEW rows must never auto-become UPDATE or CREATE.
- Do not merge or apply PR #266; its 10-SKU pilot is not Target membership.

