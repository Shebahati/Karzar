## 2026-07-17 — Full live-API alignment (frontend-only)

See `INTEGRATION_RUNTIME_NOTES.md` for the complete changelog.

Highlights:
- OTP contract `phone` (not `phone_number`)
- Admin product update no longer sends `stock_quantity`
- Idempotency-Key, refresh tokens, server cart sync, refund UI
- Tracking uses server timeline; CMS admin + product comment form
- `NEXT_PUBLIC_USE_MOCK=false` in env examples/local

**Backend files:** unchanged (runtime-only policy).

---


## Summary

All 22 tasks from the frontend prompt were addressed. Both `Storefront` and `admin-panel` pass `npm run build` with zero TypeScript errors.

**E2E with `NEXT_PUBLIC_USE_MOCK=false`:** Backend at `http://localhost:8000` was **not reachable** during this session. Builds were verified; live API integration should be re-tested once the backend session completes.

---

## Changes Table

| Priority # | Contract | App | Modified Files (key) | Summary of Change | Backend Dependent? |
|---:|---|---|---|---|---|
| 1 | C1, C2 | Storefront | `checkout-view.tsx`, `auth-step.tsx`, `details-step.tsx`, `services/payments.ts`, `services/checkout.ts`, `lib/mock-api.ts`, `app/checkout/payment/callback/page.tsx`, `app/checkout/payment/failed/page.tsx`, `types/payment.ts`, `types/checkout.ts`, `features/checkout/queries.ts` | Full payment chain: checkout → `POST /payments/init` → gateway redirect → callback → `POST /payments/verify` → success/failure. Guest checkout disabled for purchase; OTP enforced inline. Mock parity for init/verify. | Yes — `/payments/init`, `/payments/verify` |
| 2 | C2 | Storefront | `checkout-view.tsx`, `lib/constants.ts` | Secondary defense: handles `GUEST_ORDER_NOT_PAYABLE` via `ApiError.errorCode`, Persian message, redirects to OTP step. | Yes — error code from backend |
| 3 | C4, C5, C10 | Admin | `brands-management-modal.tsx`, `services/catalog.ts`, `lib/mock-api.ts`, `components/step-up-dialog.tsx`, `lib/validation.ts`, `types/category.ts`, `features/catalog/queries.ts` | Brand deletion uses `StepUpDialog` + `X-Step-Up-Token`. Returns `{ id, products_cleared }`. Toast shows dynamic count. PIN Zod `min(6).max(12)`. | Yes — `DELETE /brands/{id}` response shape |
| 4 | C15 | Both | (all above) | E2E attempted; backend offline. Mock + build verified. | Yes — live backend required |
| 5 | C9 | Admin | `product-schema.ts`, `products/new/page.tsx`, `products/[id]/edit/page.tsx`, `lib/constants.ts` | Added `description`, `original_price` to schema/UI/payload. `DEFAULT_TAX_PERCENT = 9` constant. | No (fields may need backend acceptance) |
| 6 | — | Admin | `product-images-section.tsx`, `services/catalog.ts`, `lib/mock-api.ts`, `products/[id]/edit/page.tsx` | Image upload/delete with validation, preview, loading, Persian errors. Mock parity. | Yes — `POST/DELETE /products/{id}/images` |
| 7 | — | Admin | `product-stock-section.tsx`, `services/catalog.ts`, `lib/mock-api.ts` | Stock tab: GET stock, POST adjust with reason. Mock parity. | Yes — stock endpoints |
| 8 | — | Admin | `catalog/products/deleted/page.tsx`, `services/catalog.ts`, `lib/mock-api.ts`, `features/catalog/queries.ts` | Deleted products view + restore via `POST /products/{id}/restore`. Soft-delete in mock. | Yes — `is_deleted` filter + restore |
| 9 | — | Admin | `components/layout/header.tsx`, `services/catalog.ts` | Debounced SKU search (350ms) → `GET /products/sku/{sku}` → product edit page. | Yes — SKU lookup endpoint |
| 10 | C6 | Admin | `orders/page.tsx`, `orders/[id]/page.tsx`, `services/orders.ts`, `types/order.ts`, `features/orders/queries.ts`, `lib/mock-api.ts` | Orders table + detail + status PATCH. Mirrors products table pattern. Mock parity. | Yes — `/orders/` endpoints |
| 11 | — | Admin | `customers/page.tsx`, `customers/[id]/page.tsx`, `services/customers.ts`, `types/customer.ts`, `features/customers/queries.ts`, `lib/mock-api.ts` | Customers list + edit. Mirrors products pattern. Mock parity. | Yes — `/users/` endpoints |
| 12 | C6 | Storefront | `account/orders/page.tsx`, `components/account/my-orders-view.tsx`, `services/orders.ts`, `features/orders/queries.ts`, `lib/mock-api.ts` | My Orders page with `status_label` from API. | Yes — `GET /orders/me` |
| 13 | C6 | Storefront | `success-view.tsx`, `services/orders.ts`, `features/orders/queries.ts` | Success page calls `GET /orders/track/{tracking_code}` for real timeline. | Yes — track endpoint |
| 14 | C13 | Storefront | `services/auth.ts`, `features/auth/queries.ts`, `app/providers.tsx`, `checkout-view.tsx`, `auth-step.tsx`, `lib/mock-api.ts` | `GET /auth/me` on load (token present) and after OTP. Prefills checkout name/phone. | Yes — `/auth/me` |
| 15 | C12 | Admin | `lib/api-client.ts`, `services/auth.ts`, `hooks/use-session-expiry.ts`, `app/(dashboard)/layout.tsx`, `login/login-form.tsx` | Stores `expires_in`, warns 2 min before expiry, redirects on expiry with Persian message. | No |
| 16 | — | Storefront | — | **Pending Backend** — dynamic `spec_*` PLP filters require category-specific filter options from API. | Yes |
| 17 | C7 | Storefront | `lib/feature-labels.ts`, `product-spec-tabs.tsx` | Persian feature labels via swappable local dictionary (`getFeatureLabel`). | Partial — fallback until storefront template exposed |
| 18 | C9 | Admin | `lib/constants.ts`, `product-schema.ts` | Hardcoded `"9"` replaced with `DEFAULT_TAX_PERCENT`. | No |
| 19 | C5 | Admin | `brands-management-modal.tsx` | Toast reads `products_cleared` from API response dynamically. | No |
| 20 | C7 | Admin | `types/product.ts`, `types/category.ts` | `BrandBrief.country`, `ProductSummary` completeness fields, `ProductSpecificationsDict` exact type. | No |
| 21 | C11 | Storefront | — | Country+brand filters already independent in `use-catalog-params.ts` / `filter-panel.tsx`. No `brand_id == null` hack found in current codebase — verified clean. | No |
| 22 | C10 | Admin | `lib/validation.ts`, `step-up-dialog.tsx`, `category-delete-dialog.tsx` | Centralized `stepUpPinSchema` min(6) max(12) applied to all step-up flows. | No |

---

## Newly Handled Error Codes (Storefront)

| errorCode | Where Handled | User Message |
|---|---|---|
| `GUEST_ORDER_NOT_PAYABLE` | `checkout-view.tsx` | پرداخت آنلاین فقط برای کاربران واردشده امکان‌پذیر است. لطفاً وارد شوید. |

## Newly Handled Error Codes (Admin)

| code | Where Handled | User Message |
|---|---|---|
| `INVALID_STATUS_TRANSITION` | `orders/[id]/page.tsx` (mock + API) | تغییر وضعیت از این حالت مجاز نیست. |
| `NOT_FOUND` | SKU search header | محصولی با این SKU یافت نشد |

---

## UI Quality Confirmation

| Page/Feature | Quality Notes |
|---|---|
| Orders table | Matches products page: filters, skeleton/error/empty states, responsive grid, RTL |
| Customers table | Same pattern as orders/products |
| Order detail | Customer, payment, line items cards; status select with error toast |
| Brand Step-Up | Identical `StepUpDialog` pattern as product delete |
| Product images | Card layout, upload progress state, size/type validation toasts |
| Inventory/Stock | Dedicated card on edit page with current qty + adjust controls |
| Payment callback | Loading/success/failure states with motion, Persian copy |
| My Orders | Designed empty state with CTA to catalog |

---

## Discrepancies vs Prompt / Codebase

1. **Country filter hack (C11):** Prompt referenced `catalog.ts` lines 51–52 with `if (params.country && params.brand_id == null)`. This hack is **not present** in the current storefront codebase. URL params in `use-catalog-params.ts` already support simultaneous `country` + `brand_id`. No change required.

2. **Category delete vs product delete step-up:** Categories use inline `CategoryDeleteDialog` (not `StepUpDialog`), pre-existing pattern preserved. Brands now match the **product** `StepUpDialog` pattern per C4.

3. **Backend offline for C15:** Could not execute live E2E. Recommend re-running checkout, brand deletion, and new admin pages once backend is up with `NEXT_PUBLIC_USE_MOCK=false`.

4. **Sidebar type errors:** Pre-existing `NavItem.children` and icon `className` issues fixed to allow clean builds (`nav.config.tsx`, `sidebar.tsx`).

---

## Mock Services Added

### Storefront
- `mockApi.initPayment`, `mockApi.verifyPayment`
- `mockApi.getMe`
- `mockApi.listMyOrders`, `mockApi.trackOrder`
- Updated `mockApi.submitCheckout` with canonical `status` + `status_label`

### Admin
- `mockApi.deleteBrand(id, stepUpToken)` → `BrandDeleteResult`
- `mockApi.restoreProduct`, `mockApi.getProductBySku`
- `mockApi.getProductStock`, `mockApi.adjustProductStock`
- `mockApi.uploadProductImage`, `mockApi.deleteProductImage`
- `mockApi.listOrders`, `mockApi.getOrder`, `mockApi.updateOrderStatus`
- `mockApi.listCustomers`, `mockApi.getCustomer`, `mockApi.updateCustomer`

---

## Acceptance Checklist

- [x] All 22 tasks implemented or flagged with reason
- [x] Mock version for every new service
- [ ] Full manual E2E with `NEXT_PUBLIC_USE_MOCK=false` — **blocked: backend unreachable**
- [x] Zero files modified outside `karzar-frontend/`
- [x] Zero TypeScript errors in production builds
- [x] `FRONTEND_CHANGES.md` generated
