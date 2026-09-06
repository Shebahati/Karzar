# Task record — KNOW-target-catalog-reconciliation

| Field | Value |
|-------|-------|
| NODE_ID | KNOW-target-catalog-reconciliation |
| Archetype | KNOW |
| Prompt | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| Date | 2026-09-06 |
| TASK_ID | CAT-004 |
| Change class | C1 (additive READ-ONLY tooling; not C4 — no catalog writes) |
| Allowlist | `scripts/catalog_target/**`, `scripts/reconcile_target_catalog.py`, `tests/test_catalog_target_reconciliation.py`, `data/catalog-target/**`, `aods/reports/tasks/**`, `aods/registry/document-registry.yaml` (unclassified_allow glob only), `project-management/**` |

## Authority (origin/main)

- `docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md:64-69` — Category A local only; fail-closed production writes; agents MUST NOT write production catalog data
- `docs/architecture/data-ingestion-policy.md:65-75` — no invent; provenance; ban default live-API imports
- `app/core/constants.py:4` — `TOMAN_TO_RIAL = 10`
- `app/utils/public_catalog.py:106-152` — imageless products hidden when `STOREFRONT_HIDE_IMAGELESS_PRODUCTS`
- `app/core/config.py:20` — flag default True

## Source verification

`KARZAR_TARGET_SOURCE_DIR` unset. No approved Products-and-Data files in this workspace. Legacy repo CSVs (`data/imports/insize_products.csv`, `all_products.csv`) are PDF parses, not product-scope authority. Image-only `active-products.csv` is not a full catalog snapshot. Live DB unavailable.

## Resolved target

No load. No API. No DB write.

```
python3 scripts/reconcile_target_catalog.py --output-dir data/catalog-target
```

PRODUCTION MUTATION: ZERO. APPLY flags exit 2.

## Counts (this workspace run)

| Metric | Value |
|--------|-------|
| current products observed | 0 (evidence unavailable, non-live) |
| Target SKUs | 0 (product-scope sources missing) |
| KEEP/UPDATE/CREATE/DEACTIVATE/REVIEW | 0/0/0/0/0 |
| INSIZE target | 0 |

## Tests

```
python3 -m unittest tests.test_catalog_target_reconciliation -v
```

19 passed.

## Proposed next human step (NOT run)

1. Point `KARZAR_TARGET_SOURCE_DIR` at the business-maintained Products and Data set.
2. Provide a full current-catalog snapshot CSV or a local READ-ONLY DB.
3. Re-run this tool. Review REVIEW rows. Separate APPLY node only after that — HC-09 / HC-13.

STATUS: COMPLETE for READ-ONLY tooling; APPLY blocked.
