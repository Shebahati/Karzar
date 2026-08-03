# TASK-RECORD · IMG-02A-01

| Field | Value |
|-------|-------|
| Task ID | IMG-02A-01 |
| Title | Canonical Existing Product Image Inventory |
| Change class | C2 |
| Role | R-BE-ARCH / KNOW |
| Prompt | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| Base commit | `306271e66742cddc075c32fd1713adcf9c4992c3` |
| Branch | `feat/existing-image-audit` |
| Status | in_progress (Draft PR) |

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
base commit: 306271e66742cddc075c32fd1713adcf9c4992c3
branch: feat/existing-image-audit
authoritative run status: AUTHORITATIVE RUN BLOCKED
blocker: VPS SSH (45.13.226.43, 198.105.115.135) connection timed out from this environment;
  no DATABASE_URL / POSTGRES_* / local authoritative storage available;
  local laptop counts NOT substituted
database read-only proof: not executed on authoritative DB (blocked)
authoritative database name: unavailable
storage root: unavailable
output directory: not created (no authoritative run)
output checksums: n/a
current counts: n/a (not substituted)
prior snapshot deltas: n/a (not substituted)
local static rows: n/a
remote unverified rows: n/a
missing files: n/a
decode failures: n/a
exact duplicate groups: n/a
cross-product duplicate groups: n/a
cross-brand duplicate groups: n/a
unreferenced storage files: n/a
rejected storage entries: n/a
network request count = 0 (by design; no run performed)
database writes = 0 (by design; no run performed)
storage mutations = 0 (by design; no run performed)
```

## Local validation (implementation)

- `tests/test_existing_image_audit.py`: 25 passed
- PYTHONHASHSEED 0–9: passed
- IMG-01 regression `tests/test_image_discovery*.py`: 110 passed
- ruff: passed on audit paths
- aods_validate links/registry/pmo/naming/ingestion-boundary: PASS
