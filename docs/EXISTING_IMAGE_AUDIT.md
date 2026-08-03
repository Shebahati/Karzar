# Existing Image Audit (IMG-02A-01)

**Task:** IMG-02A-01 — Canonical Existing Product Image Inventory  
**R1:** IMG-02A-01-R1 — pre-authoritative boundary hardening (see task record)  
**Status:** tooling Draft / not production-approved  
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

## Related

- Discovery tooling (separate): `docs/IMAGE_DISCOVERY_PIPELINE.md`
- Task records: `aods/reports/tasks/IMG-02A-01-CANONICAL-EXISTING-IMAGE-INVENTORY.md`, `aods/reports/tasks/IMG-02A-01-R1-CLOSE-PRE-AUTHORITATIVE-BLOCKERS.md`
