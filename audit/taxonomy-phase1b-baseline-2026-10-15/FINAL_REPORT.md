# Karzar Taxonomy Phase 1B — Current Baseline

**Collected:** 2026-10-15T09:34:39Z
**Git SHA:** f9ba7b034088129d129e432fe6faab0f50377850

## Safety
PRODUCTION_MUTATION=NO | CATEGORY_MUTATION=NO | PRODUCT_MUTATION=NO | DEPLOYMENT=NO

## Current category truth
{
  "total_categories": 135,
  "l1": 12,
  "l2": 81,
  "l3": 42,
  "depth_gt_3": 0,
  "leaves": 111,
  "selectable": 111,
  "empty_categories": 35,
  "categoryless_live_products": 0,
  "non_leaf_product_assignments": 0,
  "invalid_category_assignments": 0,
  "orphans": [],
  "cycles": [],
  "duplicate_sibling_names": 0,
  "duplicate_slugs": 0
}

## Drift vs Phase 0B (2026-09-27)
{
  "anchor_snapshot": "2026-09-27",
  "category_total_delta": -3,
  "l1_delta": -3,
  "l2_delta": 0,
  "l3_delta": 0,
  "leaves_delta": -3,
  "selectable_delta": 0,
  "empty_delta": -3,
  "categoryless_delta": 0,
  "live_products_delta": 0,
  "sellable_delta": 4,
  "visible_delta": 0,
  "anchor": {
    "snapshot_date": "2026-09-27",
    "categories": 138,
    "l1": 15,
    "l2": 81,
    "l3": 42,
    "depth_gt_3": 0,
    "leaves": 114,
    "selectable": 111,
    "empty_categories": 38,
    "categoryless_live_products": 0,
    "live_products": 6536,
    "sellable": 716,
    "storefront_visible": 1368
  },
  "current_structure": {
    "total_categories": 135,
    "l1": 12,
    "l2": 81,
    "l3": 42,
    "depth_gt_3": 0,
    "leaves": 111,
    "selectable": 111,
    "empty_categories": 35,
    "categoryless_live_products": 0,
    "non_leaf_product_assignments": 0,
    "invalid_category_assignments": 0,
    "orphans": [],
    "cycles": [],
    "duplicate_sibling_names": 0,
    "duplicate_slugs": 0
  },
  "current_global": {
    "live": 6536,
    "active": 1585,
    "priced": 4272,
    "imaged": 1464,
    "visible": 1368,
    "pt_missing": 5878,
    "available": 3811,
    "sellable": 720,
    "pt_assigned": 658
  }
}

## Legacy migration script
Do **not** run `scripts/catalog_taxonomy_migrate.py --apply`. It relies on non-authoritative `CATEGORY_ALIASES`, can create categories via ORM, and predates the seven-domain Phase 1B constitution / `KZ.CAT.*` identity model.

## Next review wave (recommendation)
1. **TX-OWNER-001 scope cohort** (owner-scope candidates) — highest governance risk, product-level decomposition required before any exit.
2. **Mixed-semantic parents** (e.g. لوازم جانبی صنعتی) — accessory decomposition.
3. **Helicoil / thread-repair** structural cohort — domain boundary vs Cutting/Thread Repair.
4. **Numeric category ID dependencies** in import scripts — remap planning.

## Correction pass (2026-10-15T09:45:55Z)

- Preserved original evidence: `/home/shebahati/Projects/Karzar/audit/taxonomy-phase1b-baseline-2026-10-15/preserved-evidence/dd7ab67ff10d`
- Removed L1 categories (Phase 0B → current): [186, 187, 188]
- Megamenu dangling refs: {'missing_refs': 3, 'historical_removed_refs': 3}
- Helicoil cohort categories: 1 (cat 55 direct=29)
- Numeric deps: raw=63 deduped=44 generated_skips=6680
