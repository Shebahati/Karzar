# KarZar — AI Project Context (Full Handover)

> **هدف این سند:** دادن کانتکست کامل به یک AI/توسعه‌دهنده جدید برای ادامه کار روی پروژه **بدون نیاز به کاوش اولیه**.  
> **آخرین به‌روزرسانی:** ۱۴۰۵/۰۵/۰۲ (فازهای ۱–۵ اصلاح فرانت)  
> **مسیر ریشه:** `/home/moahmmad/Projects/Karzar/Website/`

---

## فهرست

1. [خلاصه پروژه](#1-خلاصه-پروژه)
2. [دامنه کسب‌وکار](#2-دامنه-کسب‌وکار)
3. [ساختار مونورپو](#3-ساختار-مونورپو)
4. [استک فنی](#4-استک-فنی)
5. [نحوه اجرا](#5-نحوه-اجرا)
6. [بک‌اند (Karzar)](#6-بک‌اند-karzar)
7. [پنل ادمین (admin-panel)](#7-پنل-ادمین-admin-panel)
8. [فروشگاه (Storefront)](#8-فروشگاه-storefront)
9. [قرارداد API و ماتریس یکپارچگی](#9-قرارداد-api-و-ماتریس-یکپارچگی)
10. [احراز هویت](#10-احراز-هویت)
11. [معماری Mock vs Live](#11-معماری-mock-vs-live)
12. [مدل داده و دسته‌بندی](#12-مدل-داده-و-دسته‌بندی)
13. [قرارداد خطاها](#13-قرارداد-خطاها)
14. [وضعیت پیاده‌سازی](#14-وضعیت-پیاده‌سازی)
15. [شکاف‌های فرانت–بک](#15-شکاف‌های-فرانتبک)
16. [قراردادهای کدنویسی](#16-قراردادهای-کدنویسی)
17. [تست](#17-تست)
18. [دیپلوی](#18-دیپلوی)
19. [فایل‌های کلیدی](#19-فایل‌های-کلیدی)
20. [نکات مهم برای AI](#20-نکات-مهم-برای-ai)
21. [اصلاحات فرانت فاز ۱–۵](#21-اصلاحات-فرانت-فاز-۱۵)

---

## 1. خلاصه پروژه

**KarZar** یک پلتفرم B2B/B2C برای فروش **ابزار و تجهیزات صنعتی تراشکاری** (Industrial Lathe Tools) است.

پروژه شامل **سه اپلیکیشن جدا** است:

| اپ | مسیر | نقش | پورت dev |
|----|------|-----|----------|
| **API** | `Website/backend/` | بک‌اند FastAPI — کاتالوگ، احراز هویت، موجودی، پرداخت | `8000` |
| **Storefront** | `Website/frontend/Storefront/` | فروشگاه Next.js — PLP/PDP، سبد دو‌لاین، checkout | `3000` |
| **Admin Panel** | `Website/frontend/admin-panel/` | پنل مدیریت Next.js — CRUD، سفارش، CMS | `3001` |

**ویژگی معماری کلیدی:** هر دو فرانت یک **لایه Mock در حافظه** دارند که با env var `NEXT_PUBLIC_USE_MOCK` بدون تغییر کد به API واقعی سوئیچ می‌شوند. Mock فقط با `dynamic import` (`getMockApi`) لود می‌شود تا PIN/رمز mock وارد باندل live نشود.

**زبان UI:** فارسی، RTL (`lang="fa" dir="rtl"`)، فونت IRANYekanX.

**برند:** رنگ اصلی `#C22026` (قرمز KarZar).

---

## 2. دامنه کسب‌وکار

### محصولات
- SKU یکتا، نام، قیمت (`base_price` به صورت string یا `null`)، موجودی، واحد (`piece|kg|meter|pack`)
- مشخصات فنی در JSONB: `technical_specs[]`, `dimensions[]`, `features{}`, `optional_accessories[]`
- تصاویر چندگانه با `is_primary`
- فیلدهای بازار ایران: `warranty_text`, `weight_grams`, `is_original`, `tax_percent`
- Soft delete با `deleted_at`

### دسته‌بندی
- درخت **۳ لایه‌ای**: ریشه (depth=1) → میانی (depth=2) → برگ (depth=3)
- **فقط برگ‌های لایه ۳** می‌توانند محصول داشته باشند
- Spec template فقط برای برگ‌های لایه ۳

### مدل خرید دوگانه (Storefront)
- **Lane خرید (cart):** محصولاتی که `base_price != null` — checkout با آدرس و «پرداخت»
- **Lane استعلام (quote):** محصولاتی که `base_price == null` — checkout با نام شرکت و «ثبت استعلام قیمت»

### نقش‌های کاربر (Backend)
| نقش | استفاده فعلی |
|-----|--------------|
| `super_admin` | تمام عملیات نوشتن API + SQLAdmin |
| `b2b_customer` | تعریف شده، **endpoint ندارد** |
| `b2c_customer` | پیش‌فرض register، **endpoint ندارد** |

---

## 3. ساختار مونورپو

```
V1/
├── Karzar/                    # FastAPI backend (git submodule/repo جدا دارد)
├── admin-panel/               # Next.js admin
├── Storefront/                # Next.js shop
├── API_REQUIREMENTS_STOREFRONT.txt   # قرارداد API فروشگاه (منبع حقیقت برای endpoints فروشگاه)
├── RUN_GUIDE_FA.md            # راهنمای اجرا (۳ حالت: mock / full / deploy)
├── AI_CONTEXT.md              # همین فایل
└── scripts/
    ├── _common.ps1
    ├── start-mock-frontend.ps1
    ├── start-full-stack.ps1
    └── deploy-server.ps1
```

**نکته:** `Karzar/` داخل خودش `.git` دارد — ممکن است repo جدا باشد.

---

## 4. استک فنی

### Backend (`Karzar/`)

| لایه | تکنولوژی | نسخه |
|------|----------|------|
| Framework | FastAPI | 0.137.1 |
| ORM | SQLAlchemy 2.0 async | 2.0.27 |
| DB driver | asyncpg | 0.29.0 |
| Migration | Alembic | 1.13.1 |
| Validation | Pydantic v2 + pydantic-settings | 2.2.1 |
| Auth | python-jose (JWT) + bcrypt | — |
| Admin UI | SQLAdmin | 0.27.2 |
| Cache/Health | Redis (optional) | 5.0.1 |
| Server | uvicorn | 0.27.1 |
| Python | 3.10+ | — |
| DB | PostgreSQL 15 | — |

**Dev deps:** pytest, httpx, aiosqlite (تست با SQLite in-memory)

### Frontends (`admin-panel/` + `Storefront/`)

| لایه | تکنولوژی | نسخه |
|------|----------|------|
| Framework | Next.js App Router | 16.2.9 |
| UI | React | 19.2.4 |
| Language | TypeScript | 5.x |
| Styling | Tailwind CSS 3 + tailwindcss-logical | 3.4.17 |
| Server state | TanStack React Query | 5.101.1 |
| Client state (Storefront) | Zustand | 5.0.2 |
| HTTP | Axios | 1.18.1 |
| Forms | react-hook-form + Zod | 7.80 / 4.4 |
| Toasts (Admin) | Sonner | 2.0.7 |
| Animation (Storefront) | Framer Motion | 12.4.0 |
| Icons | react-iconly (+ lucide در admin deps) | — |
| UI primitives | shadcn-style (دست‌ساز روی Radix UI) | — |

**Path alias:** `@/*` → `src/*` در هر دو فرانت.

**Build:** `output: "standalone"` در `next.config.ts` برای Docker.

---

## 5. نحوه اجرا

راهنمای کامل: `RUN_GUIDE_FA.md`

| حالت | اسکریپت | نیاز |
|------|---------|------|
| فقط UI + Mock | `.\scripts\start-mock-frontend.ps1` | Node.js |
| Full stack | `.\scripts\start-full-stack.ps1` | Node + Docker |
| Deploy prep | `.\scripts\deploy-server.ps1 -ApiUrl ... -AdminDomain ... -StoreDomain ...` | Docker |

### Env فرانت (هر دو اپ)

```env
NEXT_PUBLIC_USE_MOCK=true|false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_MOCK_LATENCY_MS=500|650
```

### Env بک‌اند (`Karzar/.env`)

از `Karzar/.env.example` کپی کنید. فیلدهای حیاتی:
- `SECRET_KEY` — حداقل ۳۲ کاراکتر
- `POSTGRES_*` — اتصال DB
- `INITIAL_SUPER_ADMIN_PHONE/PASSWORD` — bootstrap ادمین
- `ADMIN_STEP_UP_PIN` — PIN حذف/بازیابی (در production قوی باشد)
- `CORS_ORIGINS` — دامنه‌های فرانت

### Docker Compose (dev)

`Karzar/docker-compose.yml`:
- `app` → API `:8000`
- `db` → PostgreSQL host port `:5435` (داخل container `:5432`)
- `redis` → `:6379`

---

## 6. بک‌اند (Karzar)

### معماری لایه‌ای

```
HTTP Request
    ↓
api/endpoints/*.py      ← route handlers, query params
    ↓
api/deps.py             ← JWT, super_admin, step-up
    ↓
services/*.py           ← business logic, validation, commits
    ↓
crud/*.py               ← pure DB queries
    ↓
db/models/*.py          ← SQLAlchemy ORM
    ↓
schemas/*.py            ← Pydantic request/response
    ↓
utils/product_presenter.py  ← ORM → DTO mapping
```

### Entry point

`Karzar/app/main.py`:
- Lifespan: `bootstrap_super_admin()` + `bootstrap_catalog_seed()`
- CORS + SessionMiddleware (برای SQLAdmin)
- SQLAdmin در `/admin`
- Router در `/api/v1`
- Global exception handlers → error envelope
- `/health` (liveness), `/ready` (DB+Redis readiness)

### API Endpoints (پیاده‌سازی شده)

**Base:** `/api/v1`

#### System
| Method | Path | Auth |
|--------|------|------|
| GET | `/` | — |
| GET | `/health` | — |
| GET | `/ready` | — |
| GET | `/api/v1` | — |

#### Auth (`/api/v1/auth`)
| Method | Path | Auth | توضیح |
|--------|------|------|-------|
| POST | `/register` | — | JSON body؛ قابل غیرفعال با `ALLOW_PUBLIC_REGISTER=false` |
| POST | `/login` | — | OAuth2 form: `username`=phone, `password` |
| POST | `/verify-pin` | Bearer super_admin | PIN → step-up token |

#### Products (`/api/v1/products`)
| Method | Path | Auth |
|--------|------|------|
| POST | `/` | super_admin |
| GET | `/` | — |
| GET | `/sku/{sku}` | — |
| GET | `/{product_id}` | — |
| PUT | `/{product_id}` | super_admin |
| DELETE | `/{product_id}` | super_admin + **X-Step-Up-Token** |
| POST | `/{product_id}/restore` | super_admin + step-up |
| GET | `/{product_id}/stock` | — |
| POST | `/{product_id}/stock/adjust?quantity_delta=` | super_admin |

**فیلتر لیست:** `skip`, `limit`, `category_id`, `brand_id`, `is_active`, `search`, `min_price`, `max_price`, `filters` (JSON), `spec_*` prefixed params.

**پاسخ لیست:**
```json
{
  "data": [ ProductSummary... ],
  "meta": { "total_count", "skip", "limit", "has_next", "has_prev" }
}
```

#### Categories (`/api/v1/categories`)
| Method | Path | Auth |
|--------|------|------|
| GET | `/` | — | flat list با depth/breadcrumb |
| POST | `/` | super_admin |
| PUT | `/{category_id}` | super_admin |
| DELETE | `/{category_id}` | super_admin + step-up |
| GET | `/tree` | — | nested tree |
| GET | `/{category_id}/spec-templates` | — | فقط leaf depth-3 |

#### Brands (`/api/v1/brands`)
| Method | Path | Auth |
|--------|------|------|
| GET | `/` | — |
| POST | `/` | super_admin |
| PUT | `/{brand_id}` | super_admin |
| DELETE | `/{brand_id}` | super_admin (بدون step-up) |

#### SQLAdmin
- URL: `http://localhost:8000/admin`
- Login: phone + password (فقط `super_admin` فعال)

### مدل‌های DB

**فایل:** `Karzar/app/db/models/`

```
Category (self-ref parent_id)
  └── Product (category_id nullable, brand_id nullable)
        └── ProductImage (cascade delete)

Brand
  └── Product

User (standalone)
```

**Enums:**
- `StockUnitEnum`: piece, kg, meter, pack
- `UserRole`: super_admin, b2b_customer, b2c_customer

**Audit:** همه مدل‌ها `created_at`, `updated_at` از `base.py`.

**Product JSONB specs default:**
```json
{
  "technical_specs": [],
  "features": {},
  "dimensions": [],
  "optional_accessories": []
}
```

### Migrations (Alembic)

| Revision | توضیح |
|----------|-------|
| `9bbd02b667e6` | schema اولیه catalog |
| `b51b18fa0c0b` | users + roles |
| `d4552516cd6a` | فیلدهای بازار ایران + soft delete |
| `e7f8a9b0c1d2` | fix enums + numeric |
| `f1a2b3c4d5e6` | category_id nullable |

**Head:** `f1a2b3c4d5e6`

### Seed

| منبع | چه زمانی | محتوا |
|------|----------|-------|
| `startup.py` bootstrap | اولین اجرا اگر خالی | ۱ root + ۱ subcategory + ۳ brand |
| `scripts/seed_categories.py` | دستی | ۱۲۵ category (حذف products اول!) |
| `scripts/seed_brands.py` | دستی | ۲۲ brand |

### Config کامل

`Karzar/app/core/config.py` — Pydantic Settings از `.env`.

متغیرهای مهم: `SECRET_KEY`, `POSTGRES_*`, `REDIS_HOST` (خالی = غیرفعال), `ADMIN_STEP_UP_PIN`, `STEP_UP_MAX_ATTEMPTS`, `STEP_UP_ATTEMPT_WINDOW_SECONDS`, `ALLOW_PUBLIC_REGISTER`, `CORS_ORIGINS`, `DEBUG`, `INITIAL_SUPER_ADMIN_*`, `NOTION_*` (استفاده نمی‌شود).

### سرویس‌های جانبی

| سرویس | فایل | وضعیت |
|--------|------|-------|
| Notion sync | `notion_service.py` | stub — فقط log |
| Spec templates | `spec_template_service.py` | فعال — بر اساس نام دسته |
| Redis | health only | بدون cache/session |

---

## 7. پنل ادمین (admin-panel)

### ساختار `src/`

```
src/
├── app/
│   ├── layout.tsx, providers.tsx, globals.css
│   ├── login/                    # صفحه ورود
│   └── (dashboard)/              # route group — در URL نیست
│       ├── layout.tsx            # AuthGate + Sidebar + Header
│       ├── page.tsx              # داشبورد آمار
│       ├── catalog/
│       │   ├── products/         # list, new, [id]/edit
│       │   └── categories/     # مدیریت ۳ ستونی + brands modal
│       ├── orders/               # ComingSoon
│       ├── quotes/               # ComingSoon
│       ├── customers/            # ComingSoon
│       ├── reports/              # ComingSoon
│       ├── documents/            # ComingSoon
│       └── settings/             # ComingSoon
├── components/
│   ├── auth-gate.tsx, step-up-dialog.tsx, coming-soon.tsx
│   ├── layout/ (sidebar, header, nav.config.tsx)
│   └── ui/ (shadcn-style primitives)
├── config/env.ts
├── features/
│   ├── auth/queries.ts
│   └── catalog/ (queries, product-schema, components, utils)
├── hooks/use-logout.ts
├── lib/ (api-client, mock-api, utils)
├── services/ (auth.ts, catalog.ts)
└── types/ (auth, category, product, spec-template, common)
```

### Routes

| URL | وضعیت |
|-----|-------|
| `/login` | ✅ |
| `/` | ✅ داشبورد |
| `/catalog/products` | ✅ |
| `/catalog/products/new` | ✅ |
| `/catalog/products/[id]/edit` | ✅ |
| `/catalog/categories` | ✅ |
| `/orders`, `/quotes`, `/customers`, `/reports`, `/documents`, `/settings` | 🔲 ComingSoon |

### Data flow

```
Page/Component
  → features/catalog/queries.ts (React Query)
  → services/catalog.ts
  → if env.USE_MOCK: mockApi else apiClient
```

**مهم:** `services/auth.ts` همیشه live است — mock ندارد.

### Auth (Admin)

1. `POST /auth/login` با form-urlencoded
2. Token در `localStorage["karzar.access_token"]`
3. `AuthGate` چک می‌کند token وجود دارد
4. Axios interceptor: 401 → logout + redirect `/login?next=`
5. حذف محصول/دسته: `StepUpDialog` → `POST /auth/verify-pin` → header `X-Step-Up-Token`

**Mock mode bypass login:**
```javascript
localStorage.setItem('karzar.access_token', 'mock-dev-token');
location.href = '/';
```

**Mock PIN:** `84729101` → token `mock-step-up.{timestamp}`

### Mock API (`src/lib/mock-api.ts`)

داده seed: ۴ دسته تو در تو، ۵ برند، ۶ محصول نمونه.  
تمام CRUD catalog + verifyPin. خطاها به صورت `ApiError` با همان `error_code`های live.

### فرم محصول

- Zod schema: `features/catalog/product-schema.ts`
- Spec form داینامیک: `product-specifications-form.tsx` از template دسته
- دسته فقط leaf لایه ۳: `category-leaf-combobox.tsx` + `isLayer3Leaf()` در `category-tree.ts`
- Mapper: `toProductCreatePayload` / `toProductUpdatePayload`

### React Query defaults (`providers.tsx`)

- `staleTime: 60s`, `gcTime: 5min`, `retry: 1`, `refetchOnWindowFocus: false`
- mutations: `retry: 0`
- Query keys: `catalogKeys` در `features/catalog/queries.ts`

---

## 8. فروشگاه (Storefront)

### ساختار `src/`

```
src/
├── app/                    # 12 route — همه thin page → *-view.tsx
├── components/
│   ├── layout/             # header, footer, mega-menu, mobile nav
│   ├── home/               # sections صفحه اصلی
│   ├── catalog/            # PLP + filters
│   ├── product/            # PDP
│   ├── cart/               # سبد خرید و استعلام
│   ├── checkout/           # wizard 2 مرحله‌ای
│   ├── blog/, auth/, contact/, about/
│   └── ui/
├── config/env.ts
├── data/mock-data.ts       # seed data — منبع حقیقت mock
├── features/catalog/queries.ts, checkout/queries.ts
├── lib/ (api-client, mock-api, category-tree, utils, validation)
├── services/ (catalog, checkout, auth)
├── store/ (cart-store.ts, ui-store.ts)
└── types/
```

### Routes

| URL | View |
|-----|------|
| `/` | Home sections |
| `/catalog` | CatalogView + filters در query string |
| `/product/[id]` | ProductDetailView |
| `/cart` | CartView mode=cart |
| `/quote` | CartView mode=quote |
| `/checkout` | CheckoutView (`?mode=quote` برای استعلام) |
| `/checkout/success` | SuccessView (`?ref=&mode=`) |
| `/blog`, `/blog/[slug]` | BlogList, ArticleView |
| `/login` | LoginView (OTP) |
| `/about`, `/contact` | static |

### Zustand stores

**`cart-store.ts`** (persisted: `karzar.storefront.cart`):
```typescript
{
  cart: CartLine[],    // خرید با قیمت
  quote: CartLine[],   // استعلام
  addToCart(product, qty),
  addToQuote(product, qty),
  // ...
}
```

**`ui-store.ts`:** `mobileMenuOpen`, `filterDrawerOpen`, `megaMenuOpen`

### Checkout flow

```
Step 1: AuthStep
  - مهمان: نام + موبایل
  - OTP inline
  - skip اگر token موجود

Step 2: DetailsStep
  - purchase → آدرس + «پرداخت»
  - inquiry → شرکت + توضیح + «ثبت استعلام»

Submit → checkoutService.submit(CheckoutPayload)
Success → clear basket → /checkout/success?ref=KZ-...&mode=...
```

### Catalog URL params (`use-catalog-params.ts`)

| Query | API param |
|-------|-----------|
| `category` | `category_id` |
| `brand` | `brand_id` |
| `search`, `country`, `min_price`, `max_price`, `in_stock`, `sort` | همان |

### Mock data (`data/mock-data.ts`)

| Export | تعداد |
|--------|-------|
| CATEGORIES | 22 (درخت ۳ لایه) |
| BRANDS | 5 |
| PRODUCTS | 12 |
| COMMENTS | 3 |
| BLOG_POSTS / ARTICLES | 3 |
| HERO_SLIDES | 2 |

**OTP mock:** کد `"11111"` (در `dev_code` برمی‌گردد)

### Token storage

`localStorage["karzar.storefront.token"]` — جدا از admin panel.

---

## 9. قرارداد API و ماتریس یکپارچگی

### Admin Panel → Backend (وقتی `USE_MOCK=false`)

| سرویس | Endpoint | وضعیت بک |
|-------|----------|----------|
| login | `POST /auth/login` | ✅ |
| verifyPin | `POST /auth/verify-pin` | ✅ |
| products CRUD | `/products/` | ✅ |
| categories CRUD | `/categories/` | ✅ |
| category tree | `GET /categories/tree` | ✅ |
| spec template | `GET /categories/{id}/spec-templates` | ✅ |
| brands CRUD | `/brands/` | ✅ |

### Storefront → Backend

**منبع قرارداد کامل:** `API_REQUIREMENTS_STOREFRONT.txt`

| سرویس | Endpoint | وضعیت بک |
|-------|----------|----------|
| category tree | `GET /categories/tree` | ✅ |
| flat categories | `GET /categories/` | ✅ |
| brands | `GET /brands/` | ✅ |
| products list/detail | `GET /products/` | ✅ |
| related products | `GET /products/{id}/related` | ❌ **ندارد** |
| comments | `GET /products/{id}/comments` | ❌ **ندارد** |
| blog list | `GET /blog/` | ❌ **ندارد** |
| blog post | `GET /blog/{slug}` | ❌ **ندارد** |
| hero slides | `GET /hero-slides/` | ❌ **ندارد** |
| checkout | `POST /checkout` | ❌ **ندارد** |
| contact | `POST /contact` | ❌ **ندارد** |
| OTP request | `POST /auth/otp/request` | ❌ **ندارد** |
| OTP verify | `POST /auth/otp/verify` | ❌ **ندارد** |

**نتیجه:** Storefront با `USE_MOCK=false` فقط بخش catalog کار می‌کند؛ checkout، blog، OTP و hero نیاز به پیاده‌سازی بک دارند.

### تفاوت auth ادمین vs فروشگاه

| | Admin | Storefront |
|---|-------|------------|
| روش | phone + password (OAuth2 form) | OTP (request + verify) |
| Token key | `karzar.access_token` | `karzar.storefront.token` |
| Mock login | bypass دستی localStorage | mock OTP کد `11111` |

---

## 10. احراز هویت

### JWT Access Token (Backend)

- Algorithm: HS256
- Payload: `{ sub: phone_number, exp, type: "access" }`
- TTL: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30)
- **بدون refresh token**

### Step-Up (عملیات مخرب)

```
1. POST /auth/verify-pin  { "pin": "..." }  + Bearer JWT
2. Response: { secure_token, token_type: "step_up", expires_in }
3. DELETE/restore: header X-Step-Up-Token: <secure_token>
```

Rate limit PIN: in-memory، ۵ تلاش در ۳۰۰ ثانیه per phone.

### Dependencies (`api/deps.py`)

- `get_current_user` — JWT معتبر
- `get_current_super_admin` — role == super_admin
- `get_verified_step_up` — step-up token معتبر
- `get_current_super_admin_with_step_up` — هر دو

---

## 11. معماری Mock vs Live

### Pattern مشترک (هر دو فرانت)

```typescript
// config/env.ts
export const env = {
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
  USE_MOCK: (process.env.NEXT_PUBLIC_USE_MOCK ?? "true").toLowerCase() !== "false",
  MOCK_LATENCY_MS: Number(process.env.NEXT_PUBLIC_MOCK_LATENCY_MS ?? 500),
};

// services/*.ts
async someMethod(params) {
  if (env.USE_MOCK) return mockApi.someMethod(params);
  const { data } = await apiClient.get/post(...);
  return data;
}
```

### قوانین

1. **Components هرگز مستقیم axios/mock نزنند** — فقط `services/*`
2. **Types در `types/`** mirror کنند `Karzar/app/schemas/*.py`
3. **Mock باید همان shape و error_code** برگرداند
4. **تغییر env نیاز به restart dev server** دارد (NEXT_PUBLIC_* build-time در production)

### فایل‌های mock

| اپ | Mock impl | Seed data |
|----|-----------|-----------|
| admin-panel | `src/lib/mock-api.ts` | inline در همان فایل |
| Storefront | `src/lib/mock-api.ts` | `src/data/mock-data.ts` |

---

## 12. مدل داده و دسته‌بندی

### قانون ۳ لایه (حیاتی)

```
Depth 1 (root)     → مثلاً «ابزار برقی»
  Depth 2 (mid)    → مثلاً «دریل و دریل شارژی»
    Depth 3 (leaf) → مثلاً «دریل چکشی» ← فقط اینجا product + spec template
```

**توابع کلیدی:**
- Admin: `src/features/catalog/utils/category-tree.ts` → `isLayer3Leaf()`, `flattenCategoryTree()`
- Storefront: `src/lib/category-tree.ts` → `collectDescendantIds()` برای فیلتر subtree
- Backend: `app/utils/category_depth.py`, `app/utils/category_tree.py`

### قیمت

- همیشه **string** در API (مثلاً `"1250000.00"`) یا `null`
- UI با `Number()` parse می‌کند
- `null` = lane استعلام در Storefront

### Stock status (محاسبه در presenter/mock)

`in_stock` | `low_stock` | `out_of_stock` — از `availability`, `stock_quantity`, `low_stock`

---

## 13. قرارداد خطاها

### Envelope (همه 4xx/5xx)

```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "Request validation failed",
  "details": [
    { "field": "sku", "message": "already exists" }
  ]
}
```

### Error codes (`Karzar/app/core/errors.py`)

`UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `VALIDATION_FAILED`, `STEP_UP_REQUIRED`, `STEP_UP_INVALID`, `RATE_LIMITED`, `INTERNAL_ERROR`, ...

### Frontend handling

```typescript
// lib/api-client.ts
class ApiError {
  status: number;
  code: ErrorCode | string;
  message: string;
  fieldErrors: Record<string, string>;  // از details[] map شده
}
```

در فرم‌ها: `catch (ApiError)` → `setError` روی react-hook-form + Sonner toast.

---

## 14. وضعیت پیاده‌سازی

### ✅ انجام شده

| بخش | جزئیات |
|-----|--------|
| Backend catalog API | products, categories, brands, stock, filters, soft delete |
| Backend auth | register, login, verify-pin, step-up |
| SQLAdmin | CRUD همه مدل‌ها + ProductImage |
| Admin catalog UI | products CRUD, categories 3-column, brands modal, spec forms |
| Admin dashboard | آمار از catalog |
| Storefront UI | home, catalog PLP, PDP, cart/quote, checkout wizard, blog, contact, about |
| Storefront mock | کامل برای همه features |
| Docker dev | compose با postgres + redis |
| Tests | product endpoints, category tree, jsonb filters |
| Run scripts | mock, full-stack, deploy prep |

### 🔲 ناقص / Planned (ناوبری وجود دارد، UI نیست)

| بخش | مسیر admin |
|-----|------------|
| Orders | `/orders` |
| Quotes management | `/quotes` |
| Customers | `/customers` |
| Reports | `/reports` |
| Documents | `/documents` |
| Settings | `/settings` |

### ❌ بک‌اند وجود ندارد (فرانت mock دارد)

- Storefront checkout API
- Storefront OTP auth
- Blog/CMS API
- Hero slides API
- Contact form API
- Product comments API
- Related products API
- Orders/quotes/customers (کل domain commerce)

### ⚠️ ناسازگاری‌های شناخته‌شده

1. **depth category:** بک‌اند seed_categories ۴+ لایه دارد؛ spec template فقط depth-3
2. **category_id nullable** در DB ولی required در `ProductCreate` schema
3. **تصاویر محصول:** فقط SQLAdmin — REST API برای upload ندارد
4. **Brand delete** step-up نمی‌خواهد؛ product/category delete می‌خواهند
5. **Roles b2b/b2c** تعریف شده، استفاده نمی‌شود
6. **Notion integration** stub است
7. **Redis** فقط health check

---

## 15. شکاف‌های فرانت–بک

اگر task شما «وصل کردن Storefront به بک واقعی» است، این endpoints را باید در `Karzar/app/api/endpoints/` بسازید طبق `API_REQUIREMENTS_STOREFRONT.txt`:

**اولویت بالا:**
1. `POST /auth/otp/request` + `POST /auth/otp/verify`
2. `POST /checkout`
3. `GET /products/{id}/related`
4. `GET /products/{id}/comments`

**اولویت متوسط:**
5. `GET /blog/`, `GET /blog/{slug}`
6. `GET /hero-slides/`
7. `POST /contact`

**برای admin commerce modules:**
- Order, Quote, Customer models + CRUD
- Admin panel pages جایگزین ComingSoon

---

## 16. قراردادهای کدنویسی

### Backend (Python)

- Async everywhere: `async def` endpoints, `AsyncSession`
- Business logic در `services/` نه `endpoints/`
- DB queries فقط در `crud/`
- Response mapping در `utils/product_presenter.py`
- خطاها: `raise HTTPException` یا helpers از `core/errors.py`
- Migration: `alembic revision --autogenerate` سپس `upgrade head`

### Frontend (TypeScript)

- `"use client"` فقط جایی که لازم (hooks, state, events)
- Pages نازک — logic در `*-view.tsx` یا `features/`
- React Query hooks در `features/<domain>/queries.ts`
- Query keys متمرکز (`catalogKeys`)
- RTL: logical properties (`ms-`, `me-`, `ps-`, `pe-`) + `tailwindcss-logical`
- اعداد فارسی: `formatToman()`, `formatNumber()` از `lib/utils.ts`
- `cn()` = clsx + tailwind-merge
- Icons: `react-iconly` (نام string برای category roots در mock)

### Naming

- Backend schemas: `ProductCreate`, `ProductDetailResponse`, ...
- Frontend types: mirror در `types/product.ts` با کامنت `mirrors app/schemas/product.py`
- API paths: snake_case query params, plural resources (`/products/`)

### Git

- `Karzar/` repo جدا — commit جداگانه
- فقط وقتی کاربر بخواهد commit کن

---

## 17. تست

### Backend

```bash
cd Website/backend
pip install -r requirements-dev.txt
pytest -v
```

### Frontend (فاز ۵)

```bash
# Unit (Vitest)
cd Website/frontend/Storefront && npm test
cd Website/frontend/admin-panel && npm test

# E2E smoke (Playwright, mock mode via webServer env)
cd Website/frontend/Storefront && npx playwright install chromium && npm run test:e2e
cd Website/frontend/admin-panel && npx playwright install chromium && npm run test:e2e
```

**Unit پوشش:** validation (phone/shipping)، idempotency scope، pending-payment TTL، cart lanes، sanitizeNextPath، stepUpPinSchema.

**E2E دود:** OTP→checkout→callback (Storefront mock)؛ login→products→step-up PIN (admin mock).

---

## 18. دیپلوی

### فایل‌های deploy

```
deploy/
├── docker-compose.prod.yml      # تولید شده توسط deploy-server.ps1
├── karzar.env.production.example
└── nginx.karzar.conf.example
```

### Production stack

- API, PostgreSQL, Redis در Docker
- Admin + Storefront به صورت Next.js standalone containers
- Nginx reverse proxy + SSL (Let's Encrypt)
- `NEXT_PUBLIC_*` در **build time** Docker ARG

### نکات امنیتی production

- `DEBUG=False`
- `SECRET_KEY` قوی
- `ADMIN_STEP_UP_PIN` قوی
- `CORS_ORIGINS` محدود به دامنه‌های واقعی
- DB/Redis expose نشود به اینترنت

---

## 19. فایل‌های کلیدی

### Must-read قبل از هر task

| فایل | چرا |
|------|-----|
| `API_REQUIREMENTS_STOREFRONT.txt` | قرارداد API فروشگاه |
| `Karzar/docs/FRONTEND_HANDOVER.md` | خلاصه API برای فرانت |
| `Karzar/docs/FRONTEND_INTEGRATION.md` | جزئیات integration |
| `RUN_GUIDE_FA.md` | نحوه اجرا |
| `admin-panel/src/services/catalog.ts` | الگوی mock/live facade |
| `Storefront/src/services/catalog.ts` | همان الگو |
| `Storefront/src/data/mock-data.ts` | شکل داده فروشگاه |
| `admin-panel/src/lib/mock-api.ts` | شکل داده ادمین |
| `Karzar/app/core/errors.py` | error codes |
| `Karzar/app/schemas/product.py` | product contracts |

### Backend entry points

| Task | فایل |
|------|------|
| route جدید | `app/api/endpoints/` + register در `app/api/v1/__init__.py` |
| model جدید | `app/db/models/` + alembic migration |
| business rule | `app/services/` |
| auth dependency | `app/api/deps.py` |

### Frontend entry points

| Task | Admin | Storefront |
|------|-------|------------|
| صفحه جدید | `src/app/(dashboard)/...` | `src/app/...` |
| data hook | `src/features/catalog/queries.ts` | `src/features/*/queries.ts` |
| API call | `src/services/catalog.ts` | `src/services/*.ts` |
| mock data | `src/lib/mock-api.ts` | `src/data/mock-data.ts` + `src/lib/mock-api.ts` |
| types | `src/types/` | `src/types/` |

---

## 20. نکات مهم برای AI

### قبل از کد زدن

1. **تعیین کن کدام اپ:** Karzar / admin-panel / Storefront
2. **Mock یا live?** اگر بک endpoint ندارد، یا mock را گسترش بده یا بک بساز
3. **دسته ۳ لایه** را رعایت کن — product فقط روی leaf
4. **قیمت string** — هرگز number در API response
5. **دو token storage جدا** — admin و storefront قاطی نکن

### الگوهای رایج task

| Task | مسیر پیشنهادی |
|------|---------------|
| فیلد جدید محصول | model → migration → schema → crud → service → endpoint → types → mock → form |
| endpoint فروشگاه جدید | `API_REQUIREMENTS_STOREFRONT.txt` → endpoint → service → storefront types → mock-api → service facade |
| صفحه admin جدید | `app/(dashboard)/` → view component → features/queries → service → ComingSoon را حذف |
| فیلتر PLP جدید | mock-api filter logic → catalog service → use-catalog-params → filter-panel |

### اشتباهات رایج

- ❌ فراخوانی مستقیم `apiClient` از component
- ❌ فراموش کردن `catalogKeys` invalidation بعد از mutation
- ❌ استفاده از `category_id` روی non-leaf در فرم محصول
- ❌ انتظار login mock در admin بدون bypass
- ❌ `USE_MOCK=false` برای storefront بدون endpoints checkout/blog
- ❌ commit کردن `.env` با secrets
- ❌ hard delete محصول از API (فقط soft delete + restore)

### وقتی admin-panel را توسعه می‌دهی

- Nav items در `nav.config.tsx` — `matchPrefix: true` برای nested routes
- Delete flows همیشه از `StepUpDialog` + `useVerifyPin`
- `ComingSoon` component برای stub pages

### وقتی Storefront را توسعه می‌دهی

- Cart hydration: چک `mounted` قبل از نمایش count
- `Suspense` برای pages با `useSearchParams`
- دو سبد جدا: `cart` vs `quote` در Zustand
- `base_price == null` → UI استعلام قیمت

### وقتی Backend را توسعه می‌دهی

- Destructive ops: `get_current_super_admin_with_step_up`
- List endpoints: همیشه pagination meta
- Product list: subtree category filter
- Run `pytest` بعد از تغییر
- `alembic upgrade head` بعد از migration

---

## پیوست A — نمونه payloadها

### Product Create (Admin → API)

```json
{
  "sku": "TOOL-001",
  "name": "اینسرت الماس CCGT",
  "category_id": 100,
  "brand_id": 1,
  "base_price": "1250000.00",
  "stock_quantity": "50",
  "stock_unit": "piece",
  "is_active": true,
  "specifications": {
    "technical_specs": [{ "key": "range", "value": "0-150mm" }],
    "features": { "coated": true },
    "dimensions": [],
    "optional_accessories": []
  }
}
```

### Checkout Payload (Storefront mock)

```json
{
  "mode": "purchase",
  "customer": { "full_name": "...", "phone": "0912...", "is_guest": true },
  "items": [{ "product_id": 1, "quantity": 2 }],
  "shipping": { "province": "...", "city": "...", "address": "...", "postal_code": "..." }
}
```

### Login (Admin — form-urlencoded)

```
username=09120000000&password=Admin@123456
```

---

## پیوست B — پکیج‌های npm (خلاصه)

### admin-panel dependencies
`next`, `react`, `react-dom`, `@tanstack/react-query`, `axios`, `react-hook-form`, `@hookform/resolvers`, `zod`, `@radix-ui/*`, `cmdk`, `sonner`, `react-iconly`, `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`, `tailwindcss-animate`

### Storefront dependencies
همان‌ها + `zustand`, `framer-motion`, `tailwindcss-logical` (بدون Radix/cmdk/sonner)

---

## پیوست C — مستندات موجود

| فایل | مخاطب |
|------|--------|
| `Karzar/README.md` | بک‌اند dev |
| `Karzar/docs/FRONTEND_HANDOVER.md` | فرانت‌اند dev |
| `Karzar/docs/FRONTEND_INTEGRATION.md` | integration |
| `Karzar/architecture.txt` | معماری (کمی outdated) |
| `RUN_GUIDE_FA.md` | اجرا و deploy |
| `API_REQUIREMENTS_STOREFRONT.txt` | قرارداد storefront API |

---

## 21. اصلاحات فرانت فاز ۱–۵

برنامهٔ remediation (بدون بازنویسی بی‌جهت):

| فاز | موضوع | وضعیت |
|-----|--------|--------|
| **۱ Critical** | Idempotency پایدار؛ pending payment در session+local؛ sanitize `?next=`؛ refresh قبل از logout؛ bulk stock + step-up؛ بنر Reports؛ CSP `connect-src` لوکال | انجام‌شده |
| **۲ Session/Cart** | reconcile سبد بعد OTP؛ AuthGate + `/auth/me`؛ middleware نشانگر نرم؛ mock-api فقط dynamic import؛ قرارداد cookie HttpOnly (طراحی) | انجام‌شده |
| **۳ Honesty UX** | تایم‌لاین تخمینی؛ SMS نرم؛ تب purchase/inquiry؛ نام/تصویر کالا؛ moderation کامنت؛ `/terms`؛ رمز اختیاری فقط mock؛ حذف زنگ تزئینی؛ `error`/`loading` | انجام‌شده |
| **۴ SEO/Perf** | هوم RSC + prefetch؛ sitemap `/product/{id}`؛ PDP تنبل related/comments؛ allowlist تصویر | انجام‌شده |
| **۵ Hardening** | Vitest + Playwright دود؛ README/.env.example؛ CSP بدون `unsafe-eval` در production؛ skip-link + focus trap منو موبایل؛ به‌روزرسانی همین سند | انجام‌شده |

**خارج از محدوده تا آمادگی BE:** verify فقط با `authority`؛ نشست کاملاً cookie HttpOnly؛ category landing pages.

فایل قرارداد cookie: `frontend/docs/auth-cookie-httponly-contract.md`.

---

*این سند را هنگام تغییرات معماری یا اضافه شدن ماژول‌های جدید به‌روز کنید.*
