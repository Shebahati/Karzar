# Day 5 — Classification map INSIZE (metrology)

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Session** | Post Day-4 seeds — readiness §5 remainder |
| **Attendees** | Mohammad Shebahati · Cursor |
| **Owner order** | «گام بعدی — classification map — شروع کن» |
| **Parents** | Taxonomy v0 metrology · Property Dictionary v0 · SPEC-data-transformation-architecture §3.1 · Playbook §4.5 · FOUNDATION_IMPLEMENTATION_READINESS §5 step 5 · UD-03 A |

## Scope

**In:** Git `MAPPING-TABLE` taxonomy classify rules for one brand (INSIZE / `brand_id=3`) against closed taxonomy v0 concept_ids; offline coverage against `data/imports/insize_products.csv`.

**Out:** Second Category DAG · inventing taxonomy nodes · Facts / dual-write · `PRODUCT_CLASSIFIED_AS` edge projector (KB-001 Day-2 three-edge freeze) · admin/PDP UI · production apply.

## Deliverable

`docs/architecture/specs/seeds/classification-map-insize-v0-metrology.json`  
Validated by `tests/test_classification_map_insize_v0.py`

## Evidence citations

- Transform map layer: `docs/architecture/specs/SPEC-data-transformation-architecture.md:81`
- Git SoT for maps: `docs/architecture/specs/SPEC-data-transformation-architecture.md:85`
- Classification methods + unknown → unclassified: `docs/architecture/specs/SPEC-product-import-enrichment-playbook.md:184-194`
- Closed type example: `docs/architecture/specs/SPEC-knowledge-graph-registry.md:92-101`
- Sequence step 5: `docs/architecture/specs/FOUNDATION_IMPLEMENTATION_READINESS.md:156`
- Brand id: `scripts/seed_brands.py` INSIZE id=3

## Notes / open

- Families outside taxonomy v0 (tape, level, angle, …) → `unclassified_pending_taxonomy` (domain-only or null); stewardship may extend taxonomy later.
- Inside micrometers → `fam.micrometers` without invented `type.micrometer.inside`.
- Next readiness step: admin read-only Knowledge views (still no dual-write).
