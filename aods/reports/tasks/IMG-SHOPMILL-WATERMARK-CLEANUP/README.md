# IMG-SHOPMILL-WATERMARK-CLEANUP

**Node:** IMG-SHOPMILL-WATERMARK-CLEANUP  
**Prompt:** `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md`  
**Change class:** C4 (data/media affecting — staged locally; **not** applied to production)  
**Branch:** `fix/remove-shopmill-watermarks-active-products`  
**Base:** `db0d3db` (local `main` / cached `origin/main`)

## Status legend (do not conflate)

| State | Meaning | Current |
|-------|---------|---------|
| Audited | Active/public imaged catalog inventoried | **Done** |
| Repaired | Method C outputs exist for confirmed assets | **Done (163)** |
| Staged | Repairs verified ShopMill-negative offline | **Done** |
| Applied to staging | Bytes written to a non-production serving root | **Not done** (no staging storage access) |
| Applied to production | Bytes written to live `karzar_uploads` | **Not done — STOP** |
| Live verified | Storefront QA on serving URLs | **Not done** |

## Executive result

```text
Staged remediations with post-repair ShopMill detection == 0 unique assets: YES (163/163)
Applied to staging: NO
Applied to production: NO
Live storefront ShopMill-positive after apply: UNKNOWN (still serving originals)
```

**Operational apply is blocked** in this environment: serving storage is the live VPS Docker volume (CR-011 staging≈production), and this agent has no reachable SSH/Docker mount to that volume.

## Durable repair backup

Preferred path `/home/moahmmad/Karzar-local-rescue-20260811/...` could **not** be created (agent sandbox denies writes outside the workspace).

Durable copy (byte-identical to `/var/tmp/karzar-shopmill-cleanup/repaired_assets/`):

```text
path:   /home/moahmmad/Projects/Karzar/.local-rescue/shopmill-watermark-cleanup/
images: 163
size:   65M
checksum file: repaired-assets.sha256
identical_to_vartmp: YES
gitignored: .local-rescue/
manifests/: remediation + audit CSVs/JSON copied alongside
```

`/var/tmp` copy was **not** deleted (copy-first).

## Serving storage (authoritative)

| Item | Value | Citation |
|------|-------|----------|
| Storage type | Docker named volume `karzar_uploads` | `docker-compose.yml:24`, `:77-78` |
| Container path | `/app/data/uploads` | `docs/OPERATIONS.md:149` |
| Product subtree | `/app/data/uploads/products/{product_id}/{file}` | `app/utils/file_storage.py:56-61` |
| Repo-relative path | `data/uploads/products/` | `docs/EXISTING_IMAGE_AUDIT.md:37-38` |
| Public URL marker | `/static/uploads/products/` | `app/main.py:141`, `EXISTING_IMAGE_AUDIT.md:38` |
| Public host (live) | `https://api.karzartools.com/static/uploads/products/...` | IMG-02A-01 inventory URLs |
| VPS checkout | `/opt/karzar/Karzar` | `docs/COLLABORATOR_DEPLOY.md:34` |
| Live hazard | Staging deploy target = same VPS as production | `CR-011` / `COLLABORATOR_DEPLOY.md:28-31` |

**URL → file mapping:** strip host; require exact marker `/static/uploads/products/`; remainder is relative path under the uploads products root.

## Access check (this environment)

| Mechanism | Result |
|-----------|--------|
| Local `data/uploads/products` | Empty / absent product files |
| Local Docker / `karzar_uploads` volume | Docker socket unavailable |
| SSH to configured hosts | Network unreachable |
| SSH to documented VPS `195.177.255.198` | Failed (ssh_config permissions / no usable session) |
| `.env` present | No |

**Required for apply:** interactive SSH (or equivalent) to the VPS as an operator who can reach `docker compose` / the `karzar_uploads` volume under `/opt/karzar/Karzar`, **plus explicit production authorization** (this prompt forbids unattended live mutation).

## Pre-apply verification

| Check | Result |
|-------|--------|
| Expected affected unique assets | 163 |
| Durable repairs present | 163/163 |
| Post-repair ShopMill detection | **0** positive |
| Serving originals hash-compared | **0** (storage inaccessible) |
| Classification | **MISSING SOURCE × 163** (serving) |
| Exact hash matches vs live | 0 |
| Changed source assets | unknown |
| Format note | Staged repairs are often `.png`/`.jpg` while live paths are often `.webp`; apply helper now converts on write |

Artifacts: `preapply-validation.json`, `preapply-validation.csv`, `preapply-dry-run-local-empty.json`.

## Backup (production originals)

**Not created** — no access to serving originals. Rollback readiness: **not ready**.

## Dry run

Against empty local `data/uploads/products` using durable replacement paths:

```text
planned_unique_paths=410   # per-product file paths (shared SHA ⇒ multiple paths)
classification_counts={'MISSING SOURCE': 410}
products_affected=410
conflicts=0
errors=0 (dry-run)
```

No non-production populated storage root was available for a meaningful EXACT MATCH dry-run.

## Apply

**Not executed.** Production/live is the only reachable serving storage architecture, and this prompt forbids mutating it without explicit authorization.

### Proposed production apply (REQUIRES EXPLICIT HUMAN OK)

On the VPS, after backing up the volume and verifying EXACT MATCH hashes against live files:

```bash
# 1) On VPS: backup uploads volume
cd /opt/karzar/Karzar
./scripts/backup_uploads.sh

# 2) Materialize durable repairs onto the host (example)
#    scp/rsync .local-rescue/shopmill-watermark-cleanup/ → /opt/karzar/shopmill-watermark-cleanup/

# 3) Discover the volume mount path for karzar_uploads (operator), then dry-run:
python3 scripts/apply_shopmill_watermark_remediations.py \
  --manifest aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/remediation-manifest.durable-paths.csv \
  --storage-root /PATH/TO/VOLUME/products \
  --require-exact-match \
  --report-json /tmp/shopmill-apply-report.json

# 4) Only with explicit production authorization:
python3 scripts/apply_shopmill_watermark_remediations.py \
  --manifest aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/remediation-manifest.durable-paths.csv \
  --storage-root /PATH/TO/VOLUME/products \
  --require-exact-match \
  --apply
```

Files that would be replaced if EXACT MATCH: up to **410** product file paths (**163** unique contents).

Rollback: restore from `backup_uploads.sh` archive via `scripts/restore_uploads.sh`, or per-file `*.shopmill-bak` siblings created by the apply helper.

## Active/public semantics (cited)

| Field | Storefront meaning | Citation |
|-------|--------------------|----------|
| `is_active=true` | Forced for non-admin product list | `app/api/endpoints/products_catalog.py:131-132` |
| `deleted_at IS NULL` | Soft-deleted excluded from normal queries | `app/crud/product.py:115`, `app/db/models/product.py:187-188` |
| `is_available` | Binary stock UX; **not** required for catalog visibility | `app/db/models/product.py:171-173` |
| Images | `ProductImage` rows; presenter uses primary else first | `app/db/models/product.py:236-252`, `docs/FAST_IMAGE_COVERAGE.md` |

IMG-FAST-01A live catalog total active products: **5901**.  
This audit covers all **1193** active/public products with `ProductImage` rows.

## Counts

| Metric | Value |
|--------|------:|
| Active/public products with images audited | 1193 |
| Unique active-product image SHA-256s | 614 |
| Active-product image rows | 1193 |
| HR `distributor_or_retailer` assets (ShopMill) | 163 |
| Automatic detector candidates (rows) | 412 |
| Visually/HR **confirmed** affected image rows | 410 |
| Confirmed unique assets | 163 |
| Affected products | 410 |
| Method A (clean originals) | 0 |
| Method B (clean alternates) | 0 |
| Method C (professional repair) | 163 |
| Unresolved staged assets | 0 |
| Final ShopMill-positive **staged** assets | **0** |
| Applied to live storage | **0** |

Brands (confirmed products): TERMA 181, ASTPOWER 143, SAN OU 62, Dasqua 24.

## Per-product remediation table

- `remediation-manifest.csv` (410 rows)
- `remediation-manifest.durable-paths.csv` (same rows; `output_path` → `.local-rescue/...`)
- `confirmed-unique-assets.csv` (163)
- `verification-results.csv`
- `preapply-validation.csv`

## Technical changes

| Path | Role |
|------|------|
| `scripts/audit_active_product_shopmill_watermarks.py` | Audit / remediate / verify CLI |
| `scripts/shopmill_watermark/**` | Detect + remediate + inventory loaders |
| `scripts/apply_shopmill_watermark_remediations.py` | Dry-run/apply with classification + format convert |
| `tests/test_shopmill_watermark_detect.py` | Unit tests |
| `aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/**` | Reports |
| `.gitignore` | Ignores `.local-rescue/` |

## QA evidence

### Staged verification

```text
unique_assets_verified=163
final_shopmill_positive_assets=0
```

### Unit tests

```bash
python3 -m pytest tests/test_shopmill_watermark_detect.py -q --noconftest
# 4 passed
```

### Storefront QA

**Blocked** — no applied storage + no live API/SSH from this environment.

## Reproduce offline

```bash
python3 scripts/audit_active_product_shopmill_watermarks.py --mode all \
  --report-dir aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP \
  --work-dir /var/tmp/karzar-shopmill-cleanup

python3 scripts/apply_shopmill_watermark_remediations.py \
  --manifest aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/remediation-manifest.durable-paths.csv \
  --storage-root data/uploads/products \
  --report-json aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/preapply-dry-run-local-empty.json
```
