# Wave A — All INSIZE calipers (cat 57) live Category B

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Owner order** | «موج بعدی همه‌ی کولیس‌های اینسایز» |
| **Destination** | `https://api.karzartools.com/api/v1` |
| **Category** | B |
| **Scope** | brand INSIZE · `category_id=57` · **158 SKUs** |

## Run

```bash
KARZAR_API_BASE=https://api.karzartools.com/api/v1 \
KARZAR_ALLOW_PRODUCTION_WRITE=1 \
KARZAR_INGESTION_CATEGORY=B \
python3 scripts/enrich_insize_from_shopmill.py \
  --reuse-crawl \
  --site-inventory data/imports/insize/shopmill/insize_cat57_live_inventory.json \
  --apply --apply-confirm --force
```

## Match / apply

| Metric | Value |
|--------|------:|
| Inventory (live cat57 INSIZE) | 158 |
| Unmatched | 0 |
| Ambiguous | 0 |
| Already complete (no PUT needed) | 94 |
| Payloads / applied OK | **64 / 64** |
| Apply errors | 0 |
| zero_price_writes | true |

Includes re-touch of prior pilot-20 where merge still had fillable feature fields.

## Live verify (all 158)

| Metric | Value |
|--------|------:|
| Still category 57 | 158 |
| Accuracy with `±` | 81 |
| Accuracy empty (no OEM source / not inventable) | 66 |
| Former corrupt `0/01` fixed this wave | 38 |
| Remaining true `0/01` | **0** |
| One multi-tolerance value containing `/` (not corrupt) | `2385-3` |
| Has range | 106 |
| Has resolution | 74 |

Verify JSON: `aods/reports/tasks/WAVE-A-caliper-insize-cat57-full-verify.json`

## Follow-ups

1. QA suspicious ranges (model-tainted like `0-301mm`).
2. Map `display_type` from shopmill «نوع کولیس / نوع صفحه نمایش».
3. Empty accuracy (66): only fill when OEM source appears — do not invent.
4. 28 `already_complete` rows still have a differing shopmill accuracy kept by conflict policy (non-malformed existing wins) — review if Owner wants OEM-prefer override later.

## Authority

Owner order + ADR-012 Category B + enricher content-only contract.
EOF