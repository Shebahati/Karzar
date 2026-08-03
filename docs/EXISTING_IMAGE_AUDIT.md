# Existing Image Audit (IMG-02A-01)

**Task:** IMG-02A-01 — Canonical Existing Product Image Inventory
**R1:** IMG-02A-01-R1 — pre-authoritative boundary hardening (see task record)
**Status:** tooling Ready for Review (PR #201) / not production-approved
**Authoritative run:** complete 2026-08-03T12:11Z (`karzar_staging`, `transaction_read_only=on`)
**Mutations:** none (database, ProductImage, and storage are read-only)

## Purpose

Produce a canonical, reproducible, **read-only** inventory of:

- every `Product` / `ProductImage` row (with brand/category context);
- every safely reachable local file under `data/uploads/products/`;
- exact-byte duplicate groups, coverage anomalies, and unreferenced storage files.

This phase **inventories current state only**. It does **not** judge watermark quality, image suitability, or commercial rights. Remote HTTP(S) URLs are recorded as **unverified** because this phase performs **no network requests**.

## Non-goals

- Watermark / OCR / perceptual hash / visual similarity
- KEEP / REPLACE classification
- Remote HEAD/GET/DNS or TOSAG access
- ProductImage inserts/updates/deletes
- Alembic migrations
- Storage cleanup or deleting unreferenced files
- Changing image URLs
- Deployment

## Storage convention

```text
storage root:   data/uploads/products/
public marker:  /static/uploads/products/   (exact; trailing slash required)
```

Only URLs whose path contains the **exact** public marker may map to a local file. Lookalikes such as `products-evil` or `products_backup` are rejected. HTTP(S) URLs that include the marker map locally regardless of hostname. Userinfo, query, and fragment are stripped from persisted URLs (`query_present=true` when a query existed); `url_host` is preserved.

Path validation: no symlink follow, no traversal, no absolute FS paths, per-component `lstat`, file opens use `O_RDONLY|O_NOFOLLOW`.

## Command

```bash
.venv/bin/python scripts/audit_existing_product_images.py \
  --output-dir /absolute/path/outside/repository \
  --storage-root /absolute/path/to/data/uploads/products
```

Required:

- `--output-dir` absolute, outside the repository, empty, not a symlink, and **disjoint** from `--storage-root` (neither may equal or nest inside the other)
- `--storage-root` real directory, not a symlink (defaults to `<repo>/data/uploads/products`; **not required to exist** when `--no-storage-scan`)

Optional:

- `--include-deleted-products` / `--no-include-deleted-products` (default: include)
- `--no-storage-scan` emergency DB-only mode (zero filesystem reads; rows marked `local_unverified`; `storage_scan_completed=false`)
- `--database-url` or `DATABASE_URL` / `POSTGRES_*` env (password never printed)

**Operational runs require PostgreSQL** with `transaction_read_only=on`. SQLite is test-only.

## Read-only database enforcement

1. One explicit transaction
2. PostgreSQL: `SET TRANSACTION READ ONLY` + `SHOW transaction_read_only` must be `on`
3. SELECT-only queries; autoflush disabled
4. Statement guard allows only `SELECT`/`WITH`/`EXPLAIN` plus exact `SET TRANSACTION READ ONLY` and `SHOW transaction_read_only`; rejects `SET TRANSACTION READ WRITE` and non-allowlisted `PRAGMA`
5. Transaction always rolled back (including successful runs)
6. Safe identity fields only: dialect, database_name, database_user, transaction_read_only
7. `database_read_only=true` in summary only when PostgreSQL reports `on`

## Outputs (outside Git)

All operational files are written **outside** the repository via **staged atomic publish** (temp staging → streamed checksums → publish; failure leaves output empty):

```text
inventory.csv / inventory.json
product-coverage.csv / product-coverage.json
summary.json
run-metadata.json
broken-or-unavailable.csv
remote-unverified.csv
database-anomalies.csv
duplicate-exact-sha.csv
products-without-valid-image.csv
products-with-multiple-images.csv
unreferenced-storage-assets.csv
rejected-storage-entries.csv
checksums.sha256
```

`summary.json` includes `storage_modified=false` and `storage_mutations=0`. Raw inventory rows must not be committed to Git.


## Authoritative inventory evidence (aggregate only)

Executed inside authoritative app container against PostgreSQL with `transaction_read_only=on`. Raw CSV/JSON remain on the VPS under `/var/tmp/karzar-image-audit/img02a01-20260803T121056Z` (not in Git).

| Metric | Value |
|--------|------:|
| total_products | 5918 |
| products_with_image_rows | 1194 |
| total_product_images | 1194 |
| valid_local_image_rows | 1193 |
| external_remote_rows | 1 |
| missing_local_file_rows | 0 |
| decode_failed_rows | 0 |
| exact_duplicate_sha_groups | 188 |
| cross_product_duplicate_sha_groups | 188 |
| unreferenced_storage_files | 0 |
| network_requests_performed | 0 |
| database_modified | false |
| storage_mutations | 0 |

`checksums.sha256` digest: `4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d` (all member hashes verified).

## Related

- Discovery tooling (separate): `docs/IMAGE_DISCOVERY_PIPELINE.md`
- Task records: `aods/reports/tasks/IMG-02A-01-CANONICAL-EXISTING-IMAGE-INVENTORY.md`, `aods/reports/tasks/IMG-02A-01-R1-CLOSE-PRE-AUTHORITATIVE-BLOCKERS.md`
