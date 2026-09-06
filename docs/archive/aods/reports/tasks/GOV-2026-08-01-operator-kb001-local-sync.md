# Operator residual — KB-001 local Alembic + full-catalog projection sync

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Owner order** | «1.» then «خودت انجامش بده» (full catalog, not bootstrap-only) |
| **Env** | Cloud agent VM — native PostgreSQL 16 + uvicorn `127.0.0.1:8000` (no Docker) |
| **ADR** | ADR-012 Category A local only — not staging/prod |

## Phase A — schema (earlier)

`alembic upgrade head` → through `d5e6f7a8b9c0` (`knowledge_edges`) **PASS**

## Phase B — full local catalog seed

```text
python3 scripts/seed_categories.py   → 122 categories
python3 scripts/seed_brands.py       → 22 brands
python3 scripts/seed_products_from_csv.py --csv data/imports/all_products.csv
  CSV rows: 1251
  Eligible (strict): 1064
  Inserted: 1064
  Rejected: 187  (written to data/imports/products_not_imported.csv — not committed)
```

DB counts after seed: **products=1064** (INSIZE `brand_id=3` → **337**), categories=122, brands=22.

## Phase C — projection sync

```json
{
  "products_scanned": 1064,
  "articles_scanned": 0,
  "edges_upserted": 2128,
  "edges_deprecated": 0
}
```

Then created one CMS article (`kb-local-caliper-guide`) linking products 1+2 and re-synced articles:

```json
{
  "products_scanned": 1064,
  "articles_scanned": 1,
  "edges_upserted": 2130,
  "edges_deprecated": 0
}
```

## Phase D — read proof (SQL + API)

`GET /api/v1/knowledge/edges` **total=2132**

| edge_type | status | count |
|-----------|--------|------:|
| PRODUCT_BELONGS_TO_CATEGORY | published | 1065 |
| PRODUCT_BRANDED_AS | published | 1065 |
| ARTICLE_EXPLAINS_PRODUCT | asserted | 2 |

`GET /api/v1/knowledge/products/1/neighborhood` → category + brand present.

## Notes

- This replaces the earlier bootstrap-only proof (1 sample SKU / 2 edges).
- Local `.env` gitignored; not committed.
- Rejected import CSV is a local artifact from strict quality gates — not part of this PR.
- Admin UI (#183) against this API will show the full edge list under `/knowledge`.

## Human laptop

Optional mirror of the same scripts on your compose stack if you need *your* machine’s DB; agent Category A stack already holds the seeded catalog + edges.
