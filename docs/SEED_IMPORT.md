# Catalog seed & import pipeline

Official workflow for loading a real Karzar catalog (categories, brands, products, images, storefront content).

## Prerequisites

- PostgreSQL running (`alembic upgrade head`)
- Dev/staging env with `DEBUG=true` for first-time bootstrap
- CSV/PDF source files from supplier price lists (when importing)

## Recommended order

```
1. seed_categories.py      → category tree (max depth 3)
2. seed_brands.py          → brand master data
3. seed_products_from_csv.py → bulk products from CSV
4. import_insize_images_from_tosag.py → image URLs (optional)
5. parse_price_list_pdfs.py → extract CSV from PDFs (offline prep)
6. seed_storefront.py      → blog posts, hero slides (CMS)
```

## Scripts reference

| Script | Purpose | Typical command |
|--------|---------|-----------------|
| `scripts/setup-dev.sh` | venv + deps | `./scripts/setup-dev.sh` |
| `scripts/seed_categories.py` | Full category tree + spec template keys | `python scripts/seed_categories.py` |
| `scripts/seed_brands.py` | Brand rows | `python scripts/seed_brands.py` |
| `scripts/seed_products_from_csv.py` | Import SKU, price, specs from CSV | `python scripts/seed_products_from_csv.py path/to.csv` |
| `scripts/import_insize_images_from_tosag.py` | Attach image URLs to Insize SKUs | `python scripts/import_insize_images_from_tosag.py` |
| `scripts/parse_price_list_pdfs.py` | PDF → intermediate CSV | `python scripts/parse_price_list_pdfs.py ./pdfs/` |
| `scripts/seed_storefront.py` | Blog + hero CMS content | `python scripts/seed_storefront.py` |
| `scripts/backup_db.sh` | DB dump before bulk import | `./scripts/backup_db.sh` |
| `scripts/restore_db.sh` | Restore from dump | `./scripts/restore_db.sh backups/....sql.gz` |

Docker equivalents:

```bash
docker compose exec app python scripts/seed_categories.py
docker compose exec app alembic upgrade head
```

## Safety rules

1. **Backup first** — `./scripts/backup_db.sh` before destructive seeds.
2. `seed_categories.py` may delete existing products when reseeding — never run on production without a maintenance window.
3. Product images are **URL-based** (no multipart upload storage). Validate URLs are public HTTPS; SSRF guard rejects private hosts.
4. `category_id` is required on every product; tree depth must not exceed 3 levels.
5. After import, smoke test: PLP filter, PDP detail, checkout with `DEV-CHECKOUT-001` (dev bootstrap SKU).

## Dev bootstrap (empty DB)

`app/core/startup.py` seeds a sample product `DEV-CHECKOUT-001` when the catalog is empty. See [LOCAL_DEV_FRONTEND.md](LOCAL_DEV_FRONTEND.md).

## CI vs local

- Local pytest defaults to SQLite (`tests/conftest.py`).
- CI uses Postgres (`USE_POSTGRES_TESTS=1`) to catch JSONB/GIN differences.
- Run Postgres-backed tests before large imports:

```bash
USE_POSTGRES_TESTS=1 pytest tests/test_jsonb_filters.py -q
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Category depth error | Parent chain > 3 levels; flatten tree |
| Image URL rejected | Host must be public; no `localhost`/`10.x` |
| Duplicate SKU | CSV dedupe or soft-delete old product first |
| Spec filters empty | Run categories seed; verify `spec-filter-options` for category id |
