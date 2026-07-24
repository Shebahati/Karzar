# API Gap Analysis — Detailed English Technical Report

**Date:** 17 July 2026  
**Scope:** Backend `Karzar-main` (`/api/v1`, ~87 HTTP routes) vs Frontend `karzar-frontend` (`Storefront/` + `admin-panel/`)  
**Method:** Exhaustive router inventory (`app/api/endpoints/*` + `include_router`) cross-checked against every `apiClient.*` call in `**/services/**` and auth interceptors. Mock-only UI surfaces included under “FE without BE”.

**Legend**
| Tag | Meaning |
|-----|---------|
| **MISSING_FE** | Backend route exists; no service method / no UI consumer |
| **PARTIAL** | Service exists but UI source-of-truth differs, or only subset of fields/ops used |
| **ORPHAN_FE** | Frontend feature with no matching backend capability (or hard-mock) |
| **N/A_UI** | Ops/system endpoint; normally not product UI |

Base URL pattern (both apps): `NEXT_PUBLIC_API_BASE_URL` → default `http://localhost:8000/api/v1`.

---

## 1. Executive summary

| Bucket | Count (approx.) | Verdict |
|--------|-----------------|---------|
| Backend routes wired end-to-end in Storefront and/or Admin | ~65–70 | Core commerce + CMS + admin ops covered |
| Backend routes with **no** frontend consumer | **~12–15** | Auth password lifecycle, audit logs, product statistics, change-log, bulk stock, user delete, order soft-delete |
| Frontend surfaces that are **mock / localStorage / fake success** | **~8 major** | Documents, Settings, About marketing blocks, SMS inquiry, wishlist heart, reports client aggregation, contact placeholders |
| Partial integrations (risk of drift) | **~5** | Server cart vs Zustand, order timeline fallback, comments moderation depth, contacts inbox depth, dashboard KPIs |

The integration is **production-capable for the happy path** (catalog → dual-lane cart → OTP checkout → payment → track / admin fulfill). Gaps cluster in **account security UX**, **ops analytics**, **destructive admin ops**, and **several marketed UI shells that are not backed**.

---

## 2. Complete coverage matrix by domain

### 2.1 System

| Method | Path | Auth | FE status | Notes |
|--------|------|------|-----------|-------|
| GET | `/` | Public | N/A_UI | |
| GET | `/health` | Public | N/A_UI | Used manually / Docker health |
| GET | `/ready` | Public | N/A_UI | |
| GET | `/api/v1` | Public | N/A_UI | |
| GET | `/metrics` | Public | N/A_UI | If `ENABLE_METRICS` |
| — | `/static/uploads/*` | Public | PARTIAL | Consumed as image URLs when products/CMS return paths; no dedicated uploader UI beyond product images |

---

### 2.2 Auth (`/auth`)

| Method | Path | Auth | Consumer | Status |
|--------|------|------|----------|--------|
| POST | `/auth/otp/request` | Public | Storefront `authService` | Wired |
| POST | `/auth/otp/verify` | Public | Storefront | Wired |
| POST | `/auth/login` | Public | Admin `authService` (form-urlencoded) | Wired |
| GET | `/auth/me` | Bearer | Storefront | Wired |
| POST | `/auth/refresh` | Public | Both axios interceptors | Wired |
| POST | `/auth/logout` | Bearer | Both | Wired |
| POST | `/auth/verify-pin` | SuperAdmin | Admin catalog/orders step-up | Wired |
| POST | `/auth/register` | Public* | — | **MISSING_FE** |
| POST | `/auth/change-password` | Bearer | — | **MISSING_FE** |
| POST | `/auth/password-reset/request` | Public | — | **MISSING_FE** |
| POST | `/auth/password-reset/confirm` | Public | — | **MISSING_FE** |

\*Blocked server-side when `ALLOW_PUBLIC_REGISTER=false`.

**Implication:** Storefront identity is OTP-only. Password-register, change-password, and reset flows have **zero** screens, hooks, or service methods. If product intent is OTP-only forever, these BE routes are intentional surplus; if B2B accounts need passwords, FE is incomplete.

---

### 2.3 Users / audit (`/users`) — admin

| Method | Path | Auth | Consumer | Status |
|--------|------|------|----------|--------|
| GET | `/users` | SuperAdmin | `customersService.list` | Wired |
| GET | `/users/{id}` | SuperAdmin | `customersService.get` | Wired |
| PATCH | `/users/{id}` | SuperAdmin+StepUp | `customersService.update` | Wired (step-up via interceptor/helper) |
| DELETE | `/users/{id}` | SuperAdmin+StepUp | — | **MISSING_FE** |
| GET | `/users/audit-logs/list` | SuperAdmin | — | **MISSING_FE** |

---

### 2.4 Products, search, comments, images

| Method | Path | Consumer | Status |
|--------|------|----------|--------|
| GET | `/products/` | SF + Admin | Wired (SF: PLP filters/`spec_*`; Admin: list/edit filters) |
| GET | `/products/{id}` | SF + Admin | Wired |
| GET | `/products/sku/{sku}` | Admin header search | Wired |
| GET | `/products/{id}/related` | SF PDP | Wired |
| GET | `/products/{id}/comments` | SF PDP | Wired |
| POST | `/products/{id}/comments` | SF PDP | Wired (Bearer) |
| POST | `/products/` | Admin create | Wired |
| PUT | `/products/{id}` | Admin edit | Wired (**stock_quantity omitted** — correct vs BE contract) |
| DELETE | `/products/{id}` | Admin list | Wired + step-up |
| POST | `/products/{id}/restore` | Admin deleted bin | Wired |
| POST/PATCH/DELETE | `…/images*` | Admin edit | Wired (JSON URL, multipart upload, primary, reorder, delete) |
| GET | `/products/statistics` | — | **MISSING_FE** |
| GET | `/products/{id}/change-log` | — | **MISSING_FE** |

**PARTIAL note — ratings:** BE returns comment ratings; PDP still shows a **hardcoded** `۴.۷` star display in UI (UX issue + unused data).

---

### 2.5 Inventory

| Method | Path | Consumer | Status |
|--------|------|----------|--------|
| GET | `/products/{id}/stock` | Admin edit | Wired |
| POST | `/products/{id}/stock/adjust` | Admin edit | Wired |
| POST | `/products/bulk/stock-adjust` | — | **MISSING_FE** |
| (dashboard) | — | Admin `/` | **ORPHAN_FE math** — inventory value approximated from product list `base_price` sum, not `/products/statistics` |

---

### 2.6 Categories & brands

| Method | Path | Consumer | Status |
|--------|------|----------|--------|
| GET | `/categories/tree` | SF mega-menu + Admin | Wired |
| GET | `/categories/` | Both services | Wired |
| GET | `/categories/slug/{slug}` | SF catalog | Wired |
| GET | `/categories/spec-labels` | SF boot | Wired (+ hardcoded FE fallback) |
| GET | `/categories/{id}/spec-filter-options` | SF catalog | Wired |
| GET | `/categories/{id}/spec-templates` | Admin product forms | Wired |
| POST/PUT/DELETE | `/categories/…` | Admin | Wired (delete + step-up) |
| GET | `/brands/`, `/brands/slug/{slug}` | SF | Wired |
| POST/PUT/DELETE | `/brands/…` | Admin | Wired |

No material gap in this domain.

---

### 2.7 Cart

| Method | Path | Consumer | Status |
|--------|------|----------|--------|
| GET | `/cart` | `cartService.get` | **PARTIAL** — implemented; Zustand persist is UI SoT |
| PUT | `/cart/items` | `cartService.upsert` | **PARTIAL** — best-effort sync when live |
| DELETE | `/cart/items/{product_id}` | Wired | PARTIAL |
| DELETE | `/cart` | Wired | PARTIAL |
| POST | `/cart/merge` | After OTP verify | Wired |

**Gap character:** Not “API missing from FE code,” but **architecture mismatch**. Offline/mock mode no-ops sync. Stale local cart can diverge from server stock.

---

### 2.8 Orders

| Method | Path | Consumer | Status |
|--------|------|----------|--------|
| GET | `/orders/me` | SF account | Wired |
| GET | `/orders/track/{code}` | SF success / payment | Wired (**PARTIAL** timeline: FE `buildOrderTimeline` fallback) |
| GET | `/orders` | Admin orders + quotes (`mode=inquiry`) | Wired |
| GET | `/orders/{id}` | Admin detail | Wired |
| PATCH | `/orders/{id}/status` | Admin (+ step-up on cancel) | Wired |
| POST | `/orders/{id}/quote` | Admin quote dialog | Wired |
| DELETE | `/orders/{id}` | — | **MISSING_FE** (soft-archive) |

---

### 2.9 Payments

| Method | Path | Consumer | Status |
|--------|------|----------|--------|
| POST | `/payments/init` | SF checkout | Wired + Idempotency-Key |
| GET | `/payments/callback` | Gateway → browser | Handled via redirect to SF callback page |
| POST | `/payments/verify` | SF `PaymentCallbackView` | Wired |
| POST | `/payments/refund` | Admin order panel + step-up | Wired |

No missing payment routes in FE services.

---

### 2.10 Storefront public CMS & checkout

| Method | Path | Consumer | Status |
|--------|------|----------|--------|
| POST | `/checkout` | SF checkout | Wired + Idempotency-Key |
| POST | `/contact` | SF contact | Wired |
| GET | `/hero-slides/` | SF home | Wired |
| GET | `/blog/`, `/blog/{slug}` | SF blog | Wired |
| GET | `/articles/`, `/articles/{slug}` | — | **MISSING_FE** (alias only; `/blog` used — acceptable) |

---

### 2.11 CMS admin (`/cms`)

| Method | Path | Consumer | Status |
|--------|------|----------|--------|
| CRUD | `/cms/articles` | Admin | Wired |
| CRUD | `/cms/hero-slides` | Admin | Wired |
| GET/DELETE | `/cms/product-comments` | Admin | Wired |
| GET | `/cms/contact-submissions` | Admin | Wired |

**Depth gap (both sides):** No approve/reject comment endpoints; no contact ticket status endpoints. FE correctly mirrors BE thinness — listed under §4 as product capability gap, not FE negligence alone.

---

## 3. Backend endpoints with no frontend implementation

### 3.1 Priority table (product impact)

| Priority | Endpoint | Why it matters | Suggested FE surface |
|----------|----------|----------------|----------------------|
| **P1** | `POST /auth/password-reset/request` + `confirm` | Customers locked out without SMS OTP device recovery / password accounts | `/login` → “فراموشی رمز” or post-OTP set-password |
| **P1** | `POST /auth/change-password` | Account security for password users / admins using password login | Account / settings security card |
| **P2** | `POST /auth/register` | Only if public password registration is product policy | `/register` or checkout alternate |
| **P2** | `GET /products/statistics` | Honest admin dashboard / reports | Dashboard widgets; stop inventing KPIs from `limit` samples |
| **P2** | `POST /products/bulk/stock-adjust` | Warehouse ops efficiency | Products list multi-select + bulk dialog |
| **P2** | `GET /products/{id}/change-log` | Price/stock audit for ops | Product edit “تاریخچه” tab |
| **P2** | `GET /users/audit-logs/list` | Compliance / step-up forensics | Admin Security / Audit page |
| **P3** | `DELETE /users/{id}` | Soft-delete customers | Customer detail danger zone + step-up |
| **P3** | `DELETE /orders/{id}` | Soft-archive noise orders | Order detail archive action + step-up |
| **P3** | `GET /articles/*` | Alias | Optional; keep `/blog` |

### 3.2 Explicit “not missing” clarifications

These were previously confused with gaps in earlier notes; current code **does** call them when live:

- OTP body `{ phone }` (not `phone_number`)
- Refresh token rotate
- Logout
- Checkout / payment Idempotency-Key
- Server order timeline (with FE fallback)
- Cart merge after login
- Category/brand slug resolve
- Product comment create
- Admin stock adjust (not PUT stock)
- Admin refund + step-up
- CMS pages for articles, hero, comments, contacts

---

## 4. Frontend features without backend APIs (ORPHAN_FE)

### 4.1 Storefront orphans

| Feature | Location | Behavior | Backend reality |
|---------|----------|----------|-----------------|
| About company timeline & stats | `/about` | Static marketing | No CMS “about” entity |
| Home FeatureStrip / HomeStatsStrip / WhyKarzar | Home sections | Hardcoded copy | Hero/blog/products are live; these strips are not |
| “استعلام سریع پیامکی” | `TwoLaneActions` | Validates phone length ≥10 → `setDone(true)` | **No endpoint**; success is fabricated |
| Wishlist heart | `ProductCard` | Decorative button | No wishlist routes |
| Contact DETAILS (phone/email/map) | `ContactView`, `SiteFooter` | Hardcoded placeholders | `POST /contact` exists; org profile settings do not |
| Picsum image fallback | Cards/gallery/cart | Fake photography | Upload/static URLs exist for real images |
| Spec label fallback map | `feature-labels.ts` | Offline labels | Prefer `/categories/spec-labels` |
| Synthetic order timeline | `buildOrderTimeline` | Invented steps | Prefer `timeline` from track/detail APIs |
| Dual-lane cart persistence | Zustand `karzar.storefront.cart` | Local SoT | Server cart exists but is secondary |

### 4.2 Admin orphans

| Feature | Location | Behavior | Backend reality |
|---------|----------|----------|-----------------|
| Documents archive | `/documents` | `MOCK_DOCUMENTS`; upload/download toasts | **No documents API** |
| Settings | `/settings` | `localStorage` key `karzar.admin.settings` | **No `/settings` API**; values do not affect Storefront (e.g. inquiry toggle) |
| Reports KPIs | `/reports` | Client aggregate from `GET /orders` + `GET /products` with finite `limit` | No `/reports` or analytics API; inaccurate at scale |
| Dashboard inventory value | `/` | Sum of `base_price` on sampled products | Should use `/products/statistics` (also unused) |
| Login mock credential hint | `/login` | Prints `09120000000 / Admin@123456` | Dev convenience only — must be env-gated |

### 4.3 Shared “thin BE + thin FE” (not orphan, but incomplete product)

| Capability | BE | FE | Gap |
|------------|----|----|-----|
| Comment moderation | List + delete only | Same | No approve/hide/publish workflow |
| Contact tickets | List (+ filters) | List only | No read/replied/assign/archive |
| Shop configuration | — | localStorage | Needs BE settings or CMS site config |
| Partial refunds | Full refund endpoint | Full refund UI | No amount field |

---

## 5. Per-app endpoint checklist (services inventory)

### Storefront services that hit the network

`catalogService`, `authService`, `cartService`, `checkoutService`, `paymentService`, `orderService` (+ refresh interceptor).

**Not present in Storefront services:** register, password change/reset, payments refund, any `/cms/*`, `/users/*`, stock adjust, product write, order status/quote.

### Admin services that hit the network

`authService`, `catalogService` (products/categories/brands/images/stock/pin), `ordersService`, `customersService`, `cmsService`, `paymentsAdminService` (+ refresh).

**Not present in Admin services:** OTP customer auth, storefront checkout/payment verify, cart, blog public, password reset, statistics, change-log, bulk stock, user delete, order delete, audit logs.

---

## 6. Recommended remediation backlog

### Wave A — Stop lying to users (FE-only, fast)
1. Remove or disable SMS inquiry fake success; or add BE endpoint then wire it.
2. Hide `/documents` (or mark “به‌زودی”) until API exists.
3. Relabel Settings as “local device preferences” or implement BE settings.
4. Gate admin mock credentials behind `USE_MOCK` / non-production.
5. Prefer real ratings from comments; remove hardcoded `۴.۷`.

### Wave B — Consume existing unused BE
1. Admin dashboard + reports → `GET /products/statistics`.
2. Product edit → change-log tab.
3. Products list → bulk stock-adjust.
4. Customers → soft-delete with step-up.
5. Orders → soft-archive with step-up.
6. New Admin page → audit-logs list.

### Wave C — Account security product decision
1. If OTP-only: document that register/password-reset BE is unused; optionally disable routes in BE config.
2. If passwords matter: implement Storefront (and optionally Admin) reset + change-password screens matching OpenAPI schemas.

### Wave D — Expand BE + FE together
1. Contact ticket status machine.
2. Comment moderation states.
3. Site settings (phone, address, inquiry enabled) driving Storefront.
4. Documents / media library API if ops need file archive.
5. True analytics endpoints (orders by day, conversion, refund rate).

---

## 7. Traceability

| Artifact | Path |
|----------|------|
| BE routers | `Karzar-main/app/api/endpoints/`, `app/api/v1/__init__.py` |
| SF services | `karzar-frontend/Storefront/src/services/` |
| Admin services | `karzar-frontend/admin-panel/src/services/` |
| Companion FA summary | `docs/audits/01-api-gaps-fa.md` |
| Prior runtime notes | `karzar-frontend/INTEGRATION_RUNTIME_NOTES.md`, `LOCAL_STACK_ACCESS.md` |

---

*Generated from full-repo static analysis of routes and service clients. Runtime feature flags (`USE_MOCK`, `ALLOW_PUBLIC_REGISTER`) can hide/show behavior without changing this inventory.*

---

# Appendix — API-backed UX / design remediation (deep)

> Many “design” and flow problems are honesty problems: the UI promises capabilities the API does not provide, or fails to consume APIs that already exist. This appendix ties product UX goals to concrete API work.

---

## A. Stop fabricating success (UI lies → API truth)

| UI behavior | API reality | Remediation |
|-------------|-------------|-------------|
| PDP SMS inquiry `setDone(true)` | No endpoint | Remove UI **or** add `POST /leads/callback` (or similar) then wire |
| Admin Documents upload/download | No documents API | Hide nav / «به‌زودی» until library API exists |
| Admin Settings drive shop | `localStorage` only | Server `/settings` (or CMS site config) **or** label “this device only” |
| Hardcoded PDP rating `۴.۷` | Comments include `rating` | Aggregate from `GET /products/{id}/comments` |
| Client `buildOrderTimeline` | Track/detail may return `timeline` | Prefer server timeline; fallback only if absent + mark as estimated |
| Cart feels local-only | Full `/cart` surface exists | After OTP keep `merge`; surface server stock conflicts on cart load |
| Home “special offers” | No discount feed | Use honest query (`discount` filter/sort) or hide section when empty |
| Contact phone/email/map placeholders | Only `POST /contact` | Site settings API or CMS fields for org profile |

---

## B. Existing APIs the UX must consume for smoothness

| Endpoint | UX payoff | FE work |
|----------|-----------|---------|
| `GET /products/` + `meta.total_count` | Pagination / load-more — catalog is otherwise a dead end after 24 | Storefront + admin lists |
| `GET /products/statistics` | Honest dashboard / reports instead of summing sampled `base_price` | Admin dashboard widgets |
| `GET/POST …/stock`, `…/stock/adjust` | Accurate availability messaging; low-stock cues on PDP/admin | Already partial — deepen display |
| `POST /products/bulk/stock-adjust` | Warehouse multi-SKU ops without N round-trips | New admin bulk UI |
| `GET …/change-log` | Price/stock audit trail on product edit | New “تاریخچه” tab |
| `POST /cart/merge` | Guest cart survives login | Keep prominent in OTP success path |
| `GET /orders/track/{code}` | Success, account detail, payment recovery | Account order detail (not success celebration) |
| `POST /payments/init` (retry) | Recovery when order exists but gateway init failed | Checkout fail panel + Idempotency-Key |
| `GET /categories/spec-labels` | Persian filter labels | Reduce hardcoded `feature-labels` fallback reliance |
| `GET /users/audit-logs/list` | Ops forensics after step-up actions | New admin Audit page |
| `DELETE /users/{id}`, `DELETE /orders/{id}` | Soft-delete / archive noise | Danger-zone actions + step-up |

---

## C. Backend gaps that block a “complete” journey (expand BE + FE)

| Experience need | API status | Notes |
|-----------------|------------|-------|
| Password reset / change | **BE exists, FE missing** | `password-reset/*`, `change-password` |
| Public password register | **BE exists, FE missing** | Only if product policy requires it |
| Comment approve/hide before public | **Missing both sides** | Storefront posts go live immediately |
| Contact ticket read/replied/assign | **Missing both sides** | Inbox is list-only |
| Saved addresses / address book | **Missing** | Checkout free-text province/city |
| Global site settings | **Missing** | Phone, inquiry enabled, shipping copy |
| Documents / media library | **Missing** | Admin Documents is mock |
| True analytics (`/reports`) | **Missing** | Client aggregate from capped lists is false at scale |
| Partial refunds | **BE full refund only** | UI correctly cannot offer amounts |
| Wishlist | **Missing** | Heart is decorative — remove or add API |

---

## D. Dual-lane contract hygiene (keeps design system honest)

1. Persist and display `lane=purchase|inquiry` consistently across cart, checkout, and admin `mode`.  
2. Prefer an explicit product flag/field for “inquiry-only” rather than UI inferring solely from null price (if BE can expose it).  
3. Account order list must show `mode` + `payment_status` badges from API payloads.  
4. Keep **Idempotency-Key** on `POST /checkout` and `POST /payments/init` — required for safe “Retry pay” UX.  
5. Step-up (`X-Step-Up-Token`) must remain on destructive admin paths; UI copy should explain *why* PIN is asked.  
6. Cart GET after login should reconcile quantities; show line-level errors if stock moved.

---

## E. Recommended “API × UX” delivery waves

### Wave 1 — No new backend (fast honesty)
Remove fake SMS; hide Documents; label Settings; real ratings; catalog pagination via `meta`; payment retry UI; honor `?next=`; fix footer `/quote`; env-gate admin mock credentials and test OTP strings.

### Wave 2 — Consume unused backend
Admin: statistics, bulk stock, change-log, audit-logs, optional user/order soft-delete. Storefront: stronger cart GET reconciliation + timeline preference.

### Wave 3 — Auth product decision
If OTP-only forever: document unused password routes; optionally disable via config. If passwords matter: implement reset + change-password screens against existing OpenAPI schemas.

### Wave 4 — Joint BE+FE expansions
Comment moderation states; contact ticket state machine; site settings driving Storefront chrome; address book; documents library; analytics endpoints.

---

## F. Acceptance criteria (API lens)

- No Storefront control claims success without a matching HTTP call (or explicit offline/mock banner).  
- Admin nav items either hit real APIs or are visually marked non-production.  
- Catalog can reach every product reported in `meta.total_count`.  
- Payment failure after order creation always exposes tracking code + init retry.  
- Dashboard numbers that look like “inventory value” come from `/products/statistics` (or are removed).  

---

*Companion visual/flow redesign: `02-uiux-audit-en.md` Part G. Persian API appendix: `01-api-gaps-fa.md`.*
