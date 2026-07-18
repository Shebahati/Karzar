# نقشه عملیات بررسی جامع Backend — Karzar

**نسخه:** 1.6 — 2026-07-18  
**وضعیت:** A–E `PASS` (B `PARTIAL`)؛ F `PASS`  
**هدف:** بررسی سیستماتیک کل بک‌اند، المان‌به‌المان و دامنه به‌دامنه، در گام‌های کوچک و قابل‌اجرا  
**قانون اجرا:** در هر نشست فقط **یک شماره گام** (یا حداکثر یک خوشهٔ هم‌خانواده) انجام می‌شود؛ نتیجه با وضعیت Pass / Fail / Partial ثبت می‌شود.

---

## 0. نحوه استفاده از این نقشه

### 0.1 خروجی هر گام
برای هر شماره باید ثبت شود:

| فیلد | معنی |
|------|------|
| وضعیت | `PASS` / `FAIL` / `PARTIAL` / `N/A` |
| شواهد | مسیر فایل، تست، curl، لاگ |
| ریسک | Critical / High / Medium / Low |
| اقدام پیشنهادی | fix فوری / بدهی فنی / نادیده با دلیل |
| اثر روی فرانت | آیا قرارداد API تغییر می‌کند؟ |

### 0.2 ترتیب پیشنهادی اجرا
گام‌ها از **زیربنا → امنیت → دامنه → یکپارچگی → کیفیت → ops** چیده شده‌اند.  
پرش آزاد مجاز است، ولی توصیه می‌شود ترتیب شماره‌ها حفظ شود.

### 0.3 تعریف Done کل عملیات
عملیات وقتی تمام است که:
1. همه گام‌های `A` تا `H` وضعیت داشته باشند.
2. هیچ مورد Critical باز نمانده باشد (یا با پذیرش رسمی محصول بسته شده باشد).
3. یک گزارش نهایی خلاصه در انتهای سند تکمیل شده باشد.

---

## نقشه کلان (۸ فاز اصلی)

| فاز | موضوع | المان اصلی |
|-----|--------|------------|
| **A** | پایه و قرارداد API | قرارداد پایدار با کلاینت |
| **B** | ساختار و لایه‌بندی | لایه‌بندی واضح |
| **C** | هویت و امنیت | Auth / AuthZ / hardening |
| **D** | دامنه کاتالوگ | مدل کسب‌وکار کاتالوگ |
| **E** | دامنه تجارت و سفارش | مدل commerce |
| **F** | پرداخت و یکپارچگی مالی | یکپارچگی داده + integration پرداخت |
| **G** | محتوا، اعلان، یکپارچه‌سازی‌ها | CMS + SMS + سایر |
| **H** | کیفیت، ops، آمادگی اجرا | تست/CI/deploy/backup |

---

# فاز A — قرارداد پایدار با کلاینت

### A1. فهرست رسمی endpointهای `/api/v1`
- خروجی: جدول Method + Path + Auth level
- منبع: OpenAPI یا routerها
- معیار Pass: هیچ route مخفی/مستندنشده حیاتی نمانده باشد

### A2. تطبیق OpenAPI با اسناد فرانت
- مقایسه با `FRONTEND_IMPLEMENTATION_GUIDE.md` و `API_CONTRACT.md`
- معیار Pass: تناقض مسیر/فیلد بحرانی وجود نداشته باشد

### A3. بررسی error envelope سراسری
- شکل `error_code` / `message` / `details`
- نمونه‌گیری از 400/401/403/404/409/422/429/500
- معیار Pass: همه نمونه‌ها envelope استاندارد دارند

### A4. نسخه‌بندی و changelog
- بررسی سیاست `/api/v1` و `API_CHANGELOG.md`
- معیار Pass: تغییرات اخیر ثبت شده‌اند

### A5. سازگاری فیلدهای پول و اعشار
- همه مبالغ string؟ گرد کردن؟ تومان/ریال؟
- معیار Pass: قرارداد با فرانت یکدست است

### A6. pagination و list wrappers
- `{ data, meta }` در لیست‌های اصلی
- استثناها (مثل `/categories/tree`) مستند باشند
- معیار Pass: استثناها شناخته و مستندند

### A7. headerهای قراردادی
- `Authorization`, `X-Step-Up-Token`, `Idempotency-Key`, `X-Cart-Token`
- معیار Pass: رفتار اجباری/اختیاری برای هر کدام روشن است

### A8. گزارش فاز A
- جمع‌بندی تناقض‌های قرارداد و اولویت fix

---

# فاز B — لایه‌بندی و تمیزی ساختار

### B1. نقشه لایه‌ها (endpoints / services / crud / models / schemas / core)
- معیار Pass: هر پوشه نقش واحد دارد

### B2. شناسایی god-fileهای باقی‌مانده
- فایل‌های >350 خط در endpoints/services/crud
- معیار Pass: فهرست بدهی‌ها با اولویت

### B3. نقض لایه‌بندی endpoint → crud مستقیم
- جستجوی `from app.crud` داخل endpoints
- معیار Pass: موارد غیرضروری فهرست و دسته‌بندی شده‌اند

### B4. shimها و سازگاری عقب‌رو
- `crud/platform.py`, re-exportهای OTP در content
- معیار Pass: shimها مستند و موقتی شناخته شده‌اند

### B5. مرز دامنه ماژول‌ها
- OTP جدا از CMS؟ payment adapter جدا از flow؟
- معیار Pass: مرزهای اصلی درست‌اند

### B6. وابستگی‌های دایره‌ای و importهای خطرناک
- معیار Pass: circular import حیاتی نیست

### B7. فایل‌ها/پوشه‌های مرده و artifact
- معیار Pass: ریشه و app بدون زوائد مخرب

### B8. گزارش فاز B
- پیشنهاد refactor بعدی (بدون الزام اجرای فوری)

---

# فاز C — هویت، مجوز، امنیت

### C1. جریان OTP فروشگاه
- request/verify، hash ذخیره، expiry، rate limit
- معیار Pass: OTP end-to-end سالم است

### C2. قرارداد فیلد OTP (`phone` vs `phone_number`)
- بک‌اند و اسناد فرانت
- معیار Pass: قرارداد یکتا و تست‌شده

### C3. JWT access + token_version / logout
- معیار Pass: revoke بعد از logout/password-reset کار می‌کند

### C4. Refresh token rotation
- معیار Pass: reuse توکن قدیمی رد می‌شود

### C5. Login ادمین (OAuth2 form)
- معیار Pass: فقط super_admin به مسیرهای حساس می‌رسد

### C6. Step-up PIN
- صدور، single-use jti، mismatch، missing header
- معیار Pass: عملیات مخرب بدون step-up ممکن نیست

### C7. Authorization ماتریس نقش‌ها
- public / customer / admin برای همه دامنه‌ها
- معیار Pass: ماتریس کامل و بدون حفره آشکار

### C8. Rate limit احراز هویت
- OTP request/verify، PIN، login
- معیار Pass: 429 + Retry-After منطقی

### C9. Throttle عمومی
- contact، checkout، tracking، PLP search
- معیار Pass: محدودیت‌ها فعال و قابل‌پیکربندی‌اند

### C10. CORS و Trusted Hosts / HTTPS flags
- معیار Pass: envهای dev/staging/prod قوانین درست دارند

### C11. SSRF و اعتبارسنجی URL تصویر
- معیار Pass: hostهای private رد می‌شوند

### C12. محدودیت حجم بدنه و security headers
- معیار Pass: middlewareها فعال‌اند

### C13. Secrets و config خطرناک
- SECRET_KEY، PIN ضعیف، OTP_DEV_ECHO در prod، PAYMENT mock در prod
- معیار Pass: validatorهای production کافی‌اند

### C14. گزارش فاز C
- لیست حفره‌های امنیتی با شدت

---

# فاز D — دامنه کاتالوگ

### D1. مدل محصول (فیلدها، soft-delete، is_active)
- معیار Pass: رفتار storefront vs admin روشن است

### D2. PLP: فیلتر، جستجو، sort، pagination
- معیار Pass: سناریوهای اصلی درست‌اند

### D3. Spec filters و JSONB
- `filters` و `spec_*`
- معیار Pass: با template دسته هم‌خوان است

### D4. PDP و related products
- معیار Pass: inactive برای غیر‌ادمین مخفی است

### D5. دسته‌بندی سه‌لایه و is_selectable
- معیار Pass: عمق >3 رد می‌شود

### D6. برندها و slug lookup
- معیار Pass: `/brands/slug/{slug}` و `/categories/slug/{slug}` درست‌اند

### D7. تصاویر محصول (URL + multipart)
- معیار Pass: محدودیت تعداد، primary، reorder سالم است

### D8. موجودی و stock adjust / ledger
- معیار Pass: تغییر stock فقط از مسیر رسمی

### D9. SEO fields محصول/دسته/برند
- معیار Pass: وضعیت expose در API مشخص است (فعلی/بدهی)

### D10. آمار و change-log ادمین
- معیار Pass: فقط admin دسترسی دارد

### D11. گزارش فاز D

---

# فاز E — دامنه تجارت (سبد، checkout، سفارش)

### E1. Cart API دو خطی (purchase / inquiry)
- معیار Pass: laneها جدا و درست‌اند

### E2. Guest cart با `X-Cart-Token`
- معیار Pass: حداقل طول و merge روی login درست است

### E3. Checkout purchase (auth الزامی، shipping الزامی)
- معیار Pass: قوانین کسب‌وکار enforce می‌شوند

### E4. Checkout inquiry / RFQ
- معیار Pass: وضعیت اولیه `inquiry_review` است

### E5. Idempotency روی checkout
- معیار Pass: replay همان پاسخ؛ race → 409 منطقی

### E6. رزرو موجودی در خرید
- معیار Pass: oversell رخ نمی‌دهد

### E7. Order status machine
- انتقال‌های مجاز/غیرمجاز
- معیار Pass: transitionهای غیرقانونی 409 می‌دهند

### E8. Tracking عمومی
- بدون PII؛ timeline موجود
- معیار Pass: با قرارداد فرانت هم‌خوان است

### E9. سفارش‌های من (`/orders/me`)
- معیار Pass: فقط سفارش کاربر جاری

### E10. ادمین: list/detail/status/quote/archive
- معیار Pass: quote استعلام و ship با postal code درست است

### E11. Cancel + step-up + قانون paid-before-refund
- معیار Pass: cancel paid بدون refund ممکن نیست

### E12. Order expiry worker (pending_payment)
- معیار Pass: سفارش رها‌شده لغو و stock برمی‌گردد

### E13. گزارش فاز E

---

# فاز F — پرداخت و یکپارچگی مالی

### F1. Payment init (auth، ownership، pending_payment)
- معیار Pass: guest و سفارش دیگران رد می‌شوند

### F2. Idempotency روی payment init
- معیار Pass: مشابه checkout

### F3. Callback عمومی درگاه
- معیار Pass: redirect success/fail درست است

### F4. Verify (مشتری)
- معیار Pass: فقط owner؛ وضعیت paid پایدار است

### F5. Amount conversion تومان→ریال و rounding
- معیار Pass: با ثابت‌ها و تست‌ها هم‌خوان است

### F6. Payment ledger
- معیار Pass: init/verify/fail/refund ثبت می‌شود

### F7. Refund ادمین + step-up
- معیار Pass: فقط paid؛ بعد از موفقیت cancelled/refunded

### F8. Provider abstraction (mock vs zarinpal)
- معیار Pass: تعویض provider بدون تغییر endpoint

### F9. Timeout / gateway error codes
- معیار Pass: error_codeهای پرداخت مستند و handle‌شدنی‌اند

### F10. Race و double-pay / double-verify
- معیار Pass: وضعیت نهایی یکتا است

### F11. گزارش فاز F

---

# فاز G — محتوا، اعلان، یکپارچه‌سازی‌ها

### G1. Blog/articles عمومی
- معیار Pass: فقط published برمی‌گردد

### G2. Hero slides
- معیار Pass: فقط active + ترتیب درست

### G3. Contact form + throttle + ticket
- معیار Pass: ticket یکتا صادر می‌شود

### G4. Product comments (read/create + verified buyer)
- معیار Pass: inactive product بسته است؛ auth برای create لازم است

### G5. CMS admin (`/cms/*`)
- معیار Pass: CRUD محافظت‌شده و کامل نسبت به نیاز فرانت ادمین

### G6. SMS provider (console/kavenegar)
- معیار Pass: interface درست؛ secrets فقط در env

### G7. Notification روی تغییر وضعیت سفارش
- معیار Pass: رفتار فعلی مشخص و شکست‌پذیر نرم است (fail نباید سفارش را بشکند)

### G8. Uploads / static files
- معیار Pass: مسیر عمومی و دسترسی‌ها امن‌اند

### G9. گزارش فاز G

---

# فاز H — کیفیت، تست، CI، عملیات

### H1. پوشش تست دامنه‌ها
- ماتریس: auth/catalog/commerce/payment/cms/security
- معیار Pass: هیچ دامنه Critical بدون تست نمانده

### H2. Contract tests
- `test_p1_contract` / `test_p5_contract` و هم‌خانواده‌ها
- معیار Pass: سبز و مرتبط با اسناد

### H3. CI pipeline
- ruff، mypy، pytest، alembic upgrade
- معیار Pass: gateها کافی‌اند

### H4. Migration chain و upgrade/downgrade ایمن
- معیار Pass: head مشخص؛ migration خطرناک مستند است

### H5. Health / ready / metrics
- معیار Pass: probes برای deploy کافی‌اند

### H6. Logging و request-id
- معیار Pass: قابلیت تریس درخواست وجود دارد

### H7. Backup/restore scripts و runbook
- معیار Pass: مسیر بازیابی مستند و قابل‌اجراست

### H8. Env templates (dev/staging/prod)
- معیار Pass: تفاوت‌ها درست و امن‌اند

### H9. Docker/runtime
- Python version، entrypoint، compose profiles
- معیار Pass: مسیر deploy محلی/staging روشن است

### H10. Performance smoke (PLP/checkout مسیرهای داغ)
- معیار Pass: گلوگاه آشکار شناخته شده

### H11. وابستگی‌های امنیتی پکیج‌ها (سطح سبک)
- معیار Pass: نسخه بحرانی شناخته‌شده باز نیست (یا پذیرفته شده)

### H12. گزارش فاز H + آمادگی اجرا
- لینک به `GO_LIVE_EXECUTION_PLAN.md`

---

# فاز I — جمع‌بندی نهایی عملیات (اجباری در پایان)

### I1. تجمیع همه FAIL/PARTIAL Critical/High
### I2. اولویت‌بندی backlog fix (P0/P1/P2)
### I3. تفکیک: باگ / بدهی فنی / کار محصول / کار ops
### I4. به‌روزرسانی اسناد متأثر (در صورت نیاز)
### I5. صدور حکم نهایی آمادگی بک‌اند
- مثلاً: «مناسب demo»، «مناسب staging»، «مناسب production با شرط X»

---

## ترتیب اجرای پیشنهادی نشست‌به‌نشست (خلاصه عملی)

| نشست | گام‌ها | تمرکز |
|------|--------|--------|
| 1 | A1–A4 | قرارداد پایه |
| 2 | A5–A8 | جزئیات قرارداد |
| 3 | B1–B4 | ساختار |
| 4 | B5–B8 | بدهی ساختار |
| 5 | C1–C4 | OTP/JWT |
| 6 | C5–C8 | Admin/step-up/limits |
| 7 | C9–C14 | hardening |
| 8 | D1–D5 | کاتالوگ پایه |
| 9 | D6–D11 | کاتالوگ پیشرفته |
| 10 | E1–E6 | cart/checkout |
| 11 | E7–E13 | orders |
| 12 | F1–F5 | payment happy path |
| 13 | F6–F11 | ledger/refund/races |
| 14 | G1–G5 | content/CMS |
| 15 | G6–G9 | SMS/notify/uploads |
| 16 | H1–H6 | کیفیت و observability |
| 17 | H7–H12 | ops readiness |
| 18 | I1–I5 | حکم نهایی |

هر نشست ≈ یک واحد کار قابل‌بستن در یک گفتگو.

---

## قالب ثبت نتیجه (کپی برای هر گام)

```text
گام: A3
وضعیت: PARTIAL
ریسک: Medium
شواهد:
- ...
یافته‌ها:
- ...
اقدام پیشنهادی:
- ...
اثر قرارداد فرانت: هیچ / دارد (توضیح)
```

---

## ضمیمه — نگاشت المان‌های بک‌اند مناسب به فازها

| المان مهم بک‌اند | فازهای پوشش |
|------------------|-------------|
| قرارداد پایدار با کلاینت | A |
| لایه‌بندی واضح | B |
| هویت / مجوز / امنیت | C |
| مدل دامنه کاتالوگ | D |
| مدل دامنه تجارت | E |
| یکپارچگی داده + پرداخت | F (+ بخش‌هایی از E) |
| یکپارچه‌سازی بیرونی | F, G |
| محتوا و اعلان | G |
| کیفیت، تست، CI | H1–H3 |
| عملیات و آمادگی اجرا | H4–H12, I |

---

*این سند فقط نقشه است. برای شروع اجرا، بگویید: «برو گام A1» یا «نشست 1 را اجرا کن».*

---

# نتایج اجرا — فاز A (2026-07-18)

**وضعیت فاز (پس از remediation):** `PASS` با note باقی‌مانده فقط فرانت (`phone_number`) و PDF کهنه.  
**Critical باز در بک‌اند (فاز A):** هیچ

### Remediation اجراشده (همان نشست، قبل از فاز B)
| مورد A8 | وضعیت |
|---------|--------|
| اصلاح tree در INTEGRATION + HANDOVER | Done |
| `openapi/v1.json` | Done (`openapi/v1.json`) |
| OpenAPI optional auth (`{}` + HTTPBearer) | Done (`app/api/deps.py`, `app/main.py::custom_openapi`) |
| `decimal_to_api_string` در cart | Done |
| جدول list shapes در API_CONTRACT | Done |
| تست قرارداد optional OpenAPI | Done (`test_optional_auth_openapi_allows_anonymous`) |
| PDF `FRONTEND_INTEGRATION.pdf` | **باقی** — موتور pdflatex/weasyprint در محیط نیست؛ MD منبع حقیقت است |

### A1 — فهرست رسمی endpointها — `PASS` (پس از snapshot)
- شواهد: ۸۷ operation + `openapi/v1.json` committed path.

### A2 — تطبیق با اسناد فرانت — `PASS` (بک‌اند/docs) / FE gap جدا
- tree docs اصلاح شد. OTP `phone_number` همچنان بدهی فرانت است.

### A3 — error envelope — `PASS`
### A4 — نسخه‌بندی و changelog — `PASS` (changelog به‌روز شد)
### A5 — پول و اعشار — `PASS` (cart یکدست شد)
### A6 — pagination / list wrappers — `PASS` (استثناها در API_CONTRACT رسمی شد)
### A7 — headerهای قراردادی — `PASS` (OpenAPI anonymous-capable)
### A8 — جمع‌بندی — remediation کامل به‌جز PDF و FE OTP

---

# نتایج اجرا — فاز B (2026-07-18)

**وضعیت فاز:** `PARTIAL` — اسکلت لایه‌ها درست است؛ بدهی R3 (endpoint→crud) و چند god-file باقی است.  
**Critical:** هیچ  
**ریسک غالب:** Medium (لایه‌بندی)

### B1 — نقشه لایه‌ها — `PASS` (Low)
- شواهد: `app/{api,services,crud,db,schemas,core,utils}` مطابق `ARCHITECTURE.md`.
- جریان هدف: endpoints → services → crud → models.
- معیار: هر پوشه نقش واحد دارد — برقرار است.

### B2 — god-fileها (>350 خط) — `PARTIAL` (Medium)
| خطوط | فایل | اولویت refactor |
|------|------|-----------------|
| 535 | `app/crud/product.py` | High |
| 441 | `app/services/category_service.py` | Medium |
| 398 | `app/api/endpoints/auth.py` | Medium |
| 395 | `app/api/endpoints/payment.py` | Medium |
| 391 | `app/api/endpoints/order.py` | Medium |

### B3 — نقض endpoint → crud — `PARTIAL` (Medium)
- **۱۳ فایل endpoint** هنوز `from app.crud` دارند (حتی وقتی service هم دارند).
- فقط `products_images.py` **بدون service** و مستقیماً CRUD+utils — اولویت استخراج `product_image_service`.
- سنگین‌ترین تماس‌های مستقیم: `cms.py` (~16)، `payment.py`/`order.py`/`checkout.py` (عمدتاً idempotency via platform shim).
- `category.py` و `cart.py` تمیزترند (عمدتاً service-only).
- اقدام پیشنهادی: ادامه R3 طبق `BACKEND_STRUCTURE_REFACTOR_MAP.md` — بدون تغییر URL.

### B4 — shimها — `PASS` (مستند، موقتی) (Low)
- `crud/platform.py`: re-export cart/refresh/audit/idempotency — هنوز مصرف گسترده دارد.
- `crud/content.py`: re-export OTP از `crud/otp.py`.
- `utils/category/__init__.py`: facade روی `category_*.py`های تخت — دوگانگی مسیر import.
- اقدام: deprecate تدریجی import از `platform`/`content` OTP؛ مهاجرت به ماژول‌های split.

### B5 — مرز دامنه — `PARTIAL` (Medium)
- مثبت: payment adapter جدا (`payment_service`) از flow (`payment_flow_service`)؛ checkout/cart/order سرویس دارند.
- منفی: مدل `OtpCode` هنوز در `db/models/content.py` (مرز CMS/auth مخلوط).
- منفی: `crud/product.py` از `app.schemas.product` برای Create/Update استفاده می‌کند (نشت schema به لایه persistence).
- اقدام: در refactor بعدی OTP model → auth/platform؛ DTO داخلی برای product write.

### B6 — circular imports — `PASS` (Low)
- شواهد: import smoke برای main/v1/deps/services/crud کلیدی OK.
- services→endpoints و crud→services خالی است.

### B7 — فایل/artifact مرده — `PASS` با hygiene notes (Low)
- `app/admin` حذف شده (خوب).
- سه venv محلی: `.venv`, `.venv312`, `venv` — فقط hygiene.
- `docs/FRONTEND_INTEGRATION.pdf` نسبت به MD کهنه است (Jun 23).
- `openapi/` اکنون artifact رسمی مفید است.

### B8 — جمع‌بندی فاز B / backlog ساختار
| اولویت | مورد | نوع |
|--------|------|-----|
| P1 | استخراج service برای `products_images` | بدهی لایه‌بندی |
| P1 | کاهش idempotency/crud مستقیم در checkout/payment/order | R3 |
| P2 | شکستن `crud/product.py` (>500 خط) | god-file |
| P2 | انتقال OTP model از content | مرز دامنه |
| P2 | حذف وابستگی crud→schemas در product | لایه‌بندی |
| P3 | حذف تدریجی shim `platform.py` / OTP از content | compat |
| P3 | یک venv رسمی؛ regenerate PDF وقتی موتور موجود شد | hygiene |

**حکم B:** معماری هدف درست است و refactor قبلی (R0–R2) اثر کرده؛ فاز C امنیتی می‌تواند شروع شود، ولی بدهی R3 را به‌عنوان کار موازی نگه دارید — نه blocker امنیت.

---

# نتایج اجرا — فاز C (2026-07-18)

**وضعیت فاز:** `PASS` با note باقی‌ماندهٔ Low/Medium روی SSRF مبتنی بر DNS.  
**Critical باز:** هیچ (یک bypass config production در همین نشست بسته شد).

### C1 — OTP فروشگاه — `PASS`
- شواهد: `otp_service` + `crud/otp` با `hash_otp_code`؛ expiry از `OTP_EXPIRE_SECONDS`؛ rate limit روی request/verify؛ تست‌های e2e + fail-closed وقتی Redis unreachable.

### C2 — قرارداد فیلد OTP — `PASS` (بک‌اند)
- شواهد: schema `phone`؛ تست قرارداد؛ بدهی فرانت `phone_number` خارج از بک‌اند.

### C3 — JWT / token_version / logout — `PASS`
- شواهد: `logout_user` افزایش `token_version` + revoke refresh؛ `test_logout_invalidates_existing_access_token`.

### C4 — Refresh rotation — `PASS`
- شواهد: rotation در `auth_token_service`؛ تست جدید `test_refresh_token_reuse_rejected` → 401.

### C5 — Login ادمین — `PASS`
- شواهد: OAuth2 form login؛ مسیرهای حساس با `get_current_super_admin`.

### C6 — Step-up PIN — `PASS`
- شواهد: single-use jti؛ rate limit PIN؛ تست جدید `test_step_up_token_single_use`.

### C7 — ماتریس نقش‌ها — `PASS`
- شواهد: `test_customer_cannot_access_admin_surfaces` (products/orders/cms/verify-pin → 403).

### C8 — Rate limit احراز — `PASS`
- شواهد: login/OTP/PIN با `RATE_LIMITED` + `Retry-After`؛ تست PIN rate در product endpoints.

### C9 — Throttle عمومی — `PASS`
- شواهد: contact/tracking/PLP/checkout؛ `test_p3_security` سبز.

### C10 — CORS / Trusted Hosts / HTTPS — `PASS` (پس از harden)
- قبل: `APP_ENV=production` + `DEBUG=True` محافظت‌ها را دور می‌زد؛ `TRUSTED_HOSTS` اجباری نبود.
- بعد: production نیازمند `DEBUG=False`, `TRUSTED_HOSTS`, `ENFORCE_HTTPS=True`.

### C11 — SSRF تصویر — `PASS` با note (Medium/Low)
- شواهد: block localhost/private/metadata؛ تست‌های SSRF سبز.
- باقی: بدون DNS resolve — hostname عمومی که به IP خصوصی resolve شود theoretically باز است (rebinding). اقدام بعدی اختیاری: resolve + re-check.

### C12 — Body size / headers — `PASS`
- شواهد: `RequestBodySizeLimitMiddleware`؛ headers در `request_context_middleware`؛ تست 413.

### C13 — Secrets / config خطرناک — `PASS` (پس از harden)
- شواهد: SECRET_KEY طول/placeholder؛ weak PIN؛ OTP echo؛ mock payment؛ SMS console؛ docs در production رد می‌شوند.
- تست‌های جدید production guards سبز.

### C14 — جمع‌بندی فاز C
| اولویت | مورد | وضعیت |
|--------|------|--------|
| P0 | Bypass `DEBUG=True` در production | **Fixed** |
| P0 | اجباری کردن TRUSTED_HOSTS / HTTPS / SMS واقعی در production | **Fixed** |
| P1 | تست refresh reuse + step-up single-use + customer authz | **Added** |
| P2 | SSRF DNS rebinding harden | باز (اختیاری) |
| خارج | OTP `phone` در فرانت | فرانت |

**حکم C:** بک‌اند از نظر هویت/مجوز/سخت‌سازی برای ادامهٔ فازهای دامنه آماده است؛ قبل از go-live واقعی env production را با چک‌لیست C13 تنظیم کنید.

---

# نتایج اجرا — فاز D (2026-07-18)

**وضعیت فاز:** `PASS` با بدهی شناخته‌شدهٔ SEO (فیلدها در DB هستند، در API محصول/دسته/برند کامل expose نشده‌اند).  
**Critical:** هیچ  
**شواهد تست:** ۸۳ تست کاتالوگ قبلی سبز + `tests/test_d_catalog_audit.py` (۵ تست جدید) سبز.

### D1 — مدل محصول — `PASS`
- soft-delete (`deleted_at`)، `is_active`، SKU unique روی active؛ storefront فقط active؛ admin می‌تواند inactive/`is_deleted` ببیند.

### D2 — PLP — `PASS`
- فیلتر/جستجو/sort/pagination؛ `in_stock`؛ رد sort نامعتبر؛ تست‌های storefront + product endpoints.

### D3 — Spec filters — `PASS`
- `filters` / `spec_*`؛ labels، filter-options، templates؛ template فقط برای leaf قابل‌انتخاب.

### D4 — PDP / related — `PASS`
- inactive برای غیر‌ادمین → 404؛ related فقط `is_active` و هم‌درخت؛ تست جدید PDP inactive.

### D5 — دسته سه‌لایه — `PASS`
- عمق >3 رد؛ `is_selectable` فقط depth-3 leaf؛ unit + admin tests.

### D6 — slug lookup — `PASS`
- `/categories/slug/{slug}` و `/brands/slug/{slug}`؛ تست جدید.

### D7 — تصاویر — `PASS`
- URL + multipart؛ سقف تعداد؛ primary/reorder؛ SSRF روی URL؛ `test_p5_product_images`.

### D8 — موجودی — `PASS`
- PUT مستقیم `stock_quantity` → 400؛ مسیر رسمی `stock/adjust` + ledger/change-log.

### D9 — SEO fields — `PARTIAL` (بدهی محصول، نه باگ امنیتی)
- DB: `products.slug/meta_*`، `categories.meta_*`، `brands.meta_*`.
- API: category/brand **slug** در پاسخ هست؛ **meta_*** هیچ‌کجا expose نشده؛ **product.slug** در PLP/PDP نیست.
- اقدام: وقتی فرانت SEO بخواهد، فیلدها را غیرشکست‌زا به response اضافه کنید (`API_CHANGELOG`).

### D10 — آمار / change-log — `PASS`
- فقط admin؛ تست با clear کردن dependency override fixture.

### D11 — جمع‌بندی فاز D
| اولویت | مورد | وضعیت |
|--------|------|--------|
| — | رفتار کاتالوگ runtime | سالم |
| P2 | expose `product.slug` + `meta_*` برای SEO | بدهی محصول |
| P2 | expose `meta_*` روی category/brand | بدهی محصول |

**حکم D:** دامنه کاتالوگ برای commerce (فاز E) آماده است؛ SEO URL مبتنی بر product slug هنوز نیاز به کار API+FE دارد.

---

# نتایج اجرا — فاز E (2026-07-18)

**وضعیت فاز:** `PASS`  
**Critical:** هیچ  
**شواهد:** ۴۹ تست commerce قبلی سبز + `tests/test_e_commerce_audit.py` (۶ تست جدید) سبز.

### E1 — Cart دو خطی — `PASS`
- laneهای `purchase` / `inquiry` جدا؛ تست isolation.

### E2 — Guest cart / merge — `PASS`
- `X-Cart-Token` ≥32؛ توکن کوتاه → 422؛ merge روی login.

### E3 — Checkout purchase — `PASS`
- auth الزامی (`PURCHASE_AUTH_REQUIRED`)؛ shipping الزامی → 400؛ تست‌های موجود + جدید.

### E4 — Inquiry / RFQ — `PASS`
- وضعیت اولیه `inquiry_review`؛ بدون نیاز به stock.

### E5 — Idempotency checkout — `PASS`
- `test_checkout_idempotency` replay همان `order_id`.

### E6 — رزرو موجودی — `PASS`
- oversell / duplicate lines / insufficient stock رد می‌شوند؛ lock در checkout.

### E7 — Status machine — `PASS`
- انتقال غیرمجاز → 409؛ مسیر paid→processing معتبر.

### E8 — Tracking عمومی — `PASS`
- بدون PII؛ timeline موجود.

### E9 — `/orders/me` — `PASS`
- auth الزامی؛ فقط سفارش‌های خود کاربر.

### E10 — ادمین orders — `PASS`
- list/detail/quote/archive؛ ship نیازمند postal tracking.

### E11 — Cancel + paid-before-refund — `PASS`
- cancel نیازمند step-up؛ cancel روی `paid` بدون refund → 409؛ refund خودش به cancelled می‌برد.

### E12 — Expiry worker — `PASS`
- `pending_payment` منقضی → cancel + restock.

### E13 — جمع‌بندی فاز E
| اولویت | مورد | وضعیت |
|--------|------|--------|
| — | جریان تجارت runtime | سالم |
| خارج | فرانت Idempotency-Key / cart سرور | بدهی FE |

**حکم E:** دامنه commerce برای فاز پرداخت (F) آماده است.

---

# نتایج اجرا — فاز F (2026-07-18)

**وضعیت فاز:** `PASS`  
**Critical:** هیچ  
**شواهد:** ۱۷ تست پرداخت قبلی + `tests/test_f_payment_audit.py` (۴ تست جدید) سبز.

### F1 — Payment init — `PASS`
- auth الزامی؛ ownership فقط owner؛ guest order → `GUEST_ORDER_NOT_PAYABLE` در مسیرهای مرتبط؛ فقط `pending_payment`.

### F2 — Idempotency init — `PASS`
- replay همان authority؛ Idempotency-Key روی endpoint پشتیبانی می‌شود.

### F3 — Callback — `PASS`
- OK → success redirect؛ NOK → failure redirect.

### F4 — Verify — `PASS`
- فقط owner (+ auth)؛ وضعیت paid پایدار؛ anonymous → 401.

### F5 — تومان→ریال — `PASS`
- `TOMAN_TO_RIAL=10`؛ `ROUND_HALF_UP` (۱۰.۱۵×۱۰ → ۱۰۲).

### F6 — Ledger — `PASS`
- initiated / verified / failed / refunded در `payment_transactions`.

### F7 — Refund — `PASS`
- فقط admin + step-up؛ فقط paid؛ پس از موفقیت `refunded` + `cancelled`.

### F8 — Provider abstraction — `PASS`
- mock/zarinpal پشت interface یکسان؛ تست‌های zarinpal unit سبز.

### F9 — Gateway errors — `PASS`
- `PAYMENT_GATEWAY_TIMEOUT` (504)، `PAYMENT_VERIFY_FAILED` (400).

### F10 — Double verify / race — `PASS`
- verify تکراری idempotent؛ init تکراری همان authority؛ order lock در init.

### F11 — جمع‌بندی فاز F
| اولویت | مورد | وضعیت |
|--------|------|--------|
| — | جریان پرداخت mock | سالم |
| خارج | Zarinpal واقعی در production | ops/go-live |
| خارج | Idempotency-Key سمت فرانت | بدهی FE |

**حکم F:** لایه پرداخت برای ادامهٔ فاز محتوا/یکپارچه‌سازی (G) آماده است؛ قبل از go-live واقعی provider و callback URL را در env ست کنید.
