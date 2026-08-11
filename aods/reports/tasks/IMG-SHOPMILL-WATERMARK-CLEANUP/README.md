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
- Follow-up issue: [#229](https://github.com/Shebahati/Karzar/issues/229) — correct image MIME types (out of scope for this PR)

## Watermark re-audit

Scanned all **1193** active (`is_active=true`, `deleted_at IS NULL`) product image files with `detect_shopmill_file`.

| Check | Result |
|-------|--------|
| Remediated 410 detector-positive | **0** |
| Prior HR-confirmed still positive | **0** |
| Auto-only new hits | **2** — Mitutoyo dial indicators `2137/34ec949768f70fa7.webp`, `2388/e1f3661baf5f8d01.webp` (yellow dial faces; same false-positive class previously excluded by HR-only confirmation policy) |

Artifacts: `postapply-watermark-audit.json`, `postapply-watermark-positives.csv`.

Post-sidecar regression (repaired WEBP corpus 163 + prior audit): `post-sidecar-watermark-regression.json` → **PASS** (genuine remaining 0; Mitutoyo auto-FPs unchanged).

## Sidecar `.shopmill-bak` cleanup (post-production hygiene)

Apply initially created **410** `*.webp.shopmill-bak` sidecars beside live targets. Canonical rollback remains the external final backup (not the public tree).

| Gate | Result |
|------|--------|
| SIDECARS_FOUND | 410 |
| SIDECARS_APPROVED (mapped to 410 targets) | 410 |
| SIDECAR_HASH_MATCH_ORIGINAL (vs final backup) | 410 |
| UNEXPECTED_SIDECARS | 0 |
| Final backup re-check FILES_BACKED_UP / CHECKSUM_OK | 410 / 410 |
| SIDECARS_DELETED | 410 |
| SIDECARS_REMAINING / UNEXPECTED after delete | 0 / 0 |
| Live HASH/DECODE/FORMAT after cleanup | 410 / 410 / 410 |
| Public HTTP + WEBP magic after cleanup | 410 / 410 |

Evidence: `/opt/karzar/backups/shopmill-sidecar-cleanup-20260811T140000Z/`  
**Live production image bytes were not modified during sidecar cleanup.**

## Post-merge CI fixes (after `9e576d6`)

PR #228 Backend CI initially failed on commit `9e576d6`:

| Job | Failure | Fix |
|-----|---------|-----|
| lint | Ruff `I001` in `tests/test_shopmill_watermark_detect.py` (blank line between third-party imports; `scripts` not first-party under `pyproject.toml` `src`) | Removed blank line; no `# noqa` |
| test | `ModuleNotFoundError: numpy` | Pinned `numpy==2.2.6` in `requirements.txt` (operational ShopMill detect/remediate import numpy; same pattern as Pillow) |

Local gates after fix:

```text
ruff check app tests  → All checks passed!
pytest tests/test_shopmill_watermark_detect.py tests/test_shopmill_production_preflight.py --noconftest  → 7 passed
python3 aods/tools/aods_validate.py  → PASS
```

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
ruff check app tests
pytest tests/test_shopmill_watermark_detect.py tests/test_shopmill_production_preflight.py --noconftest  → 7 passed
python3 aods/tools/aods_validate.py  → PASS
```
