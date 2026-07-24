# Frontend Ahead of Backend — APIs the Backend Must Implement

**Date:** 18 July 2026  
**Audience:** Backend / platform engineers  
**Base path:** `/api/v1`  
**Scope:** Capabilities the current `karzar-frontend` (Storefront + admin-panel) needs for a complete, honest product — endpoints that **do not exist** (or are too thin) on `Karzar-main`.

> After the July 2026 FE remediation, fabricated surfaces (fake SMS success, pretend document upload) were removed or labeled. This document lists **backend work still required** if those product capabilities should become real.

---

## 1. Executive summary

| Priority band | Theme | Why FE is blocked |
|---------------|-------|-------------------|
| **P0** | Site settings, contact ticket states, comment moderation, documents library, real reports | Admin/storefront either lie, stay local-only, or show “coming soon” |
| **P1** | Customer addresses, explicit inquiry pricing mode, partial refunds, discount feed, CMS pages | Checkout/B2B UX remains coarse |
| **P2** | Wishlist, lead/callback, server inquiry drafts | Optional product expansions |

Happy-path commerce (catalog → dual-lane cart → OTP checkout → payment → admin fulfill) already has BE coverage. Gaps below are **feature completeness**, not boot blockers.

---

## 2. P0 — Required contracts (proposed)

### 2.1 Site / shop settings

**FE today:** Admin `/settings` → `localStorage`. Storefront footer/contact identity hardcoded.

```http
GET  /api/v1/settings/site
PUT  /api/v1/settings/site          # SuperAdmin (+ optional step-up)
```

**Suggested response**

```json
{
  "shop_name": "کارزار",
  "support_phone": "021...",
  "support_email": "support@...",
  "address": "...",
  "map_embed_url": "...",
  "inquiry_enabled": true,
  "order_note_hint": "...",
  "updated_at": "ISO-8601"
}
```

**FE consumers:** Storefront footer/contact/about chrome; Admin settings page (replace localStorage); hide `/quote` nav when `inquiry_enabled=false`.

---

### 2.2 Contact submission workflow

**FE today:** `GET /cms/contact-submissions` list-only.

```http
PATCH /api/v1/cms/contact-submissions/{id}
```

Body example:

```json
{ "status": "read" | "replied" | "archived", "admin_note": "..." }
```

List should accept `?status=` filter. Audit log on status change recommended.

---

### 2.3 Product comment moderation

**FE today:** Public `POST /products/{id}/comments` publishes immediately; admin can only delete.

```http
PATCH /api/v1/cms/product-comments/{id}
# { "status": "approved" | "rejected" | "pending" }
```

Public `GET /products/{id}/comments` must return **approved only**. Admin list returns all statuses. Optional: auto-`pending` on create.

---

### 2.4 Documents / media library

**FE today:** `/documents` is coming-soon.

```http
GET    /api/v1/cms/documents
POST   /api/v1/cms/documents          # multipart or signed URL
GET    /api/v1/cms/documents/{id}/download
DELETE /api/v1/cms/documents/{id}     # SuperAdmin+StepUp
```

Fields: `id`, `title`, `mime_type`, `size_bytes`, `created_at`, `created_by`. Serve via auth-checked download, not world-readable static paths for private docs.

---

### 2.5 Reports / analytics

**FE today:** Client aggregation over capped `GET /orders` + `GET /products`.

```http
GET /api/v1/reports/overview
GET /api/v1/reports/orders-timeseries?from=&to=&granularity=day
```

Overview should include: pending fulfillment count, open inquiries, paid awaiting process, low/OOS SKU count, GMV window, refund count. All SuperAdmin-only.

---

## 3. P1 — Recommended contracts

| Capability | Proposed API | Notes |
|------------|--------------|-------|
| Address book | `CRUD /users/me/addresses` | Checkout prefill; Iranian province/city codes optional |
| Pricing mode | Product field `pricing_mode: "fixed" \| "inquiry"` | Stop inferring solely from null `base_price` |
| Partial refund | Extend `POST /payments/refund` with `amount?` | Keep full refund default; step-up required |
| Discount PLP | `GET /products/?has_discount=true` or `sort=discount_desc` | Powers home “specials” honestly |
| CMS pages | `GET /cms/pages/{slug}` (+ admin CRUD) | About, terms, marketing blocks |

---

## 4. P2 — Optional

| Capability | Proposed API |
|------------|--------------|
| Wishlist | `GET/POST/DELETE /wishlist/items` (Bearer) |
| Callback lead | `POST /leads/callback` `{ phone, product_id?, note? }` rate-limited |
| Inquiry drafts | `POST/GET /inquiries/drafts` server-side persistence |

---

## 5. Compatibility rules (non-negotiable for FE)

1. **List envelope:** `{ "data": [...], "meta": { "total_count": N, ... } }` for paginated resources.  
2. **Dual lane:** `lane` / `mode` ∈ `{ purchase, inquiry }` consistently.  
3. **Step-up:** Destructive admin mutations continue to require `X-Step-Up-Token`.  
4. **Idempotency:** Honor `Idempotency-Key` on checkout + payment init.  
5. **Timeline:** Prefer server-authored order timelines on track/detail.  
6. **CORS / TrustedHost:** Production origins only; no `*` with credentials.

---

## 6. Suggested backend delivery order

1. Site settings  
2. Contact status + comment moderation  
3. Documents  
4. Reports overview  
5. Addresses + `pricing_mode` + partial refund  

OpenAPI update + `FRONTEND_IMPLEMENTATION_GUIDE` sync should ship with each wave.

---

*Persian companion: `docs/gaps/01-fe-ahead-be-needed-fa.md`*  
*Related audits: `docs/audits/01-api-gaps-*.md`*
