# INSIZE shopmilltools.com enrichment — run report

Branch tooling: `scripts/enrich_insize_from_shopmill.py`  
Crawl helper: `scripts/shopmill_insize_crawl.py` (prices stripped from crawl output)  
Local artifacts: `data/imports/insize/shopmill/` (under gitignored `/data/` — force-add selected evidence)

## Commerce policy (confirmed)

- **price_writes: 0**
- **stock_writes: 0**
- PUT payloads allowed keys only: `short_description`, `description`, `meta_title`, `meta_description`, `specifications`
- Export / inventory stripped of all price/stock/availability keys
- `assert_payload_safe` + nested forbidden-key scan before every dry-run line and every PUT
- Apply report column `price_fields_written=none`

## Source

- SoT: [shopmilltools.com](https://shopmilltools.com) WooCommerce Store API (`/wp-json/wc/store/v1/products?search=insize`)
- Attribute tables on INSIZE PDPs (Persian labels) → locked measurement `technical_specs` + full factual `source_attributes`
- Never invent values; fill-empty merge only (conflicts keep existing)

## Locked measurement schema

`technical_specs` EN canonical keys only:

`range`, `accuracy`, `resolution`, `material`, `standard`, `battery_type`

All other factual shopmill attributes preserved under `source_attributes` (e.g. کشور سازنده, نوع کولیس, گام, …). Country-of-origin is never written as `material`.

## Counts (dry-run)

| Metric | Count |
|--------|------:|
| Karzar INSIZE catalog | 872 |
| shopmill INSIZE rows (SKU’d) | 867 |
| Matched (exact / unique suffix) | 861 |
| Skipped — shopmill empty attributes | 6 |
| Unmatched — SKU not on shopmill | 5 |
| Ambiguous | 0 |
| Content payloads ready | 861 |
| Measurement-key fills (subset) | 694 |
| Country-only attr fills | 167 |

### Unmatched SKUs (left alone)

`7114-950`, `4150-2501`, `4150-250`, `4150-1301`, `4150-130`

### Skipped (no shopmill specs)

`4139-24T`, `4129-16R`, `2878-6A`, `7142-5`, `4918-600`, `3109-300`

## Staging apply

| Metric | Count |
|--------|------:|
| Confirmed content-only PUTs (`applied.csv` ok) | **219** |
| Remaining to resume | 642 |
| Transient SSL failures recorded | 2 |
| Auth expiry mid-batch (first run) | 640 → resume with re-login |

- All successful rows: `price_fields_written=none`
- Allowlist only: `short_description`, `description`, `meta_title`, `meta_description`, `specifications`
- Resume (re-login on 401, checkpoint every 25):

```bash
PYTHONPATH=. python3 scripts/enrich_insize_from_shopmill.py \
  --reuse-crawl --reuse-export \
  --apply --apply-confirm --sleep 0.2
```

## Resume

```bash
cd backend-insize-shopmill  # worktree on feat/insize-shopmill-spec-enrichment

# Optional fresh crawl (rate-limited)
python3 scripts/enrich_insize_from_shopmill.py --crawl --dry-run

# Dry-run with existing crawl + site inventory
PYTHONPATH=. python3 scripts/enrich_insize_from_shopmill.py \
  --reuse-crawl \
  --site-inventory /path/to/site_inventory.json \
  --dry-run

# Apply (resume-safe via applied.csv)
PYTHONPATH=. python3 scripts/enrich_insize_from_shopmill.py \
  --reuse-crawl --reuse-export \
  --apply --apply-confirm --sleep 0.35
```

## Safety vs legacy `shopmill_insize_sync.py`

Legacy sync creates products and writes `base_price` / `stock_quantity`. **Do not use it for this enrichment.** This script is content-only.
