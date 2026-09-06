# IMG-FAST-01A — Live storefront catalog baseline

**Node:** IMG-FAST-01A-CATALOG-BASELINE  
**Prompt:** `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md`  
**Change class:** C2  
**Branch:** `feature/img-fast-01a-catalog-baseline`

## Goal

Authoritative, deterministic, **read-only** full-catalog primary-image baseline from the **live public storefront API**, separating existing-asset repair from internet discovery.

## Authority

- Live public API: `https://api.karzartools.com`
- List: `GET /api/v1/products/?skip=&limit=` (limit ≤ 1000; trailing slash required)
- Detail: `GET /api/v1/products/{product_id}`
- Historical reconciliation only: `docs/EXISTING_IMAGE_AUDIT.md` (IMG-02A-01 @ 2026-08-03)
- Runtime thumbnail rule: `app/utils/product_presenter.py` on `origin/main`

## Results (packaged run2)

- catalog_total = **5901**
- usable_primary = **1193**
- promotable_existing_image = **0**
- missing_all_images = **4708**
- broken_only = **0**
- known_placeholder_only = **0**
- ambiguous_current_state = **0**
- internet_discovery_universe = **4708**
- existing_asset_repair_universe = **0**
- semantic_second_run_stable = **true**
- drift_rows = **0**

Artifact: `/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01A(.zip)`

## Explicit non-goals

No DB access; no ProductImage/storage mutations; no third-party discovery; no apply/replace; Draft PR only.

## Safety invariants

- `database_accessed = false`
- `database_modified = false`
- `ProductImage_modified = false`
- `API_write_requests = 0`
- `external_discovery_requests = 0`
- Artifact external to Git
