# Two-product owner-confirmed pricing and gated rollout (2026-10-18)

Status: **OWNER_PRICE_APPROVED / STOCK_CONFIRMED / LIVE_PREFLIGHT_EXECUTED_IDENTITY_BLOCKED / MEDIA_BINARY_PENDING / APPLY_NOT_EXECUTED**.
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

## Follow-up product-change-log verification (read only)

Live `brands.id=3` exists: `INSIZE | اینسایز`. Product categories
`1944 -> 58 / انواع میکرومتر`, `3639 -> 63 / گیج داخل سیلندر`.

The two brand-clearing events are explicitly logged as `product_update`:
- ID 1944: `brand_id 3 -> NULL`, 2026-10-10T14:58:46.600658Z
- ID 3639: `brand_id 3 -> NULL`, 2026-10-18T09:18:13.567359Z

Other recorded misuse of `original_price`: ID 1944 `NULL -> 10 -> 15
-> NULL -> 47100000`; ID 3639 `NULL -> 10`. ID 3639 historical
`base_price NULL -> 53400000` was in 2026-10-06 logs, but live
`base_price=NULL`; the mechanism/time of the later clear is not proven
by the returned last-30 rows.

PR #529 now fixes the admin edit mapper to **omit** blank `brand_id`
instead of sending destructive explicit NULL, with regression tests.
The existing brand loss is still outstanding; a future exact two-ID
identity-repair authorization must add `brand_id=3` to the narrowly
allowed field set after fresh CAS preflight and canonical audit-log proof.
The previous field whitelist excluding brand is superseded **only for
that separate proposal**, not a grant of live APPLY. Do not infer the
specific human actor from `reason=product_update`.

## Second read-only follow-up gate

The SQL report now includes an exact 2026-10-18T10:40:12Z before-image drift check for both IDs, brand-master and brand-change-log verification, target price preview, and recent admin audit metadata. Its success state is `DATA_SNAPSHOT_MATCH_MEDIA_AND_AUTH_PENDING`, **not** APPLY permission. Any `STOP_*` result needs fresh investigation. The original `identity_gate` still intentionally reports `STOP_IDENTITY_MISMATCH` until the separate brand repair is authorized and applied. Execute only from a fresh `git show` extract, never use an older local /tmp file and never switch the data plane.

## Operator follow-up read-only evidence — 2026-10-18T11:14:51.890475Z

Executed the revised two-ID SQL against the independently verified live
`karzar_staging` database through `lathe_postgres`.
`transaction_read_only=on`; `ROLLBACK`; `PIPELINE_EXIT_STATUS=0`.

The original brand-identity gate remains at
`STOP_IDENTITY_MISMATCH` for both rows **by design** because live
`brand_id=NULL`. The separate, brand-repair-aware before-image gate
returned exactly **two**
`DATA_SNAPSHOT_MATCH_MEDIA_AND_AUTH_PENDING` values (IDs 1944, 3639).
Observed `updated_at`, prices, flags, category, SKU, manufacturer code,
empty images and brand were unchanged from the 10:40:12Z snapshot.
`admin_audit_logs` query returned zero rows for these IDs; that does not
invalidate the verified `product_change_logs` entries or identify the actor.

This proves state stability, **not** readiness to publish, authorization
to change brand or pricing, image suitability/license, or absence of
Hesabfa effects from a proposed write path. Remaining production blockers:
separately approved exact two-ID brand repair; valid original authorized
images for both real kits; reviewed no-Hesabfa-write mutation path,
before-images and rollback; owner APPLY decision after fresh recheck.

## Owner commercial-image-rights attestation — 2026-10-18

Owner explicitly confirmed commercial-use rights for the selected online product photography. **Rights gate: OWNER_ATTESTED**, not an independent legal/license review. Byte acquisition, actual visual SKU/kit inspection, image checksum/dimensions, and upload to Karzar remain incomplete. No additional rights request is needed solely due to prior caution; do not mark undownloaded remote pictures as materialized site assets. A self-contained offline local downloader for exact SKU source links was prepared for operator handoff when the agent download environment failed DNS; no VPS/product mutation and no hotlinking have occurred.

## Two real product image assets locally ready — 2026-10-18

Both exact-SKU image binaries were downloaded by owner and visually inspected. The ID 1944 Rubutek source actually contains six micrometers (750x750), and its separate spec table identifies 3203-1506A; ID 3639 fitted case actually contains three analog bore gauges (1600x1600). Owner attested commercial rights. Final verified chat artifact `karzar_insize_media_final_20261018.zip` SHA-256 `52394c679c3af6a4deebc7ac9b2b5598dbbdecfc68872ff18e9831e9468abf35` contains both heroes/thumbs, provenance and source/reference; full item SHA-256 values are in SOURCE_REVIEW.md and the archive manifest. **MEDIA_READY_LOCAL_BOTH; production image association still NO.** Remaining gates before any actual write: fresh read-only live state/identity/CAS, reviewed and tested side-effect-free no-Hesabfa path, scoped reversible media upload and price/brand action, and separately confirmed owner APPLY authorization. Do not merge/deploy/write automatically based on presence of zip.

## Owner-authorized release-package preparation — 2026-10-18

Owner explicitly authorized preparing a **protected, exact two-ID release**
to restore `brand_id=3`, assign approved 15% sale/list prices and attach
the locally verified two real primary photos; numeric stock and Hesabfa
must remain untouched. This is permission to **prepare** the run path,
not evidence of a completed production APPLY or permission to skip fresh
preflight/rollback gates.

A separately downloadable operator-only **read-only preflight** bundle was
created for Ubuntu:
`karzar_insize_release_preflight_20261018.zip` SHA-256
`c2633aa025bca8ee2a28ea28e6e13b38e0ab5acb07fe0e2999dcc887582b00b6`.
It contains `run_preflight.sh`, `release_preflight.sql`,
`README_FIRST.txt` and the two verified heroes with SHA256SUMS. The script
verifies exact pinned host and Compose project, `karzar_postgres_data` and
the API upload volume, executes its DB query under `REPEATABLE READ READ
ONLY` with `PGOPTIONS=default_transaction_read_only=on`, enumerates
any enabled noninternal product/image/audit-table triggers, and ends in
`ROLLBACK`. **NO production write path is inside this archive.**
It is not yet executed by owner. Do not label the release APPLIED.

After this report returns two `DATA_SNAPSHOT_MATCH_MEDIA_AND_AUTH_PENDING`
rows and no new triggers/changes, review a separate guarded transactional
writer. For image materialization use the existing API shared
`/app/data/uploads` volume; a direct admin image POST would commit
separately, so stage verified files before a single DB association and
price/brand transaction. Do not invoke `ProductService.update_product_with_validation`:
it invokes `ensure_product_in_hesabfa` after committing the product.
All writes need saved before-image, changed-row cardinality checks, and a
post-commit rollback journal; no broad catalog mutation/rename/deploy.

## Owner-run bundled preflight — 2026-10-18T11:58:19.353529Z

The owner executed `karzar_insize_release_preflight_20261018.zip` on
Ubuntu; reported both hero SHA-256 checks PASS; host
`srv5944957438`, DB volume `karzar_postgres_data`,
API upload volume `karzar_karzar_uploads`, DB `karzar_staging`,
`transaction_read_only=on`. Both target product rows returned
`DATA_SNAPSHOT_MATCH_MEDIA_AND_AUTH_PENDING`, image_count=0 and
exact frozen `updated_at` values. `brands.id=3` matches INSIZE;
session ended `ROLLBACK`. Report path on owner laptop:
`~/karzar_insize_release_preflight_20261018T115817Z.txt`.
No VPS file transfer or live mutation was performed.

Two enabled, noninternal triggers were observed:
`products.trg_products_updated_at` and
`product_images.trg_product_images_updated_at`. Before authoring or
allowing a transactional APPLY, examine their **live** definitions using
`pg_get_triggerdef` and `pg_get_functiondef` under READ ONLY,
particularly updated_at behavior and any other side effects. Do not
assume trigger names prove safety. Once definitions and current CI are
reviewed, produce a separate rollback-journaled APPLY package with
explicit operator opt-in, exactly these two IDs, no Hesabfa calls.

## Verified live trigger bodies and guarded APPLY candidate

Owner executed a separate READ ONLY trigger-body check for the two enabled
triggers. Both `trg_products_updated_at` and
`trg_product_images_updated_at` are BEFORE UPDATE and invoke
`public.set_updated_at()`, whose entire body is:
`BEGIN NEW.updated_at = NOW(); RETURN NEW; END;`. Transaction ended in
`ROLLBACK`; no other behavior is present in the returned definition.

Created an offline operator bundle
`karzar_insize_guarded_apply_20261018.zip`, SHA-256
`b778cd8a71c120539a41fdb01658a3100c173c7267feff22a7e569dfbb026661`.
It contains approved two heroes; existing read-only preflight; a single
`SERIALIZABLE` guarded transaction (locked IDs, expected stale baseline
timestamps/brand/SKU/manufacturer/category/prices/zero image rows, approved
brand=3 and prices, two local image rows, five product-change-log rows, two
admin-audit rows), pre/post snapshot reports, a journaled drift-guarded
rollback restoring previous prices and unlinked images, and README. The
operator entry points are default fail-closed: `run_apply.sh` does not
write unless explicitly invoked with `--apply` **and** an exact typed
confirmation. Shell syntax, embedded media SHA-256, SQL file hashes and ZIP
CRC passed offline checks. **No live SQL APPLY has been executed or
runtime-verified.** Ordinary ProductService path (which can invoke
Hesabfa) is not called; no Hesabfa table or network call occurs in this
script. After staged file verification, product/image/audit writes belong
to one DB transaction. Staged unused media may remain if pre-commit SQL
fails; they are not automatically inserted into the product gallery.

Fresh preflight, current PR CI and explicit operator decision remain
necessary before any actual APPLY. PR #529 remains Draft as of preparation;
do not infer successful deployment/merge or product publication.
