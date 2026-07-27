# Dohre (دوهره) official catalog enrichment

## Status (2026-07-25)

| Item | Value |
|------|-------|
| Brand | `DOHRE \| دوهره` |
| Brand ID | **9** |
| Active SKUs on `api.karzartools.com` | **0** (blocker) |
| Official source | https://www.dohrecnc.com/ |
| Apply performed | **No** (0 SKUs) |
| Price / stock writes | **0** (confirmed) |

## Commerce hard constraint

Script allowlists PUT keys only:

- `short_description`
- `description`
- `meta_title`
- `meta_description`
- `specifications` (merge into `technical_specs`)

Forbidden (never read into export files, never sent on PUT):

`price`, `sale_price`, `list_price`, `base_price`, `original_price`, `discount*`,
`stock*`, `availability`, `is_available`, `tax_percent`, `weight_grams`.

`summary.json` → `commerce_policy.zero_price_writes_confirmed: true`.

## Blocker

Brand exists with `product_count=0`. Enrichment cannot apply until active products
are imported and linked to `brand_id=9`.

## Official crawl (partial)

- Category / series HTML pages cached under `pages/`
- Download hub PDF links indexed in `crawl_pdfs.json`
- Model SKU tokens are sparse on marketing HTML (often JS/list-driven); prefer PDFs

## Resume

```bash
cd /home/moahmmad/Projects/Karzar/Website/backend-dohre-enrich

# After SKUs exist on staging:
python scripts/dohre_official_catalog_enrich.py --dry-run
# Review data/imports/dohre/official_catalog/{match_report,dry_run_payloads,summary}.json*
python scripts/dohre_official_catalog_enrich.py --apply --apply-limit 25
```

Re-crawl / refresh official assets:

```bash
# Re-run dry-run after placing new pages/PDFs under data/imports/dohre/official_catalog/
python scripts/dohre_official_catalog_enrich.py --dry-run --reuse-export
```
