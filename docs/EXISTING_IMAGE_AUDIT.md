# Existing Image Audit (IMG-02A-01)

**Task:** IMG-02A-01 — Canonical Existing Product Image Inventory
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
public marker:  /static/uploads/products/
```

Only URLs whose path contains the public marker may map to a local file, and only after safe path validation (no symlink follow, no traversal, no absolute FS paths).

## Command

```bash
.venv/bin/python scripts/audit_existing_product_images.py \
  --output-dir /absolute/path/outside/repository \
  --storage-root /absolute/path/to/data/uploads/products
```

Required:

- `--output-dir` absolute, outside the repository, empty, not a symlink
- `--storage-root` real directory, not a symlink (defaults to `<repo>/data/uploads/products`)

Optional:

- `--include-deleted-products` / `--no-include-deleted-products` (default: include)
- `--no-storage-scan` emergency DB-only mode (marks storage scan skipped)
- `--database-url` or `DATABASE_URL` / `POSTGRES_*` env (password never printed)

## Read-only database enforcement

1. One explicit transaction
2. PostgreSQL: `SET TRANSACTION READ ONLY` + `SHOW transaction_read_only` must be `on`
3. SELECT-only queries; autoflush disabled
4. Statement guard rejects INSERT/UPDATE/DELETE/DDL and related write verbs
5. Transaction always rolled back (including successful runs)
6. Safe identity fields only: dialect, database_name, database_user, transaction_read_only

## Outputs (outside Git)

All operational files are written **outside** the repository:

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

`checksums.sha256` covers every generated file except itself. Raw inventory rows must not be committed to Git.

## Related

- Discovery tooling (separate): `docs/IMAGE_DISCOVERY_PIPELINE.md`
- Task record: `aods/reports/tasks/IMG-02A-01-CANONICAL-EXISTING-IMAGE-INVENTORY.md`
