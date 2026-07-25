# Scripts inventory

Operational and maintenance scripts under `scripts/` and `deploy/staging/scripts/`.

## Backup & restore

| Script | Purpose |
|--------|---------|
| `scripts/backup_db.sh` | Local PostgreSQL dump → `./backups/` |
| `scripts/restore_db.sh` | Restore dump into target DB |
| `scripts/backup_uploads.sh` | Tar uploads volume |
| `scripts/restore_uploads.sh` | Restore uploads archive |
| `scripts/backup_offsite_sync.sh` | Sync `./backups/` to `BACKUP_OFFSITE_URI` (S3/R2) |
| `deploy/staging/scripts/install-backup-cron.sh` | Install daily backup cron on VPS |
| `deploy/staging/scripts/restore-db-staging.sh` | Staging-specific DB restore helper |

## Deploy & smoke

| Script | Purpose |
|--------|---------|
| `deploy/staging/scripts/deploy-backend.sh` | Rebuild/restart API container on VPS |
| `deploy/staging/scripts/deploy-frontend.sh` | Build Storefront + Admin images (build-args only) |
| `deploy/staging/scripts/smoke-staging.sh` | Post-deploy hard smoke (API/admin/shop) |
| `deploy/staging/scripts/bootstrap-vps.sh` | Initial VPS setup |
| `deploy/staging/scripts/remediate-staging.sh` | One-off staging remediation |
| `deploy/staging/scripts/enable-hsts.sh` | Enable HSTS on reverse proxy |
| `deploy/staging/scripts/export-local-db.sh` | Export local DB for staging import |

## Catalog seed & import

| Script | Purpose |
|--------|---------|
| `scripts/seed_categories.py` | Seed category tree |
| `scripts/seed_brands.py` | Seed brands |
| `scripts/seed_brand_logos.py` | Attach brand logo assets |
| `scripts/seed_products_from_csv.py` | Bulk product import from CSV |
| `scripts/seed_storefront.py` | Dev storefront demo data |
| `scripts/seed_category_images.py` | Category image URLs |
| `scripts/import_price_lists.py` | Import supplier price lists |
| `scripts/parse_price_list_pdfs.py` | Parse PDF price lists |
| `scripts/reconcile_prices_availability.py` | Reconcile prices vs availability flags |
| `scripts/catalog_remediation.py` | Catalog data cleanup |
| `scripts/remediate_standard_leaves.py` | Fix depth-3 leaf categories |
| `scripts/materialize_product_images.py` | Download/persist remote image URLs |
| `scripts/mirror_product_images.py` | Mirror images to local storage |

## Supplier / brand crawlers

| Script | Purpose |
|--------|---------|
| `scripts/mitutoyo_import.py` | Mitutoyo catalog import |
| `scripts/mitutoyo_crawl.py` | Mitutoyo web crawl |
| `scripts/mitutoyo_discover.py` | Mitutoyo SKU discovery |
| `scripts/import_mitutoyo_images_from_official.py` | Mitutoyo official images |
| `scripts/import_mitutoyo_images_from_official_uk.py` | Mitutoyo UK images |
| `scripts/azarsanat_import.py` | Azarsanat import |
| `scripts/azarsanat_crawl.py` | Azarsanat crawl |
| `scripts/azarsanat_rebrand.py` | Azarsanat rebrand pass |
| `scripts/shopmill_insize_sync.py` | Shopmill/Insize sync |
| `scripts/shopmill_insize_crawl.py` | Shopmill/Insize crawl |
| `scripts/insize_price_update.py` | Insize price refresh |
| `scripts/import_insize_images_from_tosag.py` | Insize images from Tosag |
| `scripts/import_dasqua_images_from_official.py` | Dasqua official images |
| `scripts/import_shopmill_brand_images.py` | Shopmill brand images |

## Hesabfa & ops misc

| Script | Purpose |
|--------|---------|
| `scripts/clear_hesabfa_pulled_stock.py` | Clear legacy Hesabfa-pulled stock columns |
| `scripts/publish_vernier_article.py` | One-off CMS/article publish |
| `scripts/setup-dev.sh` | Local dev environment bootstrap |

## Misc

Remaining one-off utilities under `scripts/` (brand logo assets in `scripts/brand_logo_assets/`, etc.) — run with `python scripts/<name>.py --help` or read module docstring before use.

See [OPERATIONS.md](./OPERATIONS.md) for RPO/RTO, restore drills, and alerting hooks.
