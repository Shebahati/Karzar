# نقشه Refactor ساختار Backend — فایل‌به‌فایل

**نسخه:** 1.0 — 2026-07-18  
**مخاطب:** تیم Backend  
**هدف:** تمیزسازی ساختار بدون تغییر رفتار API (behavior-preserving)  
**وضعیت:** R0–R2 اجرا شده (2026-07-18)؛ R3 جزئی (`product_review_service` + OTP via `crud.otp`)؛ R4 rename تست‌ها عمداً به تعویق (بدون تغییر رفتار کافی است).

**پیش‌نیاز ذهنی:** اسکلت فعلی (`api → services → crud → models`) درست است. مشکل انباشت و نقض گاه‌به‌گاه لایه‌هاست، نه نبود معماری.

---

## 0. اصول ثابت (قبل از هر حرکت)

1. **هیچ قرارداد API عوض نشود** مگر در PR جدا و با changelog.
2. **هر PR فقط یک دامنه** (مثلاً فقط product images، نه هم‌زمان OTP).
3. بعد از هر PR: `pytest` کامل سبز.
4. قانون هدف لایه‌ها:
   ```text
   endpoints/*  →  فقط services + schemas + deps
   services/*   →  crud + models + utils خالص
   crud/*       →  فقط SQLAlchemy / models
   utils/*      →  بدون DB session (ترجیحاً)
   ```
5. import مستقیم `crud` از endpoint ممنوع می‌شود (به‌تدریج؛ با ruff/custom lint در انتها).

---

## 1. وضعیت فعلی → هدف (نمای کلی)

### فعلی (ساده)

```text
app/
  api/endpoints/     # 10 فایل؛ product.py غول‌پیکر
  services/          # 19 فایل؛ بعضی خوب، بعضی نازک
  crud/              # 8 فایل؛ platform/content شلوغ
  utils/             # 15 فایل؛ ۵تای category پراکنده
  admin/             # مرده
```

### هدف (دامنه‌محور، بدون microservice)

```text
app/
  api/
    deps.py
    v1/__init__.py
    endpoints/
      auth.py
      catalog/          # NEW package
        products_public.py
        products_admin.py
        products_images.py
        products_reviews.py
        categories.py
        brands.py
      commerce/
        cart.py
        checkout.py     # از storefront جدا
        orders.py
        payments.py
      content/
        storefront_cms.py   # blog/hero/contact عمومی
        cms_admin.py        # /cms/*
      users.py
  services/             # همان نام‌ها؛ مسئولیت شفاف‌تر
  crud/
    catalog/
    commerce/
    auth/
    content/
    platform/           # فقط cross-cutting واقعی
  domains/              # اختیاری فاز آخر: utils دامنه اینجا جمع شود
  core/
  db/models/            # بدون تغییر ساختاری اجباری
```

اگر packageهای تو در تو سنگین به نظر می‌رسد، **حداقل نسخه امن** همین است که در §3 آمده (فقط شکستن فایل‌های بزرگ، بدون جابه‌جایی عمیق پوشه).

---

## 2. فازبندی اجرا

| فاز | نام | ریسک | خروجی |
|-----|-----|------|--------|
| **R0** | پاکسازی ریشه / مرده‌ها | خیلی کم | repo خلوت |
| **R1** | شکستن god-fileها (بدون جابه‌جایی پوشه) | کم | خوانایی |
| **R2** | شکستن kitchen-sinkهای crud | کم–متوسط | مرز دامنه |
| **R3** | یکنواخت‌سازی لایه‌ها (endpoint فقط service) | متوسط | معماری پایدار |
| **R4** | تست‌ها و docs هم‌تراز ساختار | کم | نگهداری |

پیشنهاد: **R0 → R1 → R2 → R3**. R4 موازی با R1/R2.

---

## 3. فاز R0 — پاکسازی ایمن ریشه

| # | اقدام | مسیر | نوع | یادداشت |
|---|--------|------|-----|---------|
| R0.1 | حذف پوشه مرده | `app/admin/` | delete | فقط `__pycache__`؛ SQLAdmin دیگر نیست |
| R0.2 | یک venv نگه دارید | `.venv` نگه؛ `venv/` و `.venv312/` حذف یا از gitignore/دیسک محلی | local | در repo commit نشوند |
| R0.3 | حذف artifact | `.coverage` | delete + gitignore | |
| R0.4 | جابه‌جایی نمونه | `sample_product.json` → `docs/examples/` یا `data/samples/` | move | |
| R0.5 | docs ریشه | `BACKEND_CHANGES.md` → `docs/BACKEND_CHANGES.md` | move | لینک‌ها را آپدیت کنید |
| R0.6 | architecture | `architecture.txt` → `docs/ARCHITECTURE.md` | move+rename | اختیاری |

**معیار Done R0:** ریشه فقط config/compose/README/requirements داشته باشد؛ بدون پوشه خالی/مرده.

---

## 4. فاز R1 — شکستن god-fileها (حداقل نسخه امن)

> مسیرها همان `app/api/endpoints/` می‌مانند؛ فقط فایل‌ها شکسته می‌شوند و از `__init__` یا `v1` include می‌شوند.

### 4.1 `app/api/endpoints/product.py` (~818 خط) → ۴ فایل

| فایل جدید | مسئولیت | routeهای تقریبی |
|-----------|----------|-----------------|
| `products_catalog.py` | PLP/PDP عمومی | `GET /`, `GET /{id}`, `GET /sku/{sku}`, `GET /{id}/related`, `GET /statistics` |
| `products_admin.py` | CRUD ادمین + soft delete/restore + stock | `POST /`, `PUT /{id}`, `DELETE /{id}`, `POST /{id}/restore`, `POST /{id}/stock/adjust`, bulk stock |
| `products_images.py` | تصاویر | `POST /{id}/images`, delete/primary/reorder |
| `products_reviews.py` | نظرات | `GET/POST /{id}/comments` |

**ترتیب کار داخل PR:**
1. کپی توابع به فایل جدید بدون تغییر signature.
2. `api/v1/__init__.py`: چند `include_router` با همان `prefix="/products"`.
3. حذف محتوای قدیمی از `product.py` یا تبدیل به re-export موقت.
4. تست‌های `test_product_endpoints.py` باید بدون تغییر assertion پاس شوند.

**خطر:** ترتیب route در FastAPI (`/sku/{sku}` قبل از `/{product_id}`). امروز درست است؛ بعد از شکستن هم همان ترتیب include را حفظ کنید.

### 4.2 `app/api/endpoints/storefront.py` → ۲ فایل

| فایل جدید | مسئولیت |
|-----------|----------|
| `storefront_content.py` | blog, articles alias, hero-slides, contact |
| `checkout.py` | فقط `POST /checkout` (+ throttle/idempotency) |

### 4.3 `app/api/endpoints/auth.py` (~398 خط) → ۲–۳ فایل (اختیاری ولی مفید)

| فایل | مسئولیت |
|------|----------|
| `auth_session.py` | login, refresh, logout, me, change-password |
| `auth_otp.py` | otp request/verify, password-reset |
| `auth_step_up.py` | verify-pin |

می‌تواند در R1 یا R3 انجام شود.

### 4.4 سرویس‌های پرداخت (از قبل نسبتاً شکسته؛ فقط مرز را ثابت کنید)

| فایل فعلی | نقش تثبیت‌شده |
|-----------|----------------|
| `payment_service.py` | adapter درگاه (mock/zarinpal) |
| `payment_flow_service.py` | init/verify جریان سفارش |
| `payment_ledger_service.py` | ledger |
| `endpoints/payment.py` | HTTP فقط؛ منطق جدید نرود داخل endpoint |

**معیار Done R1:** هیچ endpoint فایلی > ~350 خط نباشد؛ OpenAPI paths یکسان.

---

## 5. فاز R2 — شکستن kitchen-sinkهای CRUD

### 5.1 `app/crud/platform.py` (~403 خط) → ۴ فایل

| فایل جدید | توابع منتقل‌شونده |
|-----------|-------------------|
| `crud/cart.py` | `get_or_create_cart`, `get_cart_with_items`, `upsert_cart_item`, `remove_cart_item`, `clear_cart_items`, `merge_guest_cart_into_user` |
| `crud/refresh_tokens.py` | `store/get_valid/revoke*` |
| `crud/audit.py` | `record_audit_log`, `list_audit_logs`, `record_product_change`, `list_product_change_logs` |
| `crud/idempotency.py` | `get/store/reserve/finalize/delete_idempotency_record`, `consume_step_up_jti` |

`platform.py` موقتاً می‌تواند re-export کند تا importهای قدیمی نشکنند:

```python
# app/crud/platform.py — shim موقت
from app.crud.cart import *  # noqa: F403
from app.crud.idempotency import *  # noqa: F403
...
```

سپس در PR بعدی shim حذف شود.

### 5.2 `app/crud/content.py` (~267 خط) → ۳ فایل

| فایل جدید | محتوا |
|-----------|--------|
| `crud/cms_articles.py` | articles |
| `crud/cms_media.py` | hero slides + product comments |
| `crud/otp.py` | `create_otp_code`, `get_valid_otp`, `delete_otp` |
| `crud/contact.py` | contact submissions |

**مهم:** OTP از content جدا شود — الان بزرگ‌ترین smell دامنه است.

### 5.3 `app/crud/product.py` (~535 خط) — شکستن اختیاری

| فایل | مسئولیت |
|------|----------|
| `crud/product_queries.py` | list/filter/search/count |
| `crud/product_mutations.py` | create/update/soft-delete/restore |
| `crud/product_images.py` | image rows |
| `crud/product_stock.py` | stock adjust helpers |

اگر زمان کم است، فقط queries vs mutations کافی است.

### 5.4 Utils دسته — بسته‌بندی

```text
app/utils/category/
  __init__.py          # re-export عمومی
  tree.py              # از category_tree.py
  depth.py
  counts.py
  icons.py
  validation.py
```

یا اگر نمی‌خواهید package بسازید، حداقل یک `category_helpers.py` facade بگذارید که از بیرون یک import داشته باشید.

**معیار Done R2:** هیچ `crud/*.py` بیش از یک دامنه کسب‌وکار نداشته باشد؛ OTP زیر `crud/otp.py`.

---

## 6. فاز R3 — یکنواخت‌سازی لایه‌ها

### 6.1 قانون

Endpoint نباید `from app.crud import ...` داشته باشد (به‌جز موارد بسیار نادر که موقتاً whitelist می‌شوند).

### 6.2 نقشه مهاجرت endpoint → service

| Endpoint فعلی | کار لازم |
|---------------|----------|
| `product.py` (پس از شکستن) | متدهای باقی‌مانده که مستقیم crud می‌زنند → `ProductService` / `ProductImageService` / `ProductReviewService` |
| `order.py` | منطق step-up cancel و mapping response → `order_service` (تا حد ممکن) |
| `payment.py` | نگه داشتن نازک؛ فقط orchestration HTTP |
| `storefront/checkout` | idempotency orchestration می‌تواند در `checkout_service` یا `idempotency_service` بماند |
| `cms.py` | اگر مستقیم crud دارد → `CmsService` نازک |
| `users.py` | `UserAdminService` اگر منطق زیاد شد |

### 6.3 سرویس‌های پیشنهادی جدید (فقط اگر لازم)

| سرویس | دلیل |
|-------|------|
| `product_image_service.py` | جدا از CRUD محصول |
| `product_review_service.py` | comment + verified buyer |
| `cms_service.py` | جمع‌کردن admin CMS |
| `idempotency_service.py` | از قبل هست؛ endpointها فقط همین را صدا بزنند |

### 6.4 Lint پیشنهادی (آخر R3)

در `pyproject.toml` / ruff:

- ممنوعیت import `app.crud` داخل `app/api/endpoints` (با per-file-ignores موقت برای فایل‌های در حال مهاجرت)

**معیار Done R3:** `rg "from app.crud" app/api/endpoints` → صفر (یا فقط shimهای صریح).

---

## 7. فاز R4 — تست‌ها و مستندات

### 7.1 تغییر نام تست‌ها (بدون تغییر محتوا در همان PR)

| فعلی | پیشنهادی |
|------|----------|
| `test_p0_payment.py` | `test_payment_security.py` یا ادغام در `test_payments.py` |
| `test_p1_contract.py` | `test_api_contract_core.py` |
| `test_p2_platform.py` | `test_cart_refresh_audit.py` |
| `test_p3_security.py` | `test_security_throttle.py` |
| `test_p4_data_quality.py` | `test_data_quality.py` |
| `test_p5_*.py` | بر اساس دامنه: `test_product_images.py` (از قبل هست)، `test_category_admin.py`, ... |

در همان PR اول فقط rename + آپدیت CI/docs؛ assertionها دست نخورند.

### 7.2 Docs

| سند | آپدیت |
|-----|--------|
| `docs/ARCHITECTURE.md` | درخت جدید |
| `FRONTEND_IMPLEMENTATION_GUIDE.md` | فقط اگر path فایل مثال عوض شد (معمولاً نه) |
| `GO_LIVE_EXECUTION_PLAN.md` | نیازی نیست مگر اشاره به ساختار |

---

## 8. جدول فایل‌به‌فایل (چک‌لیست اجرایی)

### حذف / جابه‌جایی

| مسیر | اقدام | فاز |
|------|--------|-----|
| `app/admin/` | حذف | R0 |
| `.coverage` | حذف + gitignore | R0 |
| `sample_product.json` | move → `docs/examples/` | R0 |
| `BACKEND_CHANGES.md` | move → `docs/` | R0 |
| `architecture.txt` | move → `docs/ARCHITECTURE.md` | R0 |

### شکستن / ساخت

| مسیر فعلی | اقدام | فاز |
|-----------|--------|-----|
| `api/endpoints/product.py` | split → 4 فایل | R1 |
| `api/endpoints/storefront.py` | split → content + checkout | R1 |
| `api/endpoints/auth.py` | split اختیاری | R1/R3 |
| `crud/platform.py` | split → cart/refresh/audit/idempotency | R2 |
| `crud/content.py` | split → cms_* + otp + contact | R2 |
| `crud/product.py` | split اختیاری queries/mutations | R2 |
| `utils/category_*.py` | package `utils/category/` | R2 |
| `services/product_service.py` | متدهای image/review را جدا کنید | R3 |

### دست‌نخورده بماند (فعلاً)

| مسیر | دلیل |
|------|------|
| `db/models/*` | مرز دامنه نسبتاً خوب است |
| `schemas/*` | ۱:۱ با API؛ نیاز فوری نیست |
| `core/*` | cross-cutting درست است |
| `alembic/versions/*` | هرگز rename نکنید |
| `main.py` | فقط اگر mount router عوض شد |

---

## 9. ترتیب PRهای پیشنهادی (کوچک و قابل‌بازبینی)

1. **PR-R0:** cleanup ریشه + حذف `app/admin`
2. **PR-R1a:** split `product` endpoints (۴ فایل) + router wire-up
3. **PR-R1b:** split `storefront` → checkout جدا
4. **PR-R2a:** `crud/otp.py` از content + shim
5. **PR-R2b:** split `crud/platform.py` + shim
6. **PR-R2c:** حذف shimها بعد از آپدیت importها
7. **PR-R3a:** product endpoints بدون import مستقیم crud
8. **PR-R3b:** بقیه endpointها + lint rule
9. **PR-R4:** rename تست‌ها + ARCHITECTURE.md

هر PR باید در عنوان بنویسد: `refactor(structure): ... (no API change)`.

---

## 10. چیزهایی که عمداً انجام ندهید

- تبدیل به microservices
- جابه‌جایی مدل‌های ORM به packageهای پیچیده بدون نیاز
- تغییر نام URLهای `/api/v1/...`
- ادغام عجولانه payment_service و payment_flow_service (جدا بودنشان خوب است)
- «big bang» یک PR هزارفایلی

---

## 11. تعریف Done نهایی ساختار

ساختار تمیز است وقتی:

1. هیچ endpoint فایلی > ~350 خط نباشد.
2. `crud` ماژول‌ها تک‌دامنه باشند (OTP ≠ CMS).
3. endpointها مستقیم `crud` import نکنند.
4. ریشه repo بدون venv مرده / admin خالی / coverage artifact باشد.
5. `docs/ARCHITECTURE.md` با درخت واقعی هم‌خوان باشد.
6. تست کامل سبز بماند.

---

## 12. تخمینeffort

| فاز | نفر-روز تقریبی |
|-----|----------------|
| R0 | ۰.۵ |
| R1 | ۲–۳ |
| R2 | ۲–۳ |
| R3 | ۲–۴ |
| R4 | ۱ |

جمع: حدود **۱–۱.۵ هفته** برای یک نفر آشنا به codebase، بدون تغییر رفتار.

---

*این سند نقشه است نه دستور اجرای فوری. بعد از تأیید، از PR-R0 شروع کنید.*
