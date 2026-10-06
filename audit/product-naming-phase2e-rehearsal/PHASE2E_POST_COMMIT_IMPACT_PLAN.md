# Phase 2E — post-commit impact plan (analysis only)

Phase 2E rehearsal uses direct PostgreSQL `UPDATE products SET name = …` plus
`INSERT INTO product_change_logs` inside a rolled-back transaction. It does **not**
invoke `ProductService.update_product` or admin API handlers.

## What a future Phase 2F commit would need

| Area | Phase 2E behavior | Likely Phase 2F need |
|------|-------------------|----------------------|
| **Database** | Transient name + change log | Same transactional path with `COMMIT` after owner authorization |
| **Slug / URL** | Name-only SQL; slug unchanged in rehearsal | Confirm ORM/admin path still does not auto-regenerate slug on name-only change (`app/crud/product.py`); no slug migration in 2F unless separate policy |
| **SEO** | `meta_title` / `meta_description` untouched | No change expected; cohort has `SEO_impact_rows = 0` in Phase 2D freeze |
| **Hesabfa** | Not called | Real admin update path may call `ensure_product_in_hesabfa` — Phase 2F should use a DB-only apply path or explicit post-apply reconcile, not blind API update |
| **Search** | Not invoked | PostgreSQL-backed product search; no external index rebuild observed for name-only field |
| **Cache / Redis** | Not invoked | `distributed_lock` uses Redis for locks only; no product-name cache invalidation hook found on name update |
| **Sitemap / frontend** | Not invoked | Storefront reads live API/DB; no redeploy required for name text alone |
| **API deploy** | Not required for rehearsal | No OpenAPI shape change for Product.name string values |

## Recommended Phase 2F follow-ups (not executed in 2E)

1. Owner-signed authorization separate from this rehearsal PR.
2. Repeat drift + collision gates immediately before commit.
3. Optional: lightweight post-commit spot-check (47 names, 0 rehearsal reason logs persisted).
4. Document whether Hesabfa display name must be synced manually or via controlled job.

## Phase 2E explicit non-actions

- No cache invalidation
- No search refresh job
- No sitemap regeneration
- No deploy
- No Hesabfa / SMS / payment / queue side effects
