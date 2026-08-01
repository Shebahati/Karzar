# Wave A — Caliper pilot 20 (live Category B)

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Owner order** | «پایلوت ۲۰ تا» |
| **Destination** | `https://api.karzartools.com/api/v1` |
| **Category** | **B** (`KARZAR_ALLOW_PRODUCTION_WRITE=1` + `KARZAR_INGESTION_CATEGORY=B`) |
| **Scope** | INSIZE · `category_id=57` · 20 SKUs |

## Selection

Prefer SKUs with core metrology fill + malformed-accuracy replacement from prior local dry-run:

`1103-150/200/300`, `1106-301/302/501/502/503/505/601/602/603/802`, `1108-200/300`, `1114-150/200/300`, `1115-150/300`

## Command shape (secrets omitted)

```bash
KARZAR_API_BASE=https://api.karzartools.com/api/v1 \
KARZAR_ALLOW_PRODUCTION_WRITE=1 \
KARZAR_INGESTION_CATEGORY=B \
python3 scripts/enrich_insize_from_shopmill.py \
  --reuse-crawl \
  --site-inventory data/imports/insize/shopmill/pilot20_live_inventory.json \
  --apply --apply-confirm --apply-limit 20 --force
```

## Results

| Metric | Value |
|--------|------:|
| Applied OK | **20 / 20** |
| Apply errors | 0 |
| zero_price_writes | true |
| payload_forbidden_count | 0 |
| Still category 57 after | 20 |
| Accuracy `0/01` → OEM `±…` | **20 / 20** |
| Remaining slash-corrupt accuracy | 0 |

Verify JSON: `aods/reports/tasks/WAVE-A-caliper-pilot20-verify.json`  
Artifact zip: `/opt/cursor/artifacts/wave-a-caliper-pilot20.zip`

## Sample before → after (accuracy)

| SKU | Before | After |
|-----|--------|-------|
| 1103-150 | `0/01` | `±0.03mm` |
| 1114-150 | `0/01` | `±0.02mm` |
| 1115-300 | `0/01` | `±0.03mm` |

## Follow-ups (not in this pilot)

1. Some `range` values look model-tainted (e.g. `0-301mm`, `0-502mm`) — QA / map fix before next wave.
2. `display_type` still not written by enricher.
3. Expand beyond 20 after Owner review of storefront PDP samples.
4. Recommend rotating live admin password (was present in agent environment earlier this session).

## Authority

- Owner explicit pilot authorization
- ADR-012 Category B controls
- Enricher content-only allowlist (no price/stock)
EOF