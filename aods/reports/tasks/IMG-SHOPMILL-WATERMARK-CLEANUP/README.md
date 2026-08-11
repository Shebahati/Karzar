# IMG-SHOPMILL-WATERMARK-CLEANUP

**Node:** IMG-SHOPMILL-WATERMARK-CLEANUP  
**Prompt:** `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md`  
**Change class:** C4 (data/media affecting — staged locally; not applied to production)  
**Branch:** `fix/remove-shopmill-watermarks-active-products`  
**Base:** `db0d3db` (local `main` / cached `origin/main`; live `git fetch` failed)

## Executive result

```text
Staged remediations with post-repair ShopMill detection == 0 unique assets: YES (163/163)
Active/public products with visible ShopMill-watermarked images on the LIVE storefront after remediation: NOT YET — apply blocked
```

**Acceptance criterion for customer-visible live storefront is NOT fully met** until remediated bytes are applied to the serving storage (and any required deploy). This node completed offline audit + Method C remediation staging + verification of staged assets.

## Active/public semantics (cited)

| Field | Storefront meaning | Citation |
|-------|--------------------|----------|
| `is_active=true` | Forced for non-admin product list | `app/api/endpoints/products_catalog.py:131-132` |
| `deleted_at IS NULL` | Soft-deleted excluded from normal queries | `app/crud/product.py:115`, `app/db/models/product.py:187-188` |
| `is_available` | Binary stock UX; **not** required for catalog visibility | `app/db/models/product.py:171-173` |
| Images | `ProductImage` rows; presenter uses primary else first | `app/db/models/product.py:236-252`, `docs/FAST_IMAGE_COVERAGE.md` |

IMG-FAST-01A live catalog total active products: **5901** (external baseline).  
This audit covers all **1193** active/public products that currently have `ProductImage` rows (IMG-02A-01). The remaining active products have **no** product images → no ShopMill watermark exposure.

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
| Unresolved assets | 0 |
| Final ShopMill-positive **staged** assets | **0** |
| Broken/missing staged outputs | 0 |

Brands (confirmed products): TERMA 181, ASTPOWER 143, SAN OU 62, Dasqua 24.

## Per-product remediation table

Full machine-readable table:

- `remediation-manifest.csv` (410 product×image rows)
- `confirmed-unique-assets.csv` (163 assets)
- `verification-results.csv`

Columns include product ID/slug/title, original URL/path, Method C output path under `/var/tmp/karzar-shopmill-cleanup/repaired_assets/`, hashes, verification status.

## Technical changes

| Path | Role |
|------|------|
| `scripts/audit_active_product_shopmill_watermarks.py` | Audit / remediate / verify CLI |
| `scripts/shopmill_watermark/**` | Detect + remediate + inventory loaders |
| `scripts/apply_shopmill_watermark_remediations.py` | Local storage apply helper (dry-run default) |
| `tests/test_shopmill_watermark_detect.py` | Unit tests (4) |
| `aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/**` | CSVs, JSON summaries, before/after samples |

**Not changed:** API, frontend, Alembic, production DB, `data/uploads` (empty locally).

## Watermark pattern

Confirmed on samples across TERMA / ASTPOWER / SAN OU / Dasqua:

- Top-left **ShopMill** logo
- “Shop” yellow/orange + “Mill” navy
- Studio white background → Method C = detect bbox → fill white rectangle

Auto-only confirmation was **disabled** after false positives on Mitutoyo yellow dial faces (HR `none_visible` / `KEEP`). Confirmed set = HR `distributor_or_retailer` only.

## QA evidence

### Audit re-run (staged)

```text
unique_assets_verified=163
final_shopmill_positive_assets=0
acceptance_gate=true
```

### Unit tests

```bash
python3 -m pytest tests/test_shopmill_watermark_detect.py -q --noconftest
# 4 passed
```

### Storefront visual QA

**Blocked** — no local DB (`.env` absent), `data/uploads/products` empty, outbound HTTPS to `api.karzartools.com` failed (`Proxy CONNECT aborted` / DNS).  
Offline visual QA performed on HR previews + staged repairs (`samples/before|after/`).

### Representative before/after

See `samples/before/` and `samples/after/` (one asset per brand).

## Data sources used

| Source | Path |
|--------|------|
| IMG-02A-01 inventory | `/var/tmp/karzar-image-audit/img02a01-20260803T121056Z/inventory.csv` |
| IMG-02A-02 asset reviews | `/var/tmp/karzar-image-review/human-review/*/asset-review.csv` |
| Preview pixels | `/var/tmp/karzar-image-review/**/previews/` |
| Staged repairs | `/var/tmp/karzar-shopmill-cleanup/repaired_assets/` |

## Risks / remaining blockers

1. **Apply not executed** — no local Postgres / empty uploads tree; ADR-012 forbids production writes from this node.
2. **Live storefront still serves ShopMill originals** until storage bytes are replaced on the VPS (or equivalent Category B authorized apply).
3. **Method A/B unavailable offline** — IMG-02B accepted clean assets are INSIZE-only; ShopMill-affected brands had no manufacturer clean drops locally.
4. **Preview corpus vs VPS originals** — remediations used HR preview/package pixels (often equal or higher quality than inventory `byte_size`). Prefer re-running Method C against VPS originals at apply time if preview≠original bytes.
5. **Network** — live API/storefront verification blocked in this environment.
6. **Rights** — HR `rights_status=review_required` unchanged; this node only removes distributor watermark pixels.

## How to finish live cleanup (human / Category B)

```bash
# After local/staging storage is available (NOT production unless HC-09):
python3 scripts/apply_shopmill_watermark_remediations.py \
  --manifest aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/remediation-manifest.csv \
  --storage-root /path/to/data/uploads/products \
  --apply

# Re-verify detection on applied files, then storefront spot-check PDPs.
```

## Reproduce

```bash
python3 scripts/audit_active_product_shopmill_watermarks.py --mode all \
  --report-dir aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP \
  --work-dir /var/tmp/karzar-shopmill-cleanup
```
