# ZCC controlled production import

## Scope

Local validation completed for ZCC product drafts, prices, and primary images. Production execution is Category B and must not use a database dump from local development.

## Required approval record

- Change ticket ID: pending
- Production DB owner/delegate approval: pending
- Git commit containing the reviewed scripts and mappings: pending
- SKU allowlist and expected counts: attach to ticket before execution

## Preflight on the VPS

1. Confirm the reviewed Git commit and clean working tree.
2. Run `./scripts/backup_db.sh` and retain the returned artifact path.
3. Run `./scripts/backup_uploads.sh` and retain the returned artifact path.
4. Use the production API only with `KARZAR_ALLOW_PRODUCTION_WRITE=1` and `KARZAR_INGESTION_CATEGORY=B`.
5. Run each job as a dry run first. Record its source checksum, plan hash, target SKU allowlist, expected create/update count, and audit path in the ticket.

## Controlled execution order

1. Taxonomy and brands, limited sample, then verify.
2. Inactive product drafts, limited sample, then verify SKU uniqueness and category/brand assignment.
3. Price job only for source prices with status `ok`; exclude zero/invalid prices.
4. Images: upload source files to VPS storage; retain manufacturer marks; do not edit images unless an independent ZCC-store watermark is confirmed.

## Validation and rollback

- Confirm every planned SKU once, expected draft/price/image counts, and no unintended availability change.
- Stop on the first unexpected API response or count divergence.
- Restore database with `./scripts/restore_db.sh <pre-run-backup>` and uploads with `./scripts/restore_uploads.sh <pre-run-uploads-backup>` when rollback is authorized.
- Attach audit journals and final validation counts to the change ticket.
