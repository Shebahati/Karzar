# IMG-SHOPMILL-WATERMARK-CLEANUP

**Node:** IMG-SHOPMILL-WATERMARK-CLEANUP  
**Prompt:** `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md`  
**Change class:** C4 (media bytes at existing serving paths)  
**Branch:** `fix/remove-shopmill-watermarks-active-products`  
**STATUS:** `PRODUCTION_COMPLETE`

## Status legend

| State | Meaning | Current |
|-------|---------|---------|
| Audited | Active/public imaged catalog inventoried | **Done** |
| Repaired | Method C + WEBP-normalized outputs | **Done (163)** |
| Shadow verified | Fresh shadow apply + independent verify | **Done (410/410)** |
| Applied to production | Bytes written to live `karzar_karzar_uploads` | **Done 2026-08-11T13:33:11Z** |
| Live verified | Hash/decode/format + public HTTP | **Done (410/410)** |
| Watermark re-audit | Active storefront detector scan | **Done — 0 genuine remaining** |
| Rollback | Automatic rollback on failed post-apply | **Not required** |

## Executive result

```text
STATUS = PRODUCTION_COMPLETE
Production images modified: YES
Rollback required: NO

target serving paths replaced: 410
unique repaired WEBP assets: 163
preapply EXACT_MATCH: 410/410
shadow apply replaced: 410
shadow independent HASH/DECODE/FORMAT: 410/410
production HASH/DECODE/FORMAT: 410/410
public HTTP OK (valid WEBP bytes): 410/410
genuine remaining ShopMill positives (HR-confirmed / remediated set): 0
auto-only detector hits (Mitutoyo yellow dials, known FP class): 2
DB/catalog path mutation: NONE
```

## Production operation (2026-08-11 UTC)

| Item | Value |
|------|-------|
| VPS | `195.177.255.198` (`karzar-vps`) |
| Hostname | `srv5944957438` |
| Container | `lathe_api` |
| Volume | `karzar_karzar_uploads` |
| Container storage root | `/app/data/uploads/products` |
| Host storage root | `/var/lib/docker/volumes/karzar_karzar_uploads/_data/products` |
| Apply timestamp | `20260811T133311Z` |
| Prior backup (kept) | `/opt/karzar/backups/shopmill-preapply-20260811T123615Z` |
| Final pre-apply backup | `/opt/karzar/backups/shopmill-preapply-final-20260811T133243Z` |
| Evidence dir | `/opt/karzar/backups/shopmill-production-apply-20260811T133311Z` |
| Shadow base | `/tmp/karzar-shopmill-shadow-20260811T133126Z` |
| Rollback script | `.../shopmill-preapply-final-20260811T133243Z/rollback_shopmill_from_final_backup.py` |

## Format normalization (gate)

All 410 destinations are `.webp`; staged Method C repairs were `.png`/`.jpg`.

- Generated WEBP-normalized repairs: `.local-rescue/shopmill-watermark-cleanup/repaired_assets_webp/` (163)
- Manifest with serving finals: `remediation-manifest.serving-webp.csv`
- Apply helper writes atomically (`temp` + `os.replace`) and encodes to destination suffix
- Independent verify requires actual Pillow format `WEBP` under `.webp` paths (`FORMAT_BAD=0`)

## Catalog integrity (post-apply)

Live DB snapshot (no mutations by this task):

| Metric | Value |
|--------|------:|
| `products` total | 5918 |
| `is_active=true` AND `deleted_at IS NULL` | 1410 |
| `product_images` total | 1194 |
| Active image rows | 1193 |
| Remediated paths still present in DB URLs | 410/410 |

Note: earlier staging docs labeled ~5901 as “active”; live `is_active=true` is 1410. Active-with-images **1193** matches the prior image-row figure. Cleanup replaced file bytes only.

## Public serving

- URL form: `https://api.karzartools.com/static/uploads/products/{rel_path}`
- HTTP 200 for all 410; body magic = WEBP (`RIFF…WEBP`)
- `Content-Type` remains `application/octet-stream` (pre-existing StaticFiles behavior; not introduced by this apply)

## Watermark re-audit

Scanned all **1193** active (`is_active=true`, `deleted_at IS NULL`) product image files with `detect_shopmill_file`.

| Check | Result |
|-------|--------|
| Remediated 410 detector-positive | **0** |
| Prior HR-confirmed still positive | **0** |
| Auto-only new hits | **2** — Mitutoyo dial indicators `2137/34ec949768f70fa7.webp`, `2388/e1f3661baf5f8d01.webp` (yellow dial faces; same false-positive class previously excluded by HR-only confirmation policy) |

Artifacts: `postapply-watermark-audit.json`, `postapply-watermark-positives.csv`.

## Sidecar `.shopmill-bak` files

Apply created **410** `*.webp.shopmill-bak` sidecars beside live targets (pre-replace copies). Full-tree rollback uses the final backup under `/opt/karzar/backups/`; sidecars are additional local safety and were **not** deleted.

## Durable local artifacts (gitignored)

```text
.local-rescue/shopmill-watermark-cleanup/
  repaired_assets/           # Method C sources (163)
  repaired_assets_webp/      # serving-normalized WEBP (163)
  repaired-assets.sha256
  repaired-assets-webp.sha256
```

## Tooling

| Path | Role |
|------|------|
| `scripts/audit_active_product_shopmill_watermarks.py` | Offline audit/remediate/verify |
| `scripts/shopmill_watermark/` | Detect / remediate / inventory / preflight |
| `scripts/apply_shopmill_watermark_remediations.py` | Dry-run/apply with `--require-exact-match` |
| `scripts/shopmill_production_preflight.py` | Read-only VPS preflight CLI |

## Tests / validation

```text
pytest tests/test_shopmill_watermark_detect.py tests/test_shopmill_production_preflight.py --noconftest  → 7 passed
python3 aods/tools/aods_validate.py  → run at completion
```
