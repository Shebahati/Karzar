# Phase 2F real apply summary

## Status

**APPLIED_VERIFIED** — owner-authorized live apply on staging (`karzar_staging`).

## Scope

- **47** `products.name` updates (frozen Phase 2D `proposed_name` values)
- **47** `product_change_logs` rows (`field_name=name`, full cohort SHA in `reason`)
- **0** non-target protected-field mutations (in-transaction proof)
- **HOLD canary** `2223-153` not in cohort

## Provenance

| Item | Value |
|------|-------|
| Main at branch base | `9fc607ab90170375069c0d5b11ec33f4f64ae9dd` |
| Apply logic SHA | `8a0ab9347968db1b7f4de4b36c0d86ed2cd6c8dc` |
| Phase 2D candidate SHA256 | `25d586e371431cc371b6ce6432abba6c2da5b1f15102cac9ed187f78ef0052ff` |
| Phase 2E prestate SHA256 | `88ba82d203a0e51224cbbea81eb277cd15cb5f867470fdd7c367bad4098f43e5` |
| PostgreSQL txid | `29255` |
| Backup SHA256 | `eb7ade5cb036ebd63f2cac869aad497327b99b9da2af5e847ae9e09f517188b9` |

## Operations explicitly not performed

- No deploy (API / storefront / admin)
- No Redis / search-index / sitemap jobs
- No Hesabfa write

## Second apply

Post-apply `--preflight-only` reports `ALREADY_APPLIED_BLOCKED` (no writes).
