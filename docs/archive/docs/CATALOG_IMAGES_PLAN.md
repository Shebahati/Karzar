# Catalog main images — 7 brands (Phase A plan)

**Authority (2026-07-30):** Authorized product-image import plan under AODS `CR-019` Option A / `DECISIONS.md` **D16** (Phase-3 pause superseded-for-now).

Live DB (`karzar_staging` @ VPS, **2026-07-25 evening re-measure**), `deleted_at IS NULL`:

| Brand (site) | ID | Active | With primary | Missing | Δ vs morning snapshot |
|---|---:|---:|---:|---:|---|
| Mitutoyo \| میتوتویو | 2 | 304 | 111 | 193 | 0 |
| INSIZE \| اینسایز | 3 | 872 | 643 | 229 | +10 primary |
| Dasqua \| داسکوا | 4 | 727 | 53 | 674 | +24 primary |
| TERMA \| ترما | 5 | 312 | 181 | 131 | +181 primary |
| ZCC.CT \| زد سی‌سی | 8 | **0** | 0 | 0 | skip |
| ASTPOWER \| ای اس تی پاور | 13 | 975 | 143 | 832 | +143 primary |
| SAN OU \| سانو | 20 | 281 | 62 | 219 | +62 primary |

**Total actionable missing ≈ 2278** (ZCC has no SKUs yet).  
Morning snapshot had ≈ 2698 missing; a prior checkpoint already filled ~420 high-confidence images (materialized to `api.karzartools.com/static/uploads/...`).

Progress note: [`docs/CATALOG_IMAGES_PROGRESS_2026-07-25.md`](CATALOG_IMAGES_PROGRESS_2026-07-25.md).

## Official / preferred image sources

1. **Mitutoyo** — `https://shop.mitutoyo.co.uk/media/mitutoyoData/IM/bigweb/{SKU}_z1_jpg.webp` (official CDN). Exact SKU filename match only. Skip if already materialized on `api.karzartools.com`.
2. **INSIZE** — Tosag dealer catalog (`tosag.ch`) via existing high-confidence SKU-on-page matcher; prefer white-bg product shots.
3. **Dasqua** — Official `dasquatools.com` product sitemaps + page `image_product` / og:image; exact `NNNN-NNNN` CODE match. Supplement: shopmill title/model match (`--brand dasqua`) when official pages lack parseable CODE.
4. **TERMA / SAN OU / ASTPOWER** — High-res catalog assets on distributor CDN `shopmilltools.com` (`/wp-content/uploads/…`, WC Store API). Match by **model code in product title** (shopmill SKU field often empty). Prefer official manufacturer when discoverable later; do not invent images.
5. **ZCC.CT** — No products in DB → skip until catalog imported.

## Matching strategy

- **Mitutoyo**: SKU as-is → CDN candidate list (`_z1_jpg.webp`, `_jpg.webp`, …); reject `< MIN_BYTES` / non-photo (eps/bmp).
- **INSIZE**: Search Tosag by SKU; require INSIZE manufacturer + SKU on detail page.
- **Dasqua**: Normalize `NNNN-NNNN`; map from crawled CODE index; skip ambiguous codes. Shopmill: catalog SKU in title + brand tokens.
- **TERMA**: Catalog SKU (e.g. `CB210-150`) must appear in shopmill product name.
- **SAN OU**: Strip `SO-` internal id; extract model keys from name (`K11-080`, `D113`, `003014`, …) → shopmill title must contain key + «سانو/SAN OU».
- **ASTPOWER**: Prefer `AST-*` SKUs and model tokens in name; shopmill title must contain brand + shared model token. Numeric-only legacy SKUs without model → leave unmatched.

## Pipeline

1. Resolve best remote URL (HEAD/GET size; reject tiny thumbs / HTML).
2. Insert `product_images` primary URL only (no price/stock writes).
3. `materialize_product_images.py --brand-ilike …` → download to `data/uploads/products/{id}/` and rewrite to `https://api.karzartools.com/static/uploads/products/…`.
4. Idempotent: skip if primary already on karzartools static host with file present; `--replace` only when swapping watermarked sources.
5. Resume: CSV state under `data/imports/{brand}/` + `--resume`.
6. QA: sample 10/brand visually; write `*_rejected.csv` for unmatched.
7. Legal: rate-limit ≥50–150 ms; public catalog pages only; prefer official/brand CDN; no login walls.

## Execution order

1. TERMA (shopmill index) → materialize — **exhausted** (0 new very-high on 2026-07-25 continue)
2. SAN OU → materialize — **exhausted**
3. ASTPOWER (high-confidence only) → materialize — **exhausted**
4. Dasqua full sitemap refresh crawl + shopmill — **exhausted** (official sitemap reachable from laptop; VPS→dasquatools timed out; shopmill ∩ missing SKUs = 0)
5. Mitutoyo UK CDN for missing → materialize — **exhausted** (193 still `no_official_cdn_asset`)
6. INSIZE Tosag for missing → materialize — **exhausted** (0 new very-high)
7. Report gaps; ZCC deferred (0 SKUs)

## Ops notes (continue run)

- Shopmill / Mitutoyo CDN / Tosag are reachable **from the VPS app container**; shopmill often times out from the laptop network — run imports via `docker compose … exec -T app python scripts/…`.
- Local laptop DB (`karzar_db` @ 127.0.0.1:5435) is **not** a full live mirror (missing TERMA/SAN OU SKUs); always re-measure on VPS.
- Do **not** lower match confidence to fill gaps.
