# Wave A Week-1 — Caliper gap queue + PD alignment + INSIZE dry-run

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Scope** | L1-56 · `category_id=57` انواع کولیس · INSIZE first |
| **Destination dry-run** | `http://127.0.0.1:8000/api/v1` (Category A) |
| **Live apply** | **Not performed** |

## 1) Gap queue (from live audit Excel)

Source: `data/exports/catalog-audit-2026-08-01/L1-56-اندازه-گیری-دقیق.xlsx`

| Slice | Count |
|-------|------:|
| Products in cat 57 | 446 |
| INSIZE in cat 57 | 158 |
| Template gap rows (cat57) | large (see CSV) |
| PD gap rows (cat57) | 3167 |

Artifacts (also `/opt/cursor/artifacts/wave-a-caliper-2026-08-01/`):

- `01_caliper_products_cat57.csv`
- `01b_caliper_insize_cat57.csv`
- `04_*` / `06_*` gap CSVs

## 2) PD v0 ↔ as-built ↔ enricher alignment

Machine file: `aods/reports/tasks/WAVE-A-caliper-pd-alignment.json`

| PD key | Required | Legacy as-built | Enricher |
|--------|----------|-----------------|----------|
| measurement_range | yes | technical_specs.range | writes `range` |
| resolution | yes | technical_specs.resolution | writes `resolution` |
| accuracy | yes | technical_specs.accuracy | writes `accuracy` |
| display_type | yes | — | **NOT written (blocker)** |
| material / standard_ref / battery_type / data_output / protection_rating | no | mapped | partial |

## 3) Dry-run results (local)

Command:

```bash
KARZAR_API_BASE=http://127.0.0.1:8000/api/v1 \
  python3 scripts/enrich_insize_from_shopmill.py --crawl --dry-run
# then after malformed-accuracy fix:
KARZAR_API_BASE=http://127.0.0.1:8000/api/v1 \
  python3 scripts/enrich_insize_from_shopmill.py --reuse-crawl --dry-run
```

| Metric | Value |
|--------|------:|
| Shopmill rows | 874 |
| Local INSIZE | 337 |
| Matched payloads | 330 |
| zero_price_writes | true |
| payload_forbidden_count | 0 |
| Live INSIZE cat57 SKUs | 158 |
| Of those in local DB + matched | 71 |
| Would fill range / accuracy / resolution | 71 / 64 / 58 |
| All three core | 58 |
| `replace_malformed_accuracy` (0/01 → OEM ±) | 58 |
| Remaining slash accuracy in payload | 0 |
| display_type filled | 0 |

Slice JSON: `aods/reports/tasks/WAVE-A-caliper-dry-run-slice.json`  
Summary: `aods/reports/tasks/WAVE-A-caliper-dry-run-summary.json`

## 4) Enricher fix landed this session

`scripts/enrich_insize_from_shopmill.py`:

- Detect corrupt slash-decimals (`0/01`)
- Do **not** treat them as valid accuracy
- On conflict, if prior is corrupt and shopmill is well-formed → **replace** with explicit `replace_malformed_*` note
- Still keep non-malformed conflicts (no silent overwrite)

Tests: `tests/test_enrich_insize_malformed_accuracy.py` (3 passed)

## 5) Halt before live apply

1. Need Owner Category B authorization for production/live.
2. 87/158 live INSIZE cat57 SKUs absent from local seed — live inventory required for full wave.
3. `display_type` still not auto-filled (PD required) — map from shopmill `نوع کولیس` / `نوع صفحه نمایش` in a follow-up, or accept deferral.
4. Recommend first live pilot: **≤20 SKUs** INSIZE cat57 after Owner OK.

## Authority

- ADR-012 Category A local
- data-ingestion-policy (no invent; versioned pipeline)
- PD seed `property-dictionary-v0-metrology.json` · UD-03 A
- Enricher content-only contract (no price/stock writes)
