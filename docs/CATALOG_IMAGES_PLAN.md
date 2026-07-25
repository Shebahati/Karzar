# Catalog main images — 7 brands (Phase A plan)

Live DB (`karzar_staging` @ VPS, 2026-07-25), `deleted_at IS NULL`:

| Brand (site) | ID | Active | With primary | Missing |
|---|---:|---:|---:|---:|
| Mitutoyo \| میتوتویو | 2 | 304 | 111 | 193 |
| INSIZE \| اینسایز | 3 | 872 | 633 | 239 |
| Dasqua \| داسکوا | 4 | 727 | 29 | 698 |
| TERMA \| ترما | 5 | 312 | 0 | 312 |
| ZCC.CT \| زد سی‌سی | 8 | **0** | 0 | 0 |
| ASTPOWER \| ای اس تی پاور | 13 | 975 | 0 | 975 |
| SAN OU \| سانو | 20 | 281 | 0 | 281 |

**Total actionable ≈ 3471** (ZCC has no SKUs yet).

## Official / preferred image sources

1. **Mitutoyo** — `https://shop.mitutoyo.co.uk/media/mitutoyoData/IM/bigweb/{SKU}_z1_jpg.webp` (official CDN). Exact SKU filename match only. Skip if already materialized on `api.karzartools.com`.
2. **INSIZE** — Tosag dealer catalog (`tosag.ch`) via existing high-confidence SKU-on-page matcher; prefer white-bg product shots.
3. **Dasqua** — Official `dasquatools.com` product sitemaps + page `image_product` / og:image; exact `NNNN-NNNN` CODE match.
4. **TERMA / SAN OU / ASTPOWER** — High-res catalog assets on distributor CDN `shopmilltools.com` (`/wp-content/uploads/…`, WC Store API). Match by **model code in product title** (shopmill SKU field often empty). Prefer official manufacturer when discoverable later; do not invent images.
5. **ZCC.CT** — No products in DB → skip until catalog imported.

## Matching strategy

- **Mitutoyo**: SKU as-is → CDN candidate list (`_z1_jpg.webp`, `_jpg.webp`, …); reject `< MIN_BYTES`.
- **INSIZE**: Search Tosag by SKU; require INSIZE manufacturer + SKU on detail page.
- **Dasqua**: Normalize `NNNN-NNNN`; map from crawled CODE index; skip ambiguous codes.
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

1. TERMA (shopmill index) → materialize  
2. SAN OU → materialize  
3. ASTPOWER (high-confidence only) → materialize  
4. Dasqua full sitemap refresh crawl → materialize  
5. Mitutoyo UK CDN for missing → materialize  
6. INSIZE Tosag for missing → materialize  
7. Report gaps; ZCC deferred (0 SKUs)
