# Scripts inventory

Operational and maintenance scripts under `scripts/` and `deploy/staging/scripts/`.

| Script | Purpose |
|---|---|
| `scripts/backup_db.sh` | Local PostgreSQL dump → `./backups/` |
| `scripts/restore_db.sh` | Restore dump into target DB |
| `scripts/backup_uploads.sh` | Tar uploads volume |
| `scripts/restore_uploads.sh` | Restore uploads archive |
| `scripts/backup_offsite_sync.sh` | Sync `./backups/` to `BACKUP_OFFSITE_URI` (S3/R2) |
| `deploy/staging/scripts/smoke-staging.sh` | Post-deploy hard smoke (API/admin/shop) |
| `deploy/staging/scripts/install-backup-cron.sh` | Install daily backup cron |
| `scripts/dry_run_product_seo_descriptions.py` | Read-only SEO short/long stub coverage report (P1; no `--apply`) |
| `scripts/ingestion_boundary.py` | ADR-012 fail-closed helper (`resolve_api_base` / `resolve_asset_base`); requires `KARZAR_ALLOW_PRODUCTION_WRITE=1` + `KARZAR_INGESTION_CATEGORY=B` for production hosts |
| `scripts/publish_seo003_articles.py` | CMS upsert of buyer-intent articles; **Category B** when invoked by `deploy-staging.yml` against the live API |
| `scripts/ops_require_aods_status_check.sh` | Repo-admin helper / verifier for Protect main required checks (`lint`+`test`+`aods`; `OI-GOV-02` CLOSED) |

See [OPERATIONS.md](./OPERATIONS.md) for RPO/RTO, restore drills, and alerting hooks.

Product SEO plan: [architecture/product-seo-descriptions-plan.md](./architecture/product-seo-descriptions-plan.md).
