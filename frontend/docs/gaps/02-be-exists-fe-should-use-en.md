# Backend Exists — Frontend Must Consume (Current Gap List)

**Date:** 18 July 2026  
**Audience:** Frontend engineers / QA  
**Base path:** `/api/v1`  
**Scope:** Endpoints implemented in `Karzar-main` that the frontend either still ignores, only partially consumes, or should deepen after the July 2026 remediation.

> **Important:** The earlier audit listed statistics, bulk stock, change-log, audit-logs, user soft-delete, order archive, and password reset/change as **MISSING_FE**. Those are now **wired** in `admin-panel` / Storefront account security. This document is the **post-remediation** truth.

---

## 1. Executive summary

| Bucket | Status |
|--------|--------|
| Core commerce + CMS admin CRUD | Consumed |
| Ops APIs (statistics, bulk stock, change-log, audit, soft-delete/archive) | Consumed (deepen UX) |
| Password reset / change-password | Consumed on `/account/security` (deepen entry points) |
| Still unused by product UI | `POST /auth/register`, `/articles/*` alias, system `/health|/ready|/metrics` |
| Architectural partial | Server cart vs Zustand SoT |

---

## 2. Truly unused (product UI)

| Method | Path | Auth | FE status | Recommendation |
|--------|------|------|-----------|----------------|
| POST | `/auth/register` | Public* | No screen | Keep disabled via `ALLOW_PUBLIC_REGISTER=false` **or** add Storefront register if policy changes |
| GET | `/articles/`, `/articles/{slug}` | Public | Uses `/blog/` | Optional alias client; no action required |
| GET | `/health`, `/ready` | Public | Not in apps | Wire to deploy probes / status page |
| GET | `/metrics` | Public (if enabled) | Not in apps | Prometheus scrape only |
| GET | `/`, `/api/v1` | Public | N/A | Debug only |

\*Blocked when `ALLOW_PUBLIC_REGISTER=false`.

---

## 3. Wired but should be consumed more deeply

| Area | Endpoints | Current FE | Hardening tasks |
|------|-----------|------------|-----------------|
| Cart SoT | `GET/PUT/DELETE /cart`, `POST /cart/merge` | Service + best-effort sync; Zustand UX cache | Surface stock conflicts after `GET /cart`; block checkout on divergent OOS lines |
| Tracking timeline | `GET /orders/track/{code}` | Account order detail + success | Prefer server `timeline`; label client fallback as estimated |
| Catalog meta | `GET /products/?skip&limit` | Storefront load-more; admin pagination | Ensure every admin list uses `meta.total_count` consistently |
| Spec labels | `GET /categories/spec-labels` | Boot fetch + hardcoded fallback | Reduce fallback reliance; fail soft with toast |
| Payment retry | `POST /payments/init` | Checkout retry after order create | E2E when `sessionStorage` cleared; durable pending-order key |
| Statistics | `GET /products/statistics` | Admin dashboard | Feed Reports page until dedicated `/reports` exists |
| Bulk stock | `POST /products/bulk/stock-adjust` | Products multi-select dialog | Require reason; multi-page selection |
| Change log | `GET /products/{id}/change-log` | Product edit section | Filter by price vs stock events |
| Audit logs | `GET /users/audit-logs/list` | `/audit-logs` page | Deep-link from entity pages with `entity_type`/`entity_id` |
| Password lifecycle | `/auth/password-reset/*`, `/auth/change-password` | `/account/security` | Link from `/login`; clearer ApiError mapping |
| Soft-delete user | `DELETE /users/{id}` | Customer danger zone + step-up | Confirm copy + redirect list |
| Archive order | `DELETE /orders/{id}` | Order action panel + step-up | Only on terminal statuses; refresh list |

---

## 4. Explicitly correctly unused (by design)

| Endpoint family | Why FE does not call it from that app |
|-----------------|----------------------------------------|
| Admin CMS write from Storefront | Role separation |
| `POST /payments/refund` from Storefront | Admin-only + step-up |
| Storefront OTP from Admin | Admin uses password login |
| Product write from Storefront | Catalog is read-only for customers |

---

## 5. QA checklist (live API, `USE_MOCK=false`)

1. Dashboard numbers match `/products/statistics` (not sampled `base_price` sums).  
2. Bulk stock adjust updates multiple SKUs; change-log gains rows.  
3. Destructive step-up actions appear in `/audit-logs`.  
4. Password reset request/confirm and change-password succeed against real auth.  
5. Guest cart merges after OTP (`POST /cart/merge`).  
6. Catalog/admin lists can reach items beyond the first page via `meta`.  
7. Payment-init failure shows tracking + successful retry path.

---

## 6. Deprecation guidance for backend

Before removing `POST /auth/register` or `/articles/*`, confirm with FE. Current Storefront depends on OTP + `/blog/`. With `ALLOW_PUBLIC_REGISTER=false`, register removal is low risk if documented.

---

## 7. Traceability

| Layer | Path |
|-------|------|
| Storefront services | `Storefront/src/services/` |
| Admin services | `admin-panel/src/services/` |
| FE-ahead (needs new BE) | `docs/gaps/01-fe-ahead-be-needed-en.md` |
| Historical full matrix | `docs/audits/01-api-gaps-en.md` |

---

*Persian companion: `docs/gaps/02-be-exists-fe-should-use-fa.md`*
