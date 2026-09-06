# سند عدم انطباق Backend — KarZar Frontend

**نسخه:** 2026-07-11  
**مخاطب:** تیم Backend (FastAPI)  
**هدف:** فهرست دقیق و اولویت‌بندی‌شدهٔ تمام شکاف‌های API، قرارداد داده، و رفتار مورد انتظار فرانت‌اند تا `NEXT_PUBLIC_USE_MOCK=false` بدون workaround اجرا شود.

**مرجع تکمیلی:** `BACKEND_HANDOFF.md` (خلاصهٔ قبلی)

---

## خلاصه اجرایی

| اولویت | حوزه | وضعیت Backend (فرض) | تأثیر |
|--------|------|---------------------|--------|
| P0 | گردش کار سفارش/استعلام ادمین | ناقص | پنل ادمین عملیاتی نمی‌شود |
| P0 | پرداخت + callback | نیاز به env/verify | خرید آنلاین Storefront |
| P0 | Auth OTP + `/auth/me` | جزئی | ورود مشتری |
| P1 | Logistics (رهگیری پست، ETA، timeline) | ناقص | پیگیری سفارش + UI ادمین |
| P1 | صدور پیش‌فاکتور استعلام | **وجود ندارد** | B2B/B2C inquiry |
| P1 | فاکتور PDF | **وجود ندارد** | دانلود پیش‌فاکتور |
| P2 | محصولات حذف‌شده + restore | فیلتر ندارد | صفحه deleted products |
| P2 | گزارش‌گیری aggregate | **وجود ندارد** | reports واقعی |
| P2 | آپلود تصویر multipart | URL-only | UX آپلود واقعی |

---

## 1. قرارداد خطا (الزام سراسری)

فرانت‌اند روی **`ApiError`** با این شکل کار می‌کند:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "پیام فارسی قابل نمایش",
  "details": [
    { "field": "postal_tracking_code", "message": "..." }
  ]
}
```

FastAPI معمولاً زیر `detail` برمی‌گرداند — **هر دو** پشتیبانی می‌شود.

| `error_code` | کاربرد فرانت |
|--------------|--------------|
| `STEP_UP_REQUIRED` | باز کردن دیالوگ PIN |
| `VALIDATION_ERROR` | toast + field errors |
| `NOT_FOUND` | 404 |
| `GUEST_ORDER_NOT_PAYABLE` | هدایت به login در checkout |
| `UNAUTHORIZED` | logout + redirect |

---

## 2. احراز هویت

### 2.1 Storefront — OTP

| Endpoint | Method | Body | Response مورد انتظار |
|----------|--------|------|----------------------|
| `/auth/otp/request` | POST | `{ "phone_number": "0912..." }` | `{ "expires_in": 120 }` (+ `dev_code` فقط dev) |
| `/auth/otp/verify` | POST | `{ "phone_number", "code" }` | `{ "access_token", "token_type", "expires_in", "customer": { "id", "phone_number", "full_name" } }` |
| `/auth/me` | GET | Bearer | `{ "id", "phone_number", "full_name" }` |

**عدم انطباق‌های شناخته‌شده:**
- فیلد `phone` vs `phone_number` — فرانت map می‌کند؛ backend باید **`phone_number`** برگرداند.
- **`expires_in`** در verify — برای انقضای token در localStorage لازم است؛ بدون آن session بی‌پایان می‌ماند.
- 401 روی `/auth/me` → redirect به `/login?expired=1`

### 2.2 Admin — OAuth2 login

| Endpoint | Method | Content-Type | Body |
|----------|--------|--------------|------|
| `/auth/login` | POST | `application/x-www-form-urlencoded` | `username` (phone) + `password` |

Response:

```json
{ "access_token": "...", "token_type": "bearer", "expires_in": 3600 }
```

**Step-up (عملیات حساس):**
- Header: `X-Step-Up-Token`
- Endpoint: `POST /auth/step-up` با PIN → `{ "secure_token", "expires_in" }`
- عملیات نیازمند step-up: لغو سفارش، PATCH مشتری، حذف/restore محصول، ...

---

## 3. پرداخت (Storefront) — P0

### 3.1 Env backend

```env
PAYMENT_CALLBACK_URL=https://store.example.com/checkout/payment/callback
```

### 3.2 Init

`POST /payments/init`

```json
{ "order_id": 123 }
```

Response:

```json
{
  "authority": "...",
  "payment_url": "https://gateway.../?Authority=..."
}
```

`payment_url` باید به callback بالا redirect کند با `Authority` و `Status`.

### 3.3 Verify

`POST /payments/verify`

```json
{
  "order_id": 123,
  "authority": "...",
  "status": "OK"
}
```

**مهم:** `order_id` از sessionStorage فرانت می‌آید (نه فقط authority).

Response موفق:

```json
{
  "success": true,
  "order_id": 123,
  "tracking_code": "KZ-...",
  "status": "paid",
  "status_label": "پرداخت شده",
  "ref_id": "...",
  "message": "..."
}
```

### 3.4 قوانین کسب‌وکار

- سفارش **guest** (`is_guest: true`) → **`GUEST_ORDER_NOT_PAYABLE`** (402/403)
- فقط `pending_payment` قابل init payment
- پس از verify موفق → status = `paid`

---

## 4. Checkout / سفارش Storefront

### 4.1 Submit

`POST /checkout/`

```json
{
  "mode": "purchase" | "inquiry",
  "customer": { "full_name", "phone", "is_guest": false },
  "items": [{ "product_id", "quantity" }],
  "note": "...",
  "shipping": { "province", "city", "address", "postal_code", "phone" },
  "company_name": null
}
```

Response:

```json
{
  "order_id": 123,
  "tracking_code": "KZ-...",
  "mode": "purchase",
  "status": "pending_payment",
  "status_label": "...",
  "estimated_total": "1850000",
  "created_at": "..."
}
```

- `inquiry` → status اولیه: **`inquiry_review`**
- `purchase` + logged-in → `pending_payment`
- `estimated_total` برای inquiry می‌تواند `null` باشد تا ادمین قیمت بدهد

### 4.2 لیست سفارش‌های من

`GET /orders/me?skip=&limit=`

**فقط سفارش‌های phone کاربر لاگین‌شده** — فیلتر سمت سرور الزامی.

### 4.3 Tracking

`GET /orders/track/{tracking_code}`

**Response کامل مورد انتظار (P1):**

```json
{
  "tracking_code": "KZ-...",
  "status": "shipped",
  "status_label": "ارسال شده",
  "mode": "purchase",
  "estimated_total": "...",
  "postal_tracking_code": "1234567890123456",
  "delivery_eta": "2026-07-15T10:00:00Z",
  "timeline": [
    {
      "status": "paid",
      "status_label": "پرداخت شده",
      "occurred_at": "2026-07-09T12:00:00Z",
      "description": "پرداخت تأیید شد",
      "actor": "system"
    }
  ]
}
```

**عدم انطباق فعلی:** اغلب فقط status برمی‌گردد — timeline و logistics لازم است.

---

## 5. Admin — سفارش و گردش کار (P0) — **بحرانی**

فرانت‌اند دیگر dropdown آزاد برای status ندارد. گردش کار **مرحله‌ای** است:

### 5.1 مسیر خرید (purchase)

```
pending_payment → paid → processing → shipped → delivered
                                    ↘ cancelled (step-up)
```

| از | به | شرط | UI ادمین |
|----|-----|------|----------|
| pending_payment | paid | پرداخت تأیید | «تأیید پرداخت» (دستی/edge) |
| paid | processing | — | «شروع پردازش» |
| processing | shipped | **`postal_tracking_code` الزامی (≥10 رقم)** | دیالوگ «ثبت ارسال» |
| shipped | delivered | — | «تحویل به مشتری» |
| * | cancelled | step-up PIN | «لغو سفارش» |

### 5.2 مسیر استعلام (inquiry)

```
inquiry_review → inquiry_quoted → inquiry_closed
                              ↘ cancelled (step-up)
```

| از | به | شرط | UI ادمین |
|----|-----|------|----------|
| inquiry_review | inquiry_quoted | قیمت همه اقلام + صدور فاکتور | دیالوگ «صدور پیش‌فاکتور» |
| inquiry_quoted | inquiry_closed | — | «بستن پرونده» |

### 5.3 PATCH status — قرارداد کامل

`PATCH /orders/{id}/status`

```json
{
  "status": "shipped",
  "note": "ارسال با تیپاکس",
  "postal_tracking_code": "1234567890123456",
  "delivery_eta": "2026-07-15T10:00:00Z"
}
```

**الزامات backend:**
1. **Validation:** `shipped` بدون `postal_tracking_code` → `400 VALIDATION_ERROR`
2. **State machine:** فقط transitionهای مجاز (جدول بالا) — غیرمجاز → `400`
3. **`cancelled`** → نیاز به `X-Step-Up-Token`
4. پس از هر تغییر → append به **`timeline`** (persist در DB)
5. Response = **`OrderDetail` کامل** (نه فقط status)

**عدم انطباق فعلی (تأیید شده در فرانت live path قبلی):**
- فقط `{ status, note }` ارسال/پذیرفته می‌شود
- logistics ذخیره نمی‌شود
- state machine enforce نمی‌شود

### 5.4 صدور پیش‌فاکتور — **Endpoint جدید (P0)**

`POST /orders/{id}/quote`

```json
{
  "items": [
    { "product_id": 1, "quantity": 2, "unit_price": "925000.00" }
  ],
  "note": "شرایط پرداخت: ۵۰٪ پیش‌پرداخت",
  "valid_until": "2026-08-01T00:00:00Z"
}
```

**رفتار:**
- فقط `mode=inquiry` و `status=inquiry_review`
- به‌روزرسانی `unit_price` / `line_total` اقلام
- محاسبه `estimated_total`
- تغییر status → `inquiry_quoted`
- ایجاد **`invoice`**:

```json
{
  "invoice_number": "INV-1404-00042",
  "issued_at": "2026-07-11T...",
  "valid_until": "...",
  "total": "1850000.00",
  "note": "..."
}
```

- append timeline event

### 5.5 دانلود PDF فاکتور — **Endpoint جدید (P1)**

`GET /orders/{id}/invoice.pdf`  
یا  
`GET /invoices/{invoice_number}/pdf`

Response: `application/pdf` با Content-Disposition.

فرانت دکمه «دانلود PDF» دارد؛ mock toast می‌زند تا این endpoint آماده شود.

### 5.6 لیست سفارش‌ها

`GET /orders/?skip=&limit=&status=&search=&mode=purchase|inquiry`

- **`mode`** filter برای تفکیک `/orders` vs `/quotes`
- `search` روی tracking_code, customer name, phone

### 5.7 Order detail

`GET /orders/{id}`

Response باید شامل:

```json
{
  "id", "tracking_code", "status", "status_label", "mode",
  "customer_full_name", "customer_phone",
  "estimated_total", "created_at", "note",
  "shipping": { ... },
  "payment_status",
  "postal_tracking_code", "delivery_eta",
  "invoice": { ... } | null,
  "timeline": [ ... ],
  "items": [
    { "product_id", "quantity", "unit_price", "product_name", "sku" }
  ]
}
```

**ترجیح (decision 4-B):** `product_name` + `sku` در items (تا batch fetch لازم نباشد).

---

## 6. مشتریان (Admin)

`GET /customers/?search=&skip=&limit=`  
`GET /customers/{id}`  
`PATCH /customers/{id}` + step-up

Body PATCH (فقط):

```json
{ "full_name": "...", "is_active": true }
```

Response: `phone_number` → map به `phone`.

---

## 7. کاتالوگ

### 7.1 Categories

- `GET /categories/tree` → **آرایه bare** `[{ id, name, parent_id, subcategories: [] }]` (بدون envelope)
- CRUD categories + step-up on delete

### 7.2 Products

- List: `GET /products/?skip&limit&search&brand_id&category_id&is_deleted`
- **`is_deleted=true`** برای صفحه deleted — **الان فیلتر ندارد (P2)**
- **`POST /products/{id}/restore`** + step-up — **نیاز است**
- Spec filters: `spec_technical_specs__{key}=value`
- `GET /categories/{id}/spec-filter-options`
- `GET /categories/spec-labels` → `{ "grade": "گرید", ... }`

### 7.3 تصاویر محصول

- `POST /products/{id}/images` `{ "image_url", "is_primary?" }`
- **آینده:** `multipart/form-data` upload
- PUT primary, DELETE, reorder — wired in frontend

### 7.4 Stock

`POST /products/{id}/stock/adjust?quantity_delta=N&reason=...`

---

## 8. Brands

`GET /brands/` → `{ "data": [...] }`

---

## 9. Inquiry نیمه‌حساب (Storefront)

- Guest inquiry → localStorage (فرانت)
- پس از OTP login → restore quote basket

**Backend اختیاری (بهبود):**
- `POST /inquiry/pending/sync` برای merge سرور-side

---

## 10. SMS / Notification (آینده)

Hook points که backend باید آماده کند:

| رویداد | داده |
|--------|------|
| shipped | phone, tracking_code, postal_tracking_code |
| inquiry_quoted | phone, invoice_number, total |
| paid | phone, tracking_code |

---

## 11. گزارش‌ها (Admin) — P2

فرانت mock از list orders/products aggregate می‌گیرد.

**Endpoint پیشنهادی:**

`GET /reports/summary?from=&to=`

```json
{
  "total_orders": 120,
  "purchase_count": 95,
  "inquiry_count": 25,
  "revenue_paid": "125000000.00",
  "out_of_stock_count": 8,
  "pending_actions": [
    { "order_id": 1002, "tracking_code": "...", "status": "inquiry_review" }
  ]
}
```

---

## 12. اسناد (Admin Documents) — P2

صفحه `/documents` mock است.

**پیشنهاد:**
- `GET /documents/`
- `POST /documents/upload` (multipart)
- `GET /documents/{id}/download`

---

## 13. تنظیمات فروشگاه — P2

`GET/PATCH /settings/store`

```json
{
  "shop_name": "کارزار",
  "support_phone": "...",
  "inquiry_enabled": true,
  "min_order_note": "...",
  "require_password_for_login": true
}
```

**رفتار `require_password_for_login`:**
- `true` (پیش‌فرض production): login admin حتماً password می‌خواهد
- `false` (فقط dev): mock اجازه login با phone می‌دهد

---

## 14. مشتریان — دسته‌بندی، برچسب، سوابق (P1)

### 14.1 فیلدهای جدید Customer

```json
{
  "id": 1,
  "phone_number": "09121234567",
  "full_name": "...",
  "is_active": true,
  "category": "سازمانی",
  "tags": ["VIP", "تهران"],
  "note": "...",
  "order_count": 3,
  "created_at": "..."
}
```

`PATCH /users/{id}` + step-up باید بپذیرد:

```json
{
  "full_name": "...",
  "is_active": true,
  "note": "...",
  "category": "سازمانی",
  "tags": ["VIP", "B2B"]
}
```

### 14.2 سوابق سفارش مشتری

`GET /orders/?customer_phone=09121234567&limit=100`

یا ترجیحاً:

`GET /users/{id}/orders`

Response: همان envelope لیست سفارش با `mode`, `status`, `estimated_total`, `tracking_code`.

---

## 15. تصاویر محصول — Admin (P1)

### 15.1 Endpoints موجود (URL-only)

- `POST /products/{id}/images` `{ "image_url", "is_primary?" }`
- `POST /products/{id}/images/upload` **multipart** (الزami برای UX واقعی)
- `PATCH /products/{id}/images/{image_id}/primary`
- `PUT /products/{id}/images/reorder` `{ "image_ids": [3,1,2] }`
- `DELETE /products/{id}/images/{image_id}`

### 15.2 Response تصویر

```json
{
  "id": 101,
  "url": "https://cdn.../product.jpg",
  "is_primary": true,
  "sort_order": 0
}
```

### 15.3 CORS/CDN

URL تصاویر باید از HTTPS قابل fetch باشند (picsum, CDN فروشگاه).

---

## 16. Pagination envelope (سراسری)

```json
{
  "data": [ ... ],
  "meta": {
    "total_count": 100,
    "skip": 0,
    "limit": 20,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## 17. CORS & Headers

برای dev:

```
Access-Control-Allow-Origin: http://localhost:3000, http://localhost:3001
Access-Control-Allow-Headers: Authorization, Content-Type, X-Step-Up-Token
```

---

## 18. چک‌لیست پذیرش (Acceptance)

Backend زمانی «سازگار» است که:

- [ ] OTP login + expires_in + /auth/me
- [ ] Checkout purchase end-to-end + payment verify
- [ ] Checkout inquiry → در admin دیده شود
- [ ] Admin state machine (purchase + inquiry) enforce شود
- [ ] POST /orders/{id}/quote + invoice object
- [ ] PATCH status با logistics + timeline
- [ ] GET track با timeline + postal
- [ ] GET orders?mode=inquiry
- [ ] orders/me فیلتر شده با user
- [ ] is_deleted filter + restore
- [ ] PATCH customer با category + tags
- [ ] GET orders?customer_phone=...
- [ ] POST product image multipart upload
- [ ] GET/PATCH /settings/store با require_password_for_login
- [ ] (P1) invoice PDF download
- [ ] (P2) reports/summary

---

## 19. دستورات تست سریع

```bash
# Spec labels
curl -s http://localhost:8000/api/v1/categories/spec-labels | jq

# Orders with mode
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/orders/?mode=inquiry" | jq

# Quote issue
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"product_id":1,"quantity":2,"unit_price":"925000"}],"note":"test"}' \
  http://localhost:8000/api/v1/orders/1002/quote | jq

# Status with logistics
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"shipped","postal_tracking_code":"1234567890123456"}' \
  http://localhost:8000/api/v1/orders/1001/status | jq

# Track
curl -s http://localhost:8000/api/v1/orders/track/KZ-100001 | jq
```

---

## 20. Env فرانت برای اتصال

**Storefront `.env.local`:**
```env
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

**Admin `.env.local`:**
```env
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Admin: `npm run dev -- -p 3001`  
Storefront: `npm run dev` (3000)

---

*این سند با UI فعلی فرانت (گردش کار مرحله‌ای سفارش/استعلام، دیالوگ ارسال، صدور پیش‌فاکتور) هم‌تراز است. هر تغییر API باید در این فایل به‌روز شود.*
