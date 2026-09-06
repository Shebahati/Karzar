# Phase A continue — 2026-07-25 evening

Branch: `feat/catalog-images-phase-a-continue`  
Policy unchanged: one primary, very-high confidence only, final URLs on `api.karzartools.com/static/uploads/...`.

## Coverage (VPS `karzar_staging`)

| Brand | Before (morning doc) | After (this run) | Applied this run |
|---|---|---|---|
| Mitutoyo | 111/304 | 111/304 | dry-run only → 0 new |
| INSIZE | 633/872 | 643/872 | dry-run only → 0 new (prior +10 already live) |
| Dasqua | 29/727 | 53/727 | dry-run only → 0 new (prior +24 already live) |
| TERMA | 0/312 | 181/312 | dry-run only → 0 new |
| ASTPOWER | 0/975 | 143/975 | dry-run only → 0 new |
| SAN OU | 0/281 | 62/281 | dry-run only → 0 new |
| ZCC.CT | 0 | 0 | skip |

**No live DB writes / materialize in this continue pass** — every dry-run returned 0 eligible inserts after skipping existing primaries.

## Dry-run reject samples

### TERMA (shopmill, refresh index 214 pages / 198 accepted models)
- already_has_primary: 181
- no_shopmill_model_match: 128 — e.g. `CDE932-1000-J20`, `SDA100-150`, `CD960-500-JAW100`, `TB210`
- ambiguous_shopmill_model: 3 — e.g. `IB210N`

### SAN OU
- already_has_primary: 62
- no_shopmill_model_match: 156 — e.g. `SO-7324` / K11-080 adapter plates not on shopmill index
- ambiguous_shopmill_model: 63 — correctly skipped

### ASTPOWER
- already_has_primary: 143
- no_shopmill_model_match: 829 — mostly numeric legacy SKUs (`367`, `368`, …) without shared model token
- ambiguous_shopmill_model: 3

### Dasqua
- Official sitemap refresh from VPS: **timeout** to `dasquatools.com`
- Laptop sitemap refresh: 2918 URLs (unchanged vs Jul 22 cache)
- Prior full official crawl accepted only ~54 codes (site pages rarely expose CODE)
- Shopmill dry-run: 690 pages / 664 accepted models; **intersection with 667 missing catalog SKUs = 0**
- already_has_primary: 53; no_shopmill_model_match: 667; ambiguous: 7

### Mitutoyo UK (`--missing-only`)
- Catalog matched: 0 / Rejected: 193 all `no_official_cdn_asset`

### INSIZE Tosag
- Very-high imported: 0
- Skipped existing: 643
- Remaining rejects: no_product_candidates 128, sku_not_on_detail_page 86(+14 dup issue codes), not_insize_manufacturer 1

## Blockers

1. **Laptop → shopmilltools.com**: connection timeout (use VPS app container).
2. **VPS → dasquatools.com**: sitemap refresh timed out (laptop can fetch; need cache upload or crawl-from-laptop + apply-on-VPS if revisit).
3. **Local DB incomplete**: not suitable for TERMA/SAN OU apply without tunnel/VPS.
4. **Source coverage ceiling**: remaining gaps lack very-high matches on current authorized sources — do not guess.

## Artifacts

- `data/imports/{terma,sanou,astpower}/imported.csv` + `rejected.csv` (pulled from VPS)
- `data/imports/dasqua_shopmill/imported.csv` + `rejected.csv`
- `data/imports/dasqua/missing_live.csv` + `product_urls_refreshed.txt`
- VPS logs under `/opt/karzar/Karzar/data/imports/*/phase_a_continue_dry.log`

## Resume commands (VPS)

```bash
ssh root@195.177.255.198
cd /opt/karzar/Karzar
# After deploying newer matcher / new source:
docker compose -f docker-compose.yml -f docker-compose.staging.yml exec -T app \
  python scripts/import_shopmill_brand_images.py --brand terma --dry-run --refresh-index --delay 0.12
# Apply only when dry-run imported.csv > 0:
docker compose -f docker-compose.yml -f docker-compose.staging.yml exec -T app \
  python scripts/import_shopmill_brand_images.py --brand terma --delay 0.12
docker compose -f docker-compose.yml -f docker-compose.staging.yml exec -T app \
  python scripts/materialize_product_images.py --brand-ilike TERMA
```
