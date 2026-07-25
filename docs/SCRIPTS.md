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

See [OPERATIONS.md](./OPERATIONS.md) for RPO/RTO, restore drills, and alerting hooks.

Product SEO plan: [architecture/product-seo-descriptions-plan.md](./architecture/product-seo-descriptions-plan.md).
