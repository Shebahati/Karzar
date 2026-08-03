# TASK-RECORD · IMG-02A-01

| Field | Value |
|-------|-------|
| Task ID | IMG-02A-01 |
| Title | Canonical Existing Product Image Inventory |
| Change class | C2 |
| Role | R-BE-ARCH / KNOW |
| Prompt | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| Base commit | `306271e66742cddc075c32fd1713adcf9c4992c3` |
| Implementation head | `8a2059459a4d6d6798bb82b27793b1d26225f41f` |
| Branch | `feat/existing-image-audit` |
| Status | in_progress (PR #201 — Ready for Review after evidence commit) |

## Goal

Create a canonical, reproducible, read-only inventory of current Product / ProductImage rows and locally materialized product-image files.

## Non-goals honored

- No watermark / OCR / pHash / similarity / KEEP-REPLACE
- No remote image requests / TOSAG
- No ProductImage or storage mutations
- No Alembic / deploy
- No modification of `scripts/image_discovery/`

## Deliverables

- CLI: `scripts/audit_existing_product_images.py`
- Package: `scripts/image_audit/`
- Tests: `tests/test_existing_image_audit.py`
- Operator doc: `docs/EXISTING_IMAGE_AUDIT.md`

## Evidence (authoritative run)

```text
authoritative run = complete
implementation commit: 8a2059459a4d6d6798bb82b27793b1d26225f41f
branch: feat/existing-image-audit
execution host: VPS srv5944957438 (authoritative app container lathe_api)
dialect: postgresql
database_name: karzar_staging
database_user: karzar_staging
transaction_read_only: on
database read-only proof: SHOW transaction_read_only → on
storage root (container): /app/data/uploads/products
external output directory (host): /var/tmp/karzar-image-audit/img02a01-20260803T121056Z
checksums.sha256 digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d
checksum verification: all listed files OK (sha256sum -c)
started_at_utc: 2026-08-03T12:11:01Z
completed_at_utc: 2026-08-03T12:11:47Z

total_products: 5918
non_deleted_products: 5917
active_products: 5901
available_products: 4183
total_product_images: 1194
products_with_image_rows: 1194
products_without_image_rows: 4724
products_with_multiple_images: 0
products_without_primary: 0
products_with_multiple_primary: 0
internal_static_rows: 1193
external_remote_rows: 1
invalid_url_rows: 0
valid_local_image_rows: 1193
missing_local_file_rows: 0
decode_failed_rows: 0
unique_local_asset_sha256s: 614
exact_duplicate_sha_groups: 188
cross_product_duplicate_sha_groups: 188
cross_brand_duplicate_sha_groups: 0
storage_regular_files: 1193
unreferenced_storage_files: 0
rejected_storage_entries: 0
broken-or-unavailable rows: 0
database anomaly rows: 1 (deleted_product_retaining_images)

prior_reference_snapshot:
  total_products: 5917
  products_with_image_rows: 1193
current_delta:
  total_products: +1
  products_with_image_rows: +1

network_requests_performed = 0
database_modified = false
storage_modified = false
storage_mutations = 0
storage_scan_completed = true
repository_modified_by_run = false
raw outputs = external and not committed
```

## Local validation (implementation)

- `tests/test_existing_image_audit.py`: 43 passed (25 baseline + 18 R1 boundary tests)
- PYTHONHASHSEED 0–9: passed
- IMG-01 regression `tests/test_image_discovery*.py`: 110 passed
- ruff: passed on audit paths
- aods_validate links/registry/pmo/naming/ingestion-boundary: PASS

## R1 notes (IMG-02A-01-R1)

Boundary hardening landed before authoritative run; see `IMG-02A-01-R1-CLOSE-PRE-AUTHORITATIVE-BLOCKERS.md`.
