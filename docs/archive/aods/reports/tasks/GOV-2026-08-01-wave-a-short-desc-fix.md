# Wave A follow-up — INSIZE caliper `short_description` 0/01 rewrite

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Owner order** | Priority 1 of caliper residual queue («شروع کن») |
| **Destination** | `https://api.karzartools.com/api/v1` |
| **Category** | B (continues Wave A Owner authority) |
| **Scope** | 43 INSIZE `category_id=57` SKUs whose `short_description` still contained `دقت 0/01` |

## Code (PR)

`scripts/enrich_insize_from_shopmill.py`:

- Port corrupt slash-decimal merge helpers (`is_corrupt_slash_decimal`, replace-on-merge).
- `text_has_corrupt_slash_decimal` detects `0/01` / `۰/۰۱` in marketing blobs.
- Rebuild `short_description` + `meta_description` from safe tech facts (never re-emit corrupt tokens).
- Tests: `tests/test_enrich_insize_malformed_accuracy.py` (6).

## Dry-run

Scoped inventory of the 43 SKUs → **43 / 43** payloads · `zero_price_writes=true` · unmatched=0.

## Apply

```bash
KARZAR_API_BASE=https://api.karzartools.com/api/v1 \
KARZAR_ALLOW_PRODUCTION_WRITE=1 \
KARZAR_INGESTION_CATEGORY=B \
python3 scripts/enrich_insize_from_shopmill.py \
  --reuse-crawl \
  --site-inventory data/imports/insize/shopmill/insize_cat57_short_fix_inventory.json \
  --out-dir data/imports/insize/shopmill/short_fix_0_01 \
  --apply --apply-confirm --force
```

| Metric | Value |
|--------|------:|
| Applied HTTP 200 | **43 / 43** |
| Apply errors | 0 |
| Live `short` still with `0/01` | **0** |
| Live `meta` still with `0/01` | **0** |

Incidental (OEM-sourced, not invented): 35/43 payloads also filled `features.buttons_list` from shopmill when empty.

## Sample (live after)

`1530-500` → `… دقت ±0.08mm …` (was `دقت 0/01`)

## Next (same caliper queue)

1. Suspicious model-like ranges (~29, e.g. `0-301mm`)
2. `display_type` from «نوع کولیس / نوع صفحه نمایش»
3. Empty accuracy/range/resolution/material — only where OEM source exists

## Authority

Owner residual priority list + prior Wave A Category B authorization + ADR-012 + content-only enricher contract.
