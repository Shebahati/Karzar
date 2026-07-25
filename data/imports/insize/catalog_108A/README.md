# INSIZE catalogue 108A (2025–2027) enrichment

**Source PDF:** `INSIZE-Dimensional-Metrology-108A-2025-2027.pdf`  
**Edition:** 108A-2025-2027  
**Policy:** content-only (never price / stock / availability)

## Hard constraint

Update payloads may contain **only**:

- `short_description`
- `description`
- `meta_title`
- `meta_description`
- `specifications`

Forbidden: `base_price`, `original_price`, any `*price*`, `discount*`, `stock_*`, `is_available`, `availability`, currency/money fields.

## Artifacts

| File | Role |
|------|------|
| `pdf_text_full.txt` | `pdftotext` extract with `=====PDF_PAGE_N=====` markers |
| `catalog_index.json` | Parsed Code/Range/Accuracy (+ page meta) |
| `site_list.json` | Live INSIZE PLP inventory (commerce fields discarded) |
| `matched.csv` / `matched.json` | Very-high-confidence SKU matches |
| `rejected.csv` | Unmatched / ambiguous (unchanged on site) |
| `dry_run_payloads.json` | Content-only payloads reviewed before apply |
| `applied.csv` | Staging apply log (`price_fields_written=none`) |
| `qa_sample.json` | Post-apply QA sample |

## Resume commands

```bash
cd backend

# Rebuild index from PDF text (or --extract to re-run pdftotext)
python scripts/enrich_insize_from_catalog_108A.py index

# Refresh site list + rematch
python scripts/enrich_insize_from_catalog_108A.py match --refresh-site

# Dry-run (public GET details → payloads; no writes)
python scripts/enrich_insize_from_catalog_108A.py dry-run

# Apply remaining content-only PUTs (skips ids already 200 in applied.csv)
python scripts/enrich_insize_from_catalog_108A.py apply --apply-confirm --sleep 0.35

# QA ≥20 via public API
python scripts/enrich_insize_from_catalog_108A.py qa --limit 20
```

## Match rules (very high confidence only)

1. Exact catalog Code No. = site SKU  
2. Site bare code → **exactly one** catalog lettered variant (e.g. `1111-100` → `1111-100A`)  
3. Otherwise reject (including ambiguous suffixes like `3203-1` → `3203-1A` / `3203-1FA`)
