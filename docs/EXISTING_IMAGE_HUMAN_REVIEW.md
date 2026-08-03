# Existing Image Human Review (IMG-02A-02)

**Task:** IMG-02A-02 — Existing Image Human Review Batches and Pilot 001  
**Implementation status:** tooling Draft (open PR) / human review pending  
**Operational mode:** offline package generation only  
**Production mutation capability:** none

## Purpose

Build a deterministic, offline human-review package from the immutable IMG-02A-01 inventory:

- group validated local images by SHA-256 asset;
- select Pilot 001 (exactly 100 unique local assets);
- generate review previews/thumbnails **outside** Git and source storage;
- provide separate **asset-level** and **assignment-level** review forms;
- ship a self-contained `review.html` with no network dependency.

## Non-goals

- Database access or `ProductImage` writes
- Storage cleanup/replacement
- Remote HTTP/DNS/HEAD/GET or TOSAG
- OCR / automatic watermark verdicts / automatic product-match verdicts
- Discovery for products without images
- Deployment
- Committing images, previews, raw inventory, or the Pilot ZIP to Git

## Authoritative input

```text
source: /var/tmp/karzar-image-audit/img02a01-20260803T121056Z
checksums.sha256 digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d
```

The CLI verifies the checksum manifest and the fixed summary aggregates before any inventory read. It does **not** re-query the database.

## Command

```bash
python scripts/build_existing_image_review_batches.py \
  --source-dir /absolute/path/to/img02a01-20260803T121056Z \
  --storage-root /absolute/path/to/data/uploads/products \
  --output-dir /absolute/empty/path/outside/repo \
  --zip-path /absolute/path/IMG-02A-02-pilot-001.zip
```

Storage must be opened read-only (`O_RDONLY|O_NOFOLLOW`). Output must be empty, outside the repository, and disjoint from storage.

## Two-level review

| Level | Unit | Decides |
|-------|------|---------|
| Asset | unique SHA-256 | watermark visibility, quality, background, crop, replacement priority, rights-review state |
| Assignment | ProductImage link | exact product fit vs family-shared vs mismatch |

Defaults: `rights_status=review_required`. Never auto-set `cleared_by_owner`. Watermark pre-screen is `not_run` (human-only).

## Pilot 001

- ID: `IMG-02A-02-PILOT-001`
- 50 shared assets (`product_count > 1`) + 50 singleton assets (brand round-robin)
- Remote inventory rows are deferred (`remote-deferred.csv`), not reviewed in Pilot 001

## Boundary claims

```text
network_requests_performed = 0
database_accessed = false
source_storage_mutations = 0
product_images_modified = false
```

Pilot generation complete ≠ human decisions applied.
