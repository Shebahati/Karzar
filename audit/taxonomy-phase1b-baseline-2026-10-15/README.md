# Taxonomy Phase 1B — production baseline (read-only)

Collected **2026-10-15** against `karzar_staging` on `srv5944957438`.

- **Runner:** `python3 scripts/audit_taxonomy_phase1b_baseline.py`
- **Mutation:** none (read-only transactions only)
- **Manifest:** `05-PHASE1B-CURRENT-TARGET-WORKING-MANIFEST.csv` — all rows `review_status=UNREVIEWED` unless noted in `notes`

Do not run `scripts/catalog_taxonomy_migrate.py --apply` for Phase 1B work.
