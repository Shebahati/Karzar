# راهنمای پیاده‌سازی فرانت‌اند Karzar — هم‌ترازی با Backend (API v1)

**نسخه سند:** 2026-07-13 (پس از P8)  
**مخاطب:** تیم Storefront + Admin Panel  
**وضعیت Backend:** `main` @ `0657db9` — 160 تست پاس، CI فعال  
**مرجع زنده:** `GET /api/openapi.json` (وقتی `ENABLE_API_DOCS=true`)

این سند **منبع اصلی کار فرانت** است. اگر با `docs/FRONTEND_INTEGRATION.md` یا `karzar-frontend-main/BACKEND_NON_COMPLIANCE.md` تناقض دیدید، **این فایل + OpenAPI** اولویت دارند (بسیاری از موارد قدیمی در P7/P8 بسته شده‌اند).

---

## 1. خلاصه اجرایی — آمادگی Backend vs Frontend

| لایه | آمادگی تقریبی | توضیح |
|------|---------------|--------|
| **Backend API (قرارداد)** | **~88%** | جریان‌های اصلی خرید، پرداخت mock، OTP، سفارش، ادمین کاتالوگ، CMS API، cart سرور، idempotency، step-up |
| **Storefront UI** | **~75%** | صفحات اصلی ساخته شده؛ سرویس‌لایه dual mock/live دارد |
| **Storefront ↔ API واقعی** | **~55%** | باگ OTP سمت بک‌اند (hash column) رفع شد؛ فرانت هنوز ممکن است `phone_number` بفرستد + سبد local + بدون idempotency |
| **Admin Panel UI** | **~80%** | سفارش، کاتالوگ، مشتری، استعلام |
| **Admin ↔ API واقعی** | **~65%** | اکثر سرویس‌ها وصل‌اند؛ CMS/گزارش aggregate/PDF ندارد |
| **Production / Ops** | **~40%** | Docker image قدیمی، SMS/Zarinpal واقعی، داده کاتالوگ، SSL، مانیتورینگ |

**فاصله تا «قابل اجرا» (demo/staging با کاربر محدود):** حدود **۱–۲ هفته کار متمرکز فرانت** + تنظیم env و smoke E2E.  
**فاصله تا «production واقعی» (فروشگاه زنده):** حدود **۴–۸ هفته** (فرانت + ops + داده + پرداخت/SMS).

---

## 2. راه‌اندازی محیط توسعه (الزامی)

### 2.1 Backend

```bash
cd Karzar
cp .env.example .env
# حداقل: POSTGRES_*, SECRET_KEY (32+ chars), ADMIN_STEP_UP_PIN (6–12 رقم)

source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**نکته Docker:** کانتینر `lathe_api` ممکن است با Python 3.10 crash کند. Dockerfile فعلی 3.12 است — `docker compose build --no-cache app` بزنید.

### 2.2 Storefront (`:3000`)

```env
# karzar-frontend-main/Storefront/.env.local
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_MOCK_LATENCY_MS=500
```

```bash
cd karzar-frontend-main/Storefront
npm install
npm run dev -- --port 3000
```

### 2.3 Admin Panel (`:3001`)

```env
# admin-panel/.env.local
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

```bash
cd karzar-frontend-main/admin-panel
npm install
npm run dev -- --port 3001
```

### 2.4 env بک‌اند برای فرانت

```env
DEBUG=true
ENABLE_API_DOCS=true
OTP_DEV_ECHO=true
PAYMENT_PROVIDER=mock
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
PAYMENT_CALLBACK_URL=http://localhost:3000/checkout/payment/callback
PAYMENT_SUCCESS_REDIRECT_URL=http://localhost:3000/checkout/success
PAYMENT_FAILURE_REDIRECT_URL=http://localhost:3000/checkout/payment/failed
ALLOW_PUBLIC_REGISTER=false
```

جزئیات: [`docs/LOCAL_DEV_FRONTEND.md`](LOCAL_DEV_FRONTEND.md)

---

## 3. معماری پیشنهادی فرانت (الزامات معماری)

### 3.1 لایه‌ها

```
components/pages  →  features/*/queries (TanStack Query)  →  services/*  →  lib/api-client
                                                              ↓
                                                    env.USE_MOCK ? mock-api : axios
```

- **هیچ کامپوننتی مستقیم `axios` نزند** — فقط `services/*`.
- **خطاها:** `ApiError` با `error_code`, `message`, `details[]`.
- **پول:** همه مبالغ `string` (تومان) — `Number()` فقط برای نمایش.
- **لیست‌ها:** همیشه `{ data, meta }` — هرگز آرایه خام از `/products/` انتظار نداشته باشید.

### 3.2 احراز هویت

| نقش | روش | ذخیره |
|-----|-----|-------|
| Storefront | OTP → `access_token` | `localStorage` کلید `karzar.storefront.token` |
| Admin | OAuth2 form `username`+`password` | همان الگو در admin `api-client` |
| Step-up | `POST /auth/verify-pin` → `secure_token` | حافظه session؛ header `X-Step-Up-Token` |

**Refresh token:** بک‌اند `refresh_token` در OTP/login برمی‌گرداند؛ فرانت فعلاً **ذخیره/rotate نمی‌کند** — برای production باید اضافه شود.

### 3.3 سبد خرید — تصمیم معماری

| حالت فعلی فرانت | بک‌اند |
|-----------------|--------|
| Zustand + `localStorage` (`karzar.storefront.cart`) | `GET/PUT/DELETE /cart` + `X-Cart-Token` + merge روی login |

**توصیه برای parity:**

1. **فاز ۱ (حداقل):** همان localStorage + ارسال `items` در checkout (فعلی کار می‌کند).
2. **فاز ۲ (توصیه‌شده):** سرویس `cartService` با `X-Cart-Token` (حداقل ۳۲ کاراکتر) + `POST /cart/merge` بعد از OTP.

### 3.4 Idempotency (الزام برای production)

| Endpoint | Header | Scope |
|----------|--------|-------|
| `POST /checkout` | `Idempotency-Key: <uuid>` | `checkout:user:{id}` یا `co:guest:{hash}` |
| `POST /payments/init` | همان | `payment_init:user:{id}` |

بدون کلید، درخواست تکراری ممکن است سفارش/پرداخت دوباره بسازد. فرانت **هنوز این header را نمی‌فرستد** — باید در `checkoutService` و `paymentService` اضافه شود.

---

## 4. قرارداد خطا (سراسری)

```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "پیام قابل نمایش",
  "details": [{ "field": "phone", "message": "..." }]
}
```

| `error_code` | HTTP | اقدام UI |
|--------------|------|----------|
| `UNAUTHORIZED` | 401 | پاک token + redirect `/login` |
| `GUEST_ORDER_NOT_PAYABLE` | 403 | نمایش «برای پرداخت وارد شوید» |
| `STEP_UP_REQUIRED` | 403 | باز کردن دیالوگ PIN (ادمین) |
| `STEP_UP_INVALID` | 403 | «توکن step-up مصرف شده» — PIN دوباره |
| `RATE_LIMITED` | 429 | احترام به `Retry-After` |
| `CONFLICT` | 409 | idempotency in-progress یا وضعیت سفارش |

---

## 5. Storefront — Endpoint به Endpoint

Base: `/api/v1` — Auth: Bearer یا public

### 5.1 کاتالوگ

| Method | Path | Auth | Response | یادداشت فرانت |
|--------|------|------|----------|----------------|
| GET | `/categories/tree` | — | **آرایه خام** `[{ id, name, slug, parent_id, subcategories[] }]` | `catalogService.listCategoriesTree` — درست |
| GET | `/categories/` | — | `{ data: CategoryFlat[] }` | `slug` در P8 اضافه شد — type را به‌روز کنید |
| GET | `/categories/slug/{slug}` | — | `CategoryFlat` | **جدید** — برای URL سئو |
| GET | `/categories/spec-labels` | — | `{ labels: { key: "فارسی" } }` | cache کنید |
| GET | `/categories/{id}/spec-filter-options` | — | `{ technical_specs: { key: [values] } }` | PLP فیلتر |
| GET | `/brands/` | — | `{ data: Brand[] }` | `slug` در response |
| GET | `/brands/slug/{slug}` | — | `Brand` | **جدید** |
| GET | `/products/` | — | `{ data, meta }` | فیلتر `category_id`, `brand_id`, `search`, `spec_*`, `ids` |
| GET | `/products/{id}` | — | `ProductDetail` | **slug در API نیست** — فقط id/sku |
| GET | `/products/sku/{sku}` | — | `ProductDetail` | |
| GET | `/products/{id}/related` | — | `{ data: ProductSummary[] }` | |
| GET | `/products/{id}/comments` | — | `{ data: Comment[] }` | فقط خواندن؛ محصول inactive → 404 |
| POST | `/products/{id}/comments` | Bearer | `Comment` | **UI ندارد** — `is_verified_buyer` سرور محاسبه می‌کند |

**CategoryFlat:**

```json
{
  "id": 100, "name": "...", "slug": "drill-hammer",
  "parent_id": 10, "depth": 3, "is_leaf": true, "is_selectable": true,
  "breadcrumb": ["...", "..."], "ancestor_ids": [1, 10], "product_count": 3
}
```

**ProductSummary (PLP):** `id`, `sku`, `name`, `thumbnail`, `base_price`, `stock_status`, `availability`, `category`, `brand` — بدون `slug`.

### 5.2 محتوا

| Method | Path | Response |
|--------|------|----------|
| GET | `/blog/` یا `/articles/` | `{ data: ArticleTeaser[] }` |
| GET | `/blog/{slug}` | `BlogPost` |
| GET | `/hero-slides/` | `{ data: HeroSlide[] }` |
| POST | `/contact` | `{ ok: true, ticket: "TK-..." }` |

### 5.3 احراز هویت مشتری

| Method | Path | Body (بک‌اند واقعی) | Response |
|--------|------|---------------------|----------|
| POST | `/auth/otp/request` | `{ "phone": "09XXXXXXXXX" }` | `{ phone, expires_in, dev_code? }` |
| POST | `/auth/otp/verify` | `{ "phone", "code" }` | `{ access_token, refresh_token, expires_in, customer }` |
| GET | `/auth/me` | Bearer | `{ id, phone_number, full_name, role, ... }` |

#### ⚠️ باگ بحرانی فعلی فرانت

فایل `Storefront/src/services/auth.ts` می‌فرستد:

```json
{ "phone_number": "0912..." }
```

بک‌اند انتظار دارد:

```json
{ "phone": "0912..." }
```

**تا زمانی که این اصلاح نشود، OTP با API واقعی کار نمی‌کند.**

### 5.4 Checkout و پرداخت

**Checkout** `POST /checkout`

```json
{
  "mode": "purchase" | "inquiry",
  "customer": { "full_name", "phone", "is_guest": false },
  "items": [{ "product_id", "quantity" }],
  "note": null,
  "shipping": { "province", "city", "postal_code", "address_line" },
  "company_name": null
}
```

- `purchase` بدون login → `403 PURCHASE_AUTH_REQUIRED`
- `shipping` در purchase **الزامی**
- `postal_code` دقیقاً ۱۰ رقم

**Response:**

```json
{
  "order_id": 1, "tracking_code": "KZ-...",
  "mode": "purchase", "status": "pending_payment", "status_label": "...",
  "estimated_total": "2500000", "created_at": "...",
  "payment_url": null, "authority": null
}
```

فرانت فعلاً بعد از checkout جداگانه `POST /payments/init` می‌زند — **قابل قبول**؛ می‌توانید از `payment_url` داخل checkout هم استفاده کنید (برای کاربر لاگین‌شده پر می‌شود).

**Payment init** `POST /payments/init` — Bearer — `{ order_id }` → `{ authority, payment_url }`

**Payment verify** `POST /payments/verify` — Bearer — `{ order_id, authority, status }` → `{ order_id, payment_status, status, ref_id }`

**Callback عمومی** `GET /payments/callback?Authority=&Status=` — redirect به success/fail URL — فرانت از `/checkout/payment/callback` خودش verify می‌زند (درست).

### 5.5 سفارش مشتری

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/orders/me?skip&limit` | Bearer | `{ data: OrderSummary[], meta }` |
| GET | `/orders/track/{code}` | — | `OrderTrackingResponse` |

**Tracking (وضعیت واقعی بک‌اند P8):**

```json
{
  "tracking_code": "KZ-...",
  "mode": "purchase",
  "status": "shipped",
  "status_label": "ارسال شده",
  "created_at": "...",
  "items": [{ "product_id", "quantity", "unit_price" }],
  "timeline": [{ "status", "status_label", "occurred_at", "description", "actor" }]
}
```

**فاقد در API عمومی:** `postal_tracking_code`, `delivery_eta`, `estimated_total` (عمداً بدون PII).

فرانت در `orders.ts` timeline را **محلی** می‌سازد (`buildOrderTimeline`) — باید از `timeline` سرور استفاده کند.

### 5.6 Cart API (اختیاری ولی آماده)

| Method | Path | Headers | Query |
|--------|------|---------|-------|
| GET | `/cart` | Bearer یا `X-Cart-Token` | `lane=purchase\|inquiry` |
| PUT | `/cart/items` | همان | body: `{ lane, product_id, quantity }` |
| DELETE | `/cart/items/{product_id}` | همان | `lane` |
| DELETE | `/cart` | همان | `lane` |
| POST | `/cart/merge` | Bearer | `{ guest_token, lane? }` |

---

## 6. Admin Panel — Endpoint به Endpoint

Auth: `super_admin` + step-up برای عملیات حساس.

### 6.1 Auth

| Method | Path | Content-Type | Body |
|--------|------|--------------|------|
| POST | `/auth/login` | `application/x-www-form-urlencoded` | `username=09...&password=...` |
| POST | `/auth/verify-pin` | JSON | `{ "pin": "..." }` → `{ secure_token, expires_in }` |

**توجه:** مسیر `/auth/step-up` وجود ندارد — فقط `verify-pin`.

### 6.2 محصولات

| Method | Path | Step-up |
|--------|------|---------|
| GET | `/products/?is_deleted=true` | admin only |
| POST | `/products/` | — |
| PUT | `/products/{id}` | — |
| DELETE | `/products/{id}` | ✅ |
| POST | `/products/{id}/restore` | ✅ |
| POST | `/products/{id}/stock/adjust?quantity_delta=&reason=` | — |
| POST | `/products/{id}/images` | URL یا multipart |
| PATCH | `/products/{id}/images/reorder` | `{ image_ids: [] }` |

`stock_quantity` مستقیم در PUT **بلاک** می‌شود — فقط stock/adjust.

### 6.3 دسته و برند

CRUD استاندارد؛ حذف category/brand نیازمند step-up.

### 6.4 سفارش

| Method | Path | Step-up |
|--------|------|---------|
| GET | `/orders/?page&page_size&status&mode&search&sort` | — |
| GET | `/orders/{id}` | — (شامل timeline, invoice, allowed_next_statuses) |
| PATCH | `/orders/{id}/status` | ✅ برای `cancelled` |
| POST | `/orders/{id}/quote` | — (استعلام → inquiry_quoted) |
| DELETE | `/orders/{id}` | — (soft archive) |
| POST | `/payments/refund` | ✅ step-up — فقط admin |

**قانون مهم:** لغو سفارش `paid` بدون refund → `409`. ابتدا refund، بعد cancel.

### 6.5 کاربران

`GET/PATCH/DELETE /users` — PATCH حساس نیازمند step-up برای برخی فیلدها.

### 6.6 CMS (API آماده — UI ادمین ندارد)

| Prefix | عملیات |
|--------|--------|
| `/cms/articles` | CRUD بلاگ |
| `/cms/hero-slides` | CRUD اسلاید |
| `/cms/product-comments` | لیست/حذف نظر |
| `/cms/contact-submissions` | لیست تماس |

فرانت ادمین **هیچ سرویس `/cms` ندارد** — محتوا فقط از seed یا API دستی.

---

## 7. جدول عدم‌انطباق‌های فعلی (اولویت‌بندی شده)

### P0 — بدون این‌ها سایت live API کار نمی‌کند

| # | موضوع | فایل فرانت | اصلاح لازم |
|---|--------|-----------|------------|
| 1 | OTP body `phone` vs `phone_number` | `Storefront/src/services/auth.ts` | ارسال `{ phone }` نه `phone_number` |
| 2 | `USE_MOCK` پیش‌فرض `true` | `.env.example` هر دو فرانت | در dev/staging حتماً `false` |
| 3 | CORS / callback URL | `.env` بک‌اند | هم‌تراز با پورت 3000 |

### P1 — parity عملکردی

| # | موضوع | وضعیت | اقدام |
|---|--------|--------|-------|
| 4 | Timeline tracking | بک‌اند دارد؛ فرانت ignore | `orders.ts` → استفاده از `data.timeline` |
| 5 | Idempotency checkout/payment | بک‌اند دارد؛ فرانت ندارد | UUID در header |
| 6 | Cart سرور | بک‌اند دارد؛ فرانت localStorage | سرویس cart + merge on login |
| 7 | Refresh token | بک‌اند rotate | ذخیره + `/auth/refresh` |
| 8 | Types `slug` | بک‌اند category/brand | به‌روز `types/category.ts` |
| 9 | Product slug SEO | DB دارد؛ API ندارد | فعلاً `/product/[id]` — یا درخواست فیلد از بک‌اند |
| 10 | فرم ثبت نظر محصول | API دارد | UI + auth در PDP |

### P2 — ادمین و محتوا

| # | موضوع | اقدام |
|---|--------|-------|
| 11 | CMS admin UI | صفحات blog/hero/comments/contact |
| 12 | گزارش aggregate | فعلاً client-side از 200 سفارش — API `/reports` ندارد |
| 13 | PDF پیش‌فاکتور | invoice JSON هست؛ PDF endpoint نیست |
| 14 | Documents page | mock — حذف یا backend storage |
| 15 | `product_name` در order items | فرانت batch `GET /products/?ids=` — OK؛ enrichment اختیاری در بک‌اند |

---

## 8. چک‌لیست پیاده‌سازی فرانت (فازبندی)

### فاز A — اتصال زنده (۳–۵ روز)

- [ ] اصلاح OTP (`phone`)
- [ ] smoke: login → PLP → PDP → cart → checkout → payment mock → success
- [ ] smoke: inquiry quote flow
- [ ] smoke: admin login → محصول → سفارش → ship با کد پستی
- [ ] مدیریت `GUEST_ORDER_NOT_PAYABLE`, `STEP_UP_*`, `RATE_LIMITED`
- [ ] استفاده از timeline واقعی در tracking

### فاز B — سخت‌سازی commerce (۵–۷ روز)

- [ ] Idempotency-Key در checkout و payment init
- [ ] (اختیاری) cart API + merge
- [ ] refresh token rotation
- [ ] types از OpenAPI: `npx openapi-typescript http://localhost:8000/api/openapi.json`
- [ ] E2E Playwright برای checkout

### فاز C — SEO و محتوا (۵–۱۰ روز)

- [ ] مسیر `/catalog?category_id=` + slug lookup از `/categories/slug/{slug}`
- [ ] (بعد از اضافه شدن slug به product API) `/product/[slug]`
- [ ] CMS pages در admin
- [ ] فرم نظر محصول

### فاز D — Production (موازی ops)

- [ ] env production + Zarinpal واقعی
- [ ] SMS Kavenegar
- [ ] Docker rebuild + deploy
- [ ] مانیتورینگ `/ready`, `/metrics`
- [ ] import کاتالوگ واقعی (CSV/scripts)

---

## 9. جریان‌های E2E (مرجع تست دستی)

### 9.1 خرید آنلاین

```
1. POST /auth/otp/request        { "phone": "09123456789" }
2. POST /auth/otp/verify         { "phone", "code" }  (+ dev_code در dev)
3. GET  /products/               → انتخاب product_id
4. POST /checkout                Bearer + items + shipping
   Header: Idempotency-Key: <uuid>
5. POST /payments/init           { order_id }
6. باز کردن payment_url (mock) یا POST /payments/verify
7. GET  /orders/track/{code}   → timeline
```

### 9.2 استعلام B2B

```
1. POST /checkout  mode=inquiry  (مهمان OK)
2. Admin: GET /orders?mode=inquiry
3. Admin: POST /orders/{id}/quote
4. مشتری: track با tracking_code
```

### 9.3 لغو و refund

```
1. Admin: POST /payments/refund  + X-Step-Up-Token
2. سفارش → refunded + cancelled
3. PATCH status=cancelled روی paid بدون refund → خطا
```

---

## 10. وضعیت صفحات فرانت

### Storefront

| مسیر | UI | API زنده | یادداشت |
|------|-----|----------|---------|
| `/` | ✅ | ✅ | hero, categories, carousels |
| `/catalog` | ✅ | ✅ | spec filters |
| `/product/[id]` | ✅ | ✅ | بدون slug route |
| `/cart`, `/quote` | ✅ | local only | |
| `/checkout` | ✅ | ⚠️ | OTP bug |
| `/checkout/payment/callback` | ✅ | ✅ | |
| `/login` | ✅ | ⚠️ | OTP bug |
| `/account/orders` | ✅ | ✅ | |
| `/blog/*` | ✅ | ✅ | |
| `/contact` | ✅ | ✅ | |
| tracking عمومی | ⚠️ | ⚠️ | timeline محلی |

### Admin

| مسیر | UI | API زنده |
|------|-----|----------|
| `/catalog/products` | ✅ | ✅ |
| `/catalog/products/deleted` | ✅ | ✅ `is_deleted` |
| `/catalog/categories` | ✅ | ✅ |
| `/orders`, `/orders/[id]` | ✅ | ✅ |
| `/quotes` | ✅ | ✅ |
| `/customers` | ✅ | ✅ |
| `/reports` | ✅ | ⚠️ client aggregate |
| `/documents` | mock | ❌ |
| CMS | ❌ | API آماده |

---

## 11. فاصله تا مرحله اجرایی — پاسخ صریح

### الان چه داریم؟

- **بک‌اند:** API v1 بالغ، تست‌شده، امنیت commerce (P7/P8)، mock payment، OTP، سفارش دوخط (خرید/استعلام).
- **فرانت:** UI نسبتاً کامل با لایه mock/live؛ **اتصال واقعی نیمه‌کاره** و یک باگ OTP مانع تست end-to-end است.
- **داده:** seed توسعه (`DEV-CHECKOUT-001`) — **کاتالوگ فروش واقعی import نشده**.
- **ops:** اجرای local کار می‌کند؛ Docker production image نیاز به rebuild دارد.

### «اجرایی» یعنی چه؟

| سطح | معنی | فاصله |
|-----|------|--------|
| **Demo داخلی** | mock=false، خرید تست، ادمین کار کند | **۳–۵ روز** (فاز A) |
| **Staging محدود** | داده واقعی جزئی، Zarinpal sandbox، ۱۰–۵۰ کاربر | **۲–۳ هفته** (A+B+D جزئی) |
| **Production** | SMS، پرداخت واقعی، SSL، مانیتورینگ، کاتالوگ کامل، SEO | **۴–۸ هفته** |

### دقیقاً چه باید کرد؟ (ترتیب پیشنهادی)

1. **امروز/فردا:** اصلاح OTP + تست smoke کامل storefront و admin روی `USE_MOCK=false`.
2. **این هفته:** idempotency + timeline واقعی + types از OpenAPI.
3. **هفته بعد:** cart سرور (یا تصمیم رسمی ماندن local) + refresh token.
4. **موازی:** import محصولات (`scripts/seed_*`, CSV) + تصاویر.
5. **قبل launch:** Zarinpal + Kavenegar + Docker deploy + دامنه HTTPS.
6. **بعد launch:** CMS admin، PDF invoice، گزارش‌های aggregate، product slug در API.

---

## 12. منابع و فایل‌های مرجع

| فایل | محل |
|------|-----|
| این سند | `Karzar/docs/FRONTEND_IMPLEMENTATION_GUIDE.md` |
| راهنمای کوتاه integration | `Karzar/docs/FRONTEND_INTEGRATION.md` |
| dev setup | `Karzar/docs/LOCAL_DEV_FRONTEND.md` |
| changelog API | `Karzar/docs/API_CHANGELOG.md` |
| قرارداد mock فرانت | `karzar-frontend-main/API_REQUIREMENTS_STOREFRONT.txt` |
| سند قدیمی عدم انطباق | `karzar-frontend-main/BACKEND_NON_COMPLIANCE.md` (بخش‌های زیادی منسوخ) |
| OpenAPI | `http://localhost:8000/api/openapi.json` |

---

## 13. تعریف Done — هم‌ترازی بک و فرانت

پروژه وقتی «در یک سطح آمادگی» است که:

1. `NEXT_PUBLIC_USE_MOCK=false` روی staging بدون workaround اجرا شود.
2. تمام مسیرهای P0 جدول §7 بسته شده باشند.
3. smoke E2E خرید + استعلام + refund + admin catalog سبز باشد.
4. OpenAPI در CI فرانت با بک‌اند diff شود.
5. checklist فاز A و B تیک خورده باشد.

---

*آخرین به‌روزرسانی: 2026-07-13 — Backend `0657db9` (P8)*
