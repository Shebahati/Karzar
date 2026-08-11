# ShopMill production preflight (read-only) — operator notes

Companion to tooling on branch `fix/remove-shopmill-watermarks-active-products`.

## Portable bundle

`.local-rescue/shopmill-watermark-cleanup/vps-preflight/` (gitignored binaries/dir; instructions + manifests also mirrored under this report where noted)

* `target-serving-paths.csv` — also at `aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/target-serving-paths.csv`
* Script: `scripts/shopmill_production_preflight.py`

## Discovery expectations

On VPS:

1. Find backend container with mount destination `/app/data/uploads`
2. Resolve named volume → `Mountpoint` via `docker volume inspect`
3. `PRODUCTS_STORAGE_ROOT="${UPLOADS_VOLUME_MOUNTPOINT}/products"`
4. Confirm directory exists; run preflight with reports under `/tmp/karzar-shopmill-preflight-*` only

## Paste block

See final response / `VPS-READONLY-PREFLIGHT.sh` in the portable bundle.
