# Two-product owner-confirmed pricing and gated rollout (2026-10-18)

Status: **OWNER_PRICE_APPROVED / STOCK_CONFIRMED / LIVE_PREFLIGHT_PENDING / MEDIA_BINARY_PENDING / APPLY_NOT_EXECUTED**.
This is a plan and immutable price intent, **not production write authorization**.
Scope locked to existing product IDs `1944` and `3639`. No inferred lookup by fuzzy name or reverse SKU may add other rows.

## Owner-approved ordinary prices and deterministic 15% discounts (unit: toman)

| product_id | CURRENT STORED SKU EXPECTATION | original_price (ordinary) | 15% reduction | base_price (sale) |
|---|---|---:|---:|---:|
| 1944 | 3203-1506 | 47,100,000.00 | 7,065,000.00 | **40,035,000.00** |
| 3639 | S3-2824 | 53,400,000.00 | 8,010,000.00 | **45,390,000.00** |

`2824-S3` is the manufacturer's listing order for site SKU `S3-2824`; SKU must **not** be renamed in this operation. Earlier historical `original_price=10` for 3639 is invalid; owner-approved ordinary price replaces it only after a fresh read-only snapshot confirms row identity and no unreviewed drift. Owner confirmed real availability for **both** products on 2026-10-18; no numeric inventory claim and no automatic supplier-wide availability update.

## Preflight: all gates must be PASS before any production write

1. Freeze exact `main` and deployed application SHA and product/image DB snapshot timestamp. PR #529 includes the admin calculator and this evidence, not a permission to merge/deploy/apply. Check latest HEAD CI *after* the last documentation/test commit.
2. Fetch production product ID 1944 and 3639 under read-only DB transaction. Record exact SKU, manufacturer code, brand, slug, `deleted_at`, `updated_at`, `is_active`, `is_available`, `base_price`, `original_price`, category, primary image and every image ID/URL, and public PDP result. Abort if IDs/identity/brand differ, soft-deleted, duplicate, or concurrent revision changes.
3. Media: original full-resolution binaries must be positively matched to physically stocked six-piece 0–150 mm micrometer kit and analog three-piece 18–160 mm bore-gauge kit. Verify provenance, storefront commercial permission, checksum, resolution, file MIME and non-placeholder/non-watermarked correct variant. The manufacturer 3203 PDF's pictured 1004A/3006A are NOT pictures of 1506A. Prior identified merchant gallery URLs remain candidates only. Abort if media unverified or URL is inaccessible/non-materialized.
4. Verify site stock authority is still owner-approved AVAILABLE for both. Confirm storefront publication settings (including hide-imageless and materialized-images policies) and upload strategy without introducing remote placeholders.
5. Inspect Hesabfa integration config and any queued side effect. **Ordinary ProductService.update_product_with_validation invokes ensure_product_in_hesabfa after DB commit. Do not use an update path that can send item/save or create mappings.** Do not change integration flags as a bypass; design an isolated, reviewed update that provably performs zero Hesabfa requests/mutations. Stop unless no-Hesabfa-write property is proven by inspection and test.
6. Capture entire before-image, image rows, product-change log baseline, pending transactions and SHA256 evidence; verify no other catalog mutation/owner freeze blocks release. Precompute rollback with compare-and-swap guards.

## Proposed scoped transaction — future operator execution ONLY after gates and separate explicit owner approval

- No changes before valid image binaries are stored, rights checked and durable storefront URLs verified. Prefer stage/copy binary and validate availability before making products public; exact image row changes must be audited.
- All product-field mutations constrained to `WHERE id IN (1944, 3639)`, exact expected SKU, `deleted_at IS NULL`, and expected `updated_at`/old field values from immediately preceding fresh preflight. Treat any mismatch or rowcount other than **exactly two** as FAIL and ROLLBACK. If availability needs a separate API, make it a gated phase with its own before-image and postflight; do not assume it belongs to generic form update.
- Allowed product column set: `original_price`, `base_price`, `is_active`, `is_available` only; expected values: 1944 => (47100000.00,40035000.00,true,true), 3639 => (53400000.00,45390000.00,true,true). Product-image rows only for separately approved precise URLs and prior image state. No SKU, slug, name, product type, brand, category, tax, warehouse count, deletion, global catalog, price source, integration flag, or Hesabfa modifications.
- Prefer minimal explicitly reviewed service path with proper audit log entries for old/new price and availability and timestamp handling. No direct ad-hoc SQL UPDATE from this document; no script in this PR has APPLY enabled.
- Require post-commit exact two-ID diff; inspect public list/PDP and add-to-cart (without completing a real payment): HTTP 200, correct authentic image, available/purchasable, strikethrough ordinary price and exact 15% final sale price, no unrelated product delta, no Hesabfa call.
- On partial failure or unexpected public state, halt further mutation, assess compensating rollback from the captured before-images with concurrency guards, and produce a journal; do not roll back by blindly overwriting an intervening owner's changes.

## Current disposition
Price and arithmetic: PASS (owner confirmation). Real stock: PASS (owner confirmation). Latest deployed production read-only inspection: PENDING. Licensed downloaded product image bytes: PENDING. No-Hesabfa-write isolated path and tests: PENDING. The last two plus fresh CI and owner APPLY approval are required before live publication.

## Preflight implementation handoff

An exact two-ID SQL read-only report now lives at
`scripts/catalog_target/insize_two_product_readonly_preflight_20261018.sql`.
On an already-approved **read-only Production connection**, operator runs:

```bash
psql "$READ_ONLY_DSN" -X -v ON_ERROR_STOP=1 \
  -f scripts/catalog_target/insize_two_product_readonly_preflight_20261018.sql
```

The session explicitly starts `REPEATABLE READ READ ONLY`, prints database identity
and `transaction_read_only`, lists current product and image rows, then
`ROLLBACK`s. Accept only `transaction_read_only=on`, exact `found_target_rows=2`,
`matching_identity_rows=2`, `nondeleted_rows=2` and both `identity_gate=IDENTITY_MATCH`.
If the database is not independently proven to be the live data plane, STOP. Never
share credentials, environment values or unredacted DB network details. The report
is a preflight **request**, not evidence it has been run.

Independent public storefront probes were attempted from the external retrieval
environment, but the live shop/API could not be fetched reliably; no HTTP status,
image materialization or cart result is claimed.

Media acquisition: candidate Cutwel exact-SKU direct JPEG paths were investigated
but could not be materialized/verified through the available download environment.
The official INSIZE product pages certify 2824-S3 specs and 3203 series code, but
do not grant republication rights for image assets. Original full-resolution
storefront-authorized photographs must come from the owner or supplier. Manufacturer
contact is `sales@insize.com` per its official contact page; written rights and
the exact kit photo should be requested before image ingestion.

## Live production read-only preflight — 2026-10-18T10:40:12Z

Operator ran `scripts/catalog_target/insize_two_product_readonly_preflight_20261018.sql`
against independently verified `srv5944957438` / Docker container
`lathe_postgres` / mounted volume `karzar_postgres_data` / Compose project
`karzar` / DB `karzar_staging` (the live data plane). Session
`transaction_read_only=on`, `ROLLBACK`, process exit=0.

| ID | SKU | brand_id | active | available | base_price | original_price | image_rows | deleted_at |
|---|---|---:|---|---|---:|---:|---:|---|
| 1944 | 3203-1506 | NULL | true | true | 47,100,000.00 | 47,100,000.00 | 0 | NULL |
| 3639 | S3-2824 | NULL | true | true | NULL | 10.00 | 0 | NULL |

`found_target_rows=2`, `matching_identity_rows=0`, `nondeleted_rows=2`.
Both fail the original brand_id=3 identity gate. Manufacturer code for 1944
is `3203-1506`; 3639 manufacturer code is NULL. Prior 2026-09-30/2026-10-13
snapshots identified these IDs with `brand_id=3`; current loss is unexplained.
Older product 1789 audit documented an admin path capable of clearing brand_id
on product save; this is only a hypothesis here, **not an attribution**.
Existing active+available state MUST NOT be interpreted as public visibility:
both image arrays are empty and 3639 has no sale price. No price/image/brand
mutation authorized by this snapshot. Need read-only brand existence, category
and product_change_logs inspection, and separate owner approval before any
identity-critical brand repair. **Do not silently relax identity preflight**.
