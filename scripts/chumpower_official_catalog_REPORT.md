# Chumpower official catalog enrichment — run report

Branch tooling: `scripts/chumpower_official_catalog_enrich.py`  
Local artifacts: `data/imports/chumpower/official_catalog/` (gitignored `/data/`)

## Commerce policy (confirmed)

- **price_writes: 0**
- **stock_writes: 0**
- PUT payloads allowed keys only: `short_description`, `description`, `meta_title`, `meta_description`, `specifications`
- Export strips all price/stock/availability keys; apply asserts commerce-free before each PUT

## Sources

- SoT site: https://www.chumpowerchuck.com/en/ (chucks / tooling)
- Catalog PDFs linked from Download (CDN under `chumpower.com/UserFiles/down/`)
- **Not used for SKUs:** https://www.chumpower.com/en/index.html (PET blow-molding)

## Counts (staging dry-run → apply)

| Metric | Count |
|--------|------:|
| Active Chumpower SKUs exported | 354 |
| Official codes indexed | 2668 |
| Unique Type/SPEC map | 714 |
| Matched (exact code or unique type) | 9 |
| Unmatched (left alone) | 345 |
| Payloads ready | 9 |
| Applied to staging | 9 |
| Apply errors | 0 |

### Applied SKUs (QA set)

`BT50-SF20`, `D32-SF33`, `BA2BT40032501A`, `BE812SA01A`, `BA90103020018A`, `BA90102020006A`, `BA90102020002A`, `BA90103020005A`, `JT2S-SF12-61L`

## Blockers / why coverage is low

1. Most site SKUs are short distributor codes (`35252`, `62420`, …) that **do not appear** as manufacturer Code No. on the official chuck site/PDFs.
2. ~10 site `BA…` codes are absent from the current official PDF/HTML edition (near-family codes exist; no safe unique map without guessing).
3. Type strings like `10S-B10` are often split across PDF columns; not indexed as a single unique Type without inventing joins.

## Resume

```bash
cd backend-chumpower-enrich  # worktree on feat/chumpower-official-catalog-enrichment

python3 scripts/chumpower_official_catalog_enrich.py --rebuild-index
python3 scripts/chumpower_official_catalog_enrich.py --reuse-export --apply --apply-limit 25
```
