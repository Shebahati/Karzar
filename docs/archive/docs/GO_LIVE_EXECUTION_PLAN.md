# برنامه اجرایی راه‌اندازی Karzar — بک‌اند، فرانت، داده، و عملیات

**نسخه:** 1.0 — 2026-07-14  
**وضعیت پروژه:** Backend `main` @ `af3b0e6` (P8 + docs)  
**مخاطب:** تیم فنی، محصول، و عملیات  
**هدف:** فهرست کامل و اولویت‌بندی‌شدهٔ **همه اقدامات لازم** تا وبسایت از حالت توسعه به **اجرای واقعی** (staging → production) برسد.

**اسناد مرتبط:**
- [FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md) — قرارداد API و شکاف‌های فرانت
- [OPERATIONS.md](OPERATIONS.md) — runbook عملیاتی
- [SEED_IMPORT.md](SEED_IMPORT.md) — pipeline داده کاتالوگ
- [LOCAL_DEV_FRONTEND.md](LOCAL_DEV_FRONTEND.md) — راه‌اندازی محلی

---

## 1. تعریف «اجرایی شدن»

| سطح | معیار پذیرش | مخاطب |
|-----|-------------|--------|
| **L0 — Dev** | `localhost` با mock یا API واقعی | توسعه‌دهنده |
| **L1 — Demo داخلی** | خرید end-to-end با `PAYMENT_PROVIDER=mock`، ادمین عملیاتی، `USE_MOCK=false` | تیم داخلی |
| **L2 — Staging** | دامنه HTTPS، داده واقعی جزئی، Zarinpal sandbox، SMS تست | QA + ذینفع |
| **L3 — Production** | فروش واقعی، پرداخت/SMS زنده، پشتیبان‌گیری، مانیتورینگ، SLA | مشتری نهایی |

**وضعیت فعلی:** بین L0 و L1 — بک‌اند آماده‌تر از فرانت و ops.

---

## 2. نمای کلی — چهار محور کار

```
┌─────────────────────────────────────────────────────────────────┐
│                        GO-LIVE PROGRAM                          │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│   FRONTEND   │   BACKEND    │     DATA     │       OPS          │
│ Storefront   │ API hardening│ Catalog seed │ Docker/SSL/Deploy  │
│ Admin Panel  │ Integrations │ Images/SEO   │ Backup/Monitor     │
└──────────────┴──────────────┴──────────────┴────────────────────┘
                              │
                    QA + E2E + Security
```

---

## 3. ماتریس آمادگی (وضعیت فعلی)

| حوزه | % | وضعیت | مانع اصلی |
|------|---|--------|-----------|
| Backend API | 88 | آماده staging | product slug در API، گزارش aggregate |
| Storefront UI | 75 | صفحات ساخته | اتصال live ناقص |
| Storefront ↔ API | 55 | نیمه‌کاره | باگ OTP (`phone` vs `phone_number`) |
| Admin UI | 80 | عملیاتی | CMS UI ندارد |
| Admin ↔ API | 65 | اکثراً وصل | reports client-side |
| Catalog/Data | 25 | seed dev فقط | import انبوه نشده |
| DevOps | 40 | compose موجود | image قدیمی، deploy نشده |
| Integrations | 15 | mock/console | Zarinpal + Kavenegar واقعی |

---

## 4. فازبندی اجرایی (Timeline پیشنهادی)

| فاز | مدت | خروجی | Gate (شرط عبور) |
|-----|-----|--------|------------------|
| **F0** آماده‌سازی | ۲–۳ روز | env یکپارچه، smoke script | هر سه سرویس بالا |
| **F1** اتصال زنده | ۱ هفته | mock=false پایدار | E2E خرید + ادمین |
| **F2** داده و محتوا | ۱–۲ هفته | کاتالوگ واقعی + CMS | PLP > 100 محصول |
| **F3** Staging | ۱ هفته | HTTPS + sandbox پرداخت | QA sign-off |
| **F4** Production | ۱–۲ هفته | launch + مانیتورینگ | 48h بدون SEV1 |

**جمع تقریبی تا Production:** ۵–۸ هفته کاری (با تیم ۲–۳ نفره).

---

## 5. فاز F0 — آماده‌سازی محیط (۲–۳ روز)

### 5.1 Backend

| # | اقدام | مسئول | Done وقتی |
|---|--------|--------|-----------|
| B0.1 | `alembic upgrade head` روی DB هدف | Backend | بدون خطا |
| B0.2 | `.env` کامل: `SECRET_KEY`, `POSTGRES_*`, `ADMIN_STEP_UP_PIN`, `CORS_ORIGINS` | Backend | `/ready` → 200 |
| B0.3 | `DEBUG=true`, `OTP_DEV_ECHO=true`, `PAYMENT_PROVIDER=mock` (dev) | Backend | OTP در لاگ |
| B0.4 | `PAYMENT_CALLBACK_URL` = URL فرانت `/checkout/payment/callback` | Backend | redirect درست |
| B0.5 | rebuild Docker: `docker compose build --no-cache app` (Python 3.12) | Ops | container healthy |
| B0.6 | bootstrap super admin (`INITIAL_SUPER_ADMIN_*`) | Backend | login ادمین OK |

### 5.2 Storefront (`:3000`)

| # | اقدام | مسئول | Done وقتی |
|---|--------|--------|-----------|
| F0.1 | `NEXT_PUBLIC_USE_MOCK=false` | Frontend | همه سرویس‌ها live |
| F0.2 | `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` | Frontend | PLP داده واقعی |
| F0.3 | `npm install && npm run build` بدون خطا | Frontend | build سبز |
| F0.4 | تست دستی صفحه اصلی، catalog، PDP | QA | 200 + داده |

### 5.3 Admin Panel (`:3001`)

| # | اقدام | مسئول | Done وقتی |
|---|--------|--------|-----------|
| A0.1 | همان envهای F0.1–F0.2 با پورت 3001 | Frontend | login ادمین |
| A0.2 | `npm install && npm run build` | Frontend | build سبز |
| A0.3 | CORS شامل `http://localhost:3001` | Backend | بدون CORS error |

### 5.4 Gate F0

```bash
curl -sf http://localhost:8000/ready
curl -sf http://localhost:3000/ -o /dev/null -w '%{http_code}'
curl -sf http://localhost:3001/ -o /dev/null -w '%{http_code}'
```

---

## 6. فاز F1 — اتصال زنده و رفع شکاف‌های بحرانی (۱ هفته)

### 6.1 Frontend — Storefront (P0)

| # | اقدام | فایل/محل | اولویت |
|---|--------|----------|--------|
| F1.1 | **اصلاح OTP:** ارسال `{ phone }` نه `phone_number` | `Storefront/src/services/auth.ts` | P0 |
| F1.2 | استفاده از `timeline` سرور در tracking | `Storefront/src/services/orders.ts` | P1 |
| F1.3 | افزودن `Idempotency-Key` (UUID) به checkout | `Storefront/src/services/checkout.ts` | P1 |
| F1.4 | افزودن `Idempotency-Key` به payment init | `Storefront/src/services/payments.ts` | P1 |
| F1.5 | مدیریت `GUEST_ORDER_NOT_PAYABLE` در checkout | `checkout-view.tsx` | P0 |
| F1.6 | به‌روز types: `slug` در Category/Brand | `types/category.ts` | P2 |
| F1.7 | (اختیاری) `cartService` + `X-Cart-Token` + merge on login | سرویس جدید | P2 |
| F1.8 | (اختیاری) refresh token + `/auth/refresh` | `auth.ts`, `api-client.ts` | P2 |
| F1.9 | فرم ثبت نظر محصول (POST comments) | `product-comments.tsx` | P3 |

### 6.2 Frontend — Admin (P0–P1)

| # | اقدام | فایل/محل | اولویت |
|---|--------|----------|--------|
| A1.1 | تست کامل quote استعلام → `POST /orders/{id}/quote` | orders workflow | P0 |
| A1.2 | لغو سفارش paid فقط پس از refund (پیام خطا) | order action panel | P1 |
| A1.3 | step-up برای cancel: PIN تازه برای هر عمل | auth flow | P1 |
| A1.4 | صفحه deleted products با `is_deleted=true` | موجود — تست live | P1 |
| A1.5 | CMS UI: blog, hero, comments, contact | **جدید** — `/cms/*` | P2 |
| A1.6 | حذف یا پنهان `/documents` (mock) | nav.config | P3 |

### 6.3 Backend — تکمیل‌های لازم برای parity

| # | اقدام | توضیح | اولویت |
|---|--------|--------|--------|
| B1.1 | افزودن `slug` به `ProductSummary`/`ProductDetail` | SEO PDP | P2 |
| B1.2 | `GET /products/slug/{slug}` | route جدید | P2 |
| B1.3 | `postal_tracking_code` + `delivery_eta` در public tracking (بدون PII) | قرارداد فرانت | P2 |
| B1.4 | `product_name`/`sku` در `OrderItemResponse` (اختیاری) | کاهش N+1 ادمین | P3 |
| B1.5 | endpoint گزارش aggregate (`/admin/reports/summary`) | جایگزین client-side | P3 |
| B1.6 | PDF پیش‌فاکتور | invoice download | P4 |

### 6.4 QA — Smoke E2E (الزام قبل از F2)

| سناریو | مراحل | نتیجه مورد انتظار |
|--------|--------|-------------------|
| خرید آنلاین | OTP → PLP → cart → checkout → payment mock → success | status=paid |
| استعلام | quote cart → checkout inquiry → admin quote | inquiry_quoted |
| پیگیری | `GET /orders/track/{code}` | timeline از سرور |
| ادمین | login → ویرایش محصول → تغییر وضعیت سفارش → ship | tracking code |
| refund | refund step-up → cancelled | payment_status=refunded |
| امنیت | cancel paid بدون refund | 409 |

### 6.5 Gate F1

- [ ] `NEXT_PUBLIC_USE_MOCK=false` روی storefront و admin
- [ ] ۶ سناریوی smoke بالا سبز
- [ ] `pytest` بک‌اند: 160+ pass
- [ ] بدون خطای CORS/401 در جریان اصلی

---

## 7. فاز F2 — داده، محتوا، و SEO (۱–۲ هفته)

### 7.1 Pipeline کاتالوگ

ترتیب اجرا (جزئیات: [SEED_IMPORT.md](SEED_IMPORT.md)):

```text
backup_db.sh
  → seed_categories.py
  → seed_brands.py
  → seed_products_from_csv.py  (یا parse_price_list_pdfs.py)
  → import_insize_images_from_tosag.py
  → seed_storefront.py
```

| # | اقدام | مسئول | Done وقتی |
|---|--------|--------|-----------|
| D2.1 | backup قبل از import | Ops | فایل در `backups/` |
| D2.2 | دسته‌بندی ۳ لایه + spec templates | Data | tree در mega-menu |
| D2.3 | برندها با slug | Data | `/brands/` پر |
| D2.4 | import محصولات CSV (SKU یکتا، category_id معتبر) | Data | PLP > 100 |
| D2.5 | تصاویر HTTPS (بدون localhost/private IP) | Data | thumbnail پر |
| D2.6 | قیمت و موجودی واقعی | Data | checkout بدون خطای stock |
| D2.7 | بلاگ + hero slides | Content | صفحه اصلی زنده |
| D2.8 | smoke PLP filter + spec filter + PDP | QA | فیلترها کار کنند |

### 7.2 SEO و URL

| # | اقدام | وضعیت |
|---|--------|--------|
| S2.1 | slug دسته/برند در API | ✅ موجود |
| S2.2 | slug محصول در API | ❌ — F2 backend |
| S2.3 | مسیر `/catalog?category_id=` | ✅ |
| S2.4 | مسیر `/product/[slug]` در فرانت | بعد از B1.1 |
| S2.5 | meta title/description محصول | فیلد DB موجود — expose در API |
| S2.6 | sitemap.xml + robots.txt | فرانت Next.js |

### 7.3 Gate F2

- [ ] حداقل ۱۰۰ محصول فعال با تصویر
- [ ] ۰ خطای import بحرانی (duplicate SKU)
- [ ] checkout با محصول واقعی (نه فقط DEV-CHECKOUT-001)

---

## 8. فاز F3 — Staging (۱ هفته)

### 8.1 زیرساخت Staging

| # | اقدام | مرجع |
|---|--------|------|
| O3.1 | سرور/VPS یا cloud (حداقل 2 vCPU, 4GB RAM) | — |
| O3.2 | دامنه: `api.staging.*`, `shop.staging.*`, `admin.staging.*` | DNS |
| O3.3 | TLS (Let's Encrypt یا CDN) | — |
| O3.4 | `docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build` | compose |
| O3.5 | `.env.staging` از `.env.staging.example` | secrets |
| O3.6 | `ENFORCE_HTTPS=true`, `OTP_DEV_ECHO=false`, `ENABLE_API_DOCS=false` | امنیت |
| O3.7 | Redis اجباری (`DEBUG=false`) | config validator |
| O3.8 | `TRUSTED_HOSTS` = hostname API | middleware |

### 8.2 env Staging — نمونه

```env
APP_ENV=staging
CORS_ORIGINS=https://shop.staging.example.com,https://admin.staging.example.com
PAYMENT_PROVIDER=mock
PAYMENT_CALLBACK_URL=https://shop.staging.example.com/checkout/payment/callback
SMS_PROVIDER=console
```

### 8.3 Frontend Staging

| # | اقدام |
|---|--------|
| O3.9 | build production: `next build && next start` |
| O3.10 | `NEXT_PUBLIC_API_BASE_URL=https://api.staging.example.com/api/v1` |
| O3.11 | reverse proxy (nginx/caddy): `/` → 3000, `/admin` → 3001 |
| O3.12 | یا deploy جدا: Vercel/Netlify برای فرانت + API جدا |

### 8.4 QA Staging

| # | تست |
|---|------|
| Q3.1 | regression کامل smoke F1 |
| Q3.2 | موبایل + RTL |
| Q3.3 | rate limit (OTP، checkout) |
| Q3.4 | session expiry / 401 redirect |
| Q3.5 | performance: PLP < 2s, PDP < 1.5s (هدف) |

### 8.5 Gate F3

- [ ] HTTPS end-to-end
- [ ] QA sign-off
- [ ] backup روزانه فعال
- [ ] `/metrics` scrape شده

---

## 9. فاز F4 — Production (۱–۲ هفته)

### 9.1 یکپارچه‌سازی‌های بیرونی (الزام فروش واقعی)

#### پرداخت — Zarinpal

| # | اقدام | env |
|---|--------|-----|
| I4.1 | ثبت merchant در Zarinpal | — |
| I4.2 | `PAYMENT_PROVIDER=zarinpal` | production |
| I4.3 | `ZARINPAL_MERCHANT_ID=...` | secret |
| I4.4 | `PAYMENT_CALLBACK_URL` = URL production فرانت | HTTPS |
| I4.5 | تست sandbox → production با مبلغ کم | manual |
| I4.6 | runbook refund ادمین + step-up | docs |

#### SMS — Kavenegar (OTP)

| # | اقدام | env |
|---|--------|-----|
| I4.7 | `SMS_PROVIDER=kavenegar` | production |
| I4.8 | `SMS_KAVENEGAR_API_KEY`, `SMS_KAVENEGAR_SENDER` | secret |
| I4.9 | (اختیاری) template OTP | `SMS_KAVENEGAR_OTP_TEMPLATE` |
| I4.10 | `OTP_DEV_ECHO=false` | اجباری |
| I4.11 | تست ارسال واقعی به ۳ شماره | QA |

### 9.2 امنیت Production

| # | اقدام | env/کد |
|---|--------|--------|
| SEC4.1 | `SECRET_KEY` تصادفی ۳۲+ کاراکتر — هر env جدا | vault |
| SEC4.2 | `ADMIN_STEP_UP_PIN` قوی — rotate دوره‌ای | vault |
| SEC4.3 | `ALLOW_PUBLIC_REGISTER=false` (یا محدود) | .env |
| SEC4.4 | `CORS_ORIGINS` فقط دامنه‌های production | .env |
| SEC4.5 | `TRUSTED_HOSTS` + `ENFORCE_HTTPS=true` | .env |
| SEC4.6 | secrets در repo نباشند | gitignore |
| SEC4.7 | rate limit با Redis (نه in-memory) | Redis up |
| SEC4.8 | review دسترسی super_admin | users table |

### 9.3 DevOps Production

| # | اقدام | مرجع |
|---|--------|------|
| O4.1 | `APP_SERVER=gunicorn`, workers مناسب CPU | staging.example |
| O4.2 | healthcheck: `/health`, `/ready` در load balancer | compose |
| O4.3 | `scripts/backup_db.sh` cron روزانه + off-site (S3) | OPERATIONS |
| O4.4 | log aggregation (Loki/ELK/CloudWatch) | ops |
| O4.5 | alert روی 5xx، payment verify fail، DB down | monitoring |
| O4.6 | RPO ≤ 24h، RTO ≤ 2h — تست restore ماهانه | OPERATIONS |
| O4.7 | upload volume `karzar_uploads` پشتیبان | ops |
| O4.8 | CI gate: ruff + mypy + pytest + alembic | `.github/workflows` |

### 9.4 Deploy Production — چک‌لیست

1. [ ] Tag release + [API_CHANGELOG.md](API_CHANGELOG.md) به‌روز
2. [ ] CI سبز روی `main`
3. [ ] backup DB production قبل از deploy
4. [ ] `alembic upgrade head`
5. [ ] deploy API → smoke `/ready`
6. [ ] deploy storefront + admin
7. [ ] smoke: OTP واقعی → خرید کوچک → verify
8. [ ] ۱۵ دقیقه مانیتور error rate
9. [ ] اعلان به تیم

### 9.5 Gate F4 (Launch)

- [ ] پرداخت واقعی موفق (≥۱ تراکنش تست)
- [ ] SMS OTP واقعی
- [ ] ۴۸ ساعت بدون SEV1
- [ ] runbook incident در دسترس on-call

---

## 10. چک‌لیست جامع بر اساس نقش

### 10.1 تیم Backend

- [ ] migrations روی staging/production
- [ ] env validation (Redis، CORS، weak PIN)
- [ ] payment flow + ledger
- [ ] order expiry worker
- [ ] product slug API (F2)
- [ ] tracking fields (F1)
- [ ] CI: alembic در pipeline ✅
- [ ] OpenAPI export برای فرانت

### 10.2 تیم Frontend — Storefront

- [ ] OTP fix (F1.1)
- [ ] USE_MOCK=false
- [ ] idempotency headers
- [ ] timeline سرور
- [ ] error codes UX
- [ ] build production
- [ ] SEO routes
- [ ] E2E Playwright (توصیه)

### 10.3 تیم Frontend — Admin

- [ ] USE_MOCK=false
- [ ] order workflow کامل
- [ ] refund/cancel messaging
- [ ] CMS pages (F2)
- [ ] build production

### 10.4 تیم Data / محتوا

- [ ] category tree نهایی
- [ ] CSV import محصولات
- [ ] تصاویر
- [ ] قیمت‌گذاری و مالیات
- [ ] بلاگ و hero
- [ ] متن‌های قانونی (گارانتی، شرایط فروش)

### 10.5 تیم Ops / DevOps

- [ ] Docker rebuild 3.12
- [ ] staging environment
- [ ] SSL
- [ ] backup/restore تست‌شده
- [ ] monitoring + alerts
- [ ] secrets management

### 10.6 QA

- [ ] smoke scripts
- [ ] regression قبل هر release
- [ ] mobile/RTL
- [ ] payment edge cases
- [ ] load smoke (اختیاری)

---

## 11. معماری استقرار پیشنهادی (Production)

```text
                    ┌─────────────┐
                    │   CDN/WAF   │
                    └──────┬──────┘
                           │ HTTPS
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   shop.example.com  admin.example.com  api.example.com
   (Next.js :3000)   (Next.js :3001)   (FastAPI :8000)
          │                │                │
          └────────────────┴────────────────┘
                           │
                    ┌──────┴──────┐
                    │   Nginx /   │
                    │   Caddy LB  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         PostgreSQL      Redis      Uploads vol
           :5432         :6379      /data/uploads
```

**حداقل منابع پیشنهادی (شروع):**
- API + DB + Redis: 4 vCPU / 8GB RAM
- Storefront + Admin: 2 vCPU / 4GB RAM (یا static hosting)

---

## 12. ریسک‌ها و mitigation

| ریسک | احتمال | تأثیر | اقدام |
|------|--------|-------|--------|
| OTP با API واقعی کار نکند | بالا | بالا | F1.1 فوری |
| Docker image قدیمی (Py 3.10) | بالا | متوسط | rebuild F0.5 |
| داده ناقص در launch | بالا | بالا | F2 اجباری قبل F4 |
| پرداخت double-charge | متوسط | بالا | idempotency F1.3–4 |
| SMS هزینه/محدودیت | متوسط | متوسط | rate limit + Kavenegar template |
| import CSV خراب stock | متوسط | متوسط | backup + staging import اول |
| عدم parity فرانت/بک | متوسط | متوسط | OpenAPI diff در CI |

---

## 13. شاخص‌های موفقیت (KPIs) پس از Launch

| KPI | هدف هفته اول | هدف ماه اول |
|-----|--------------|-------------|
| Uptime API | ≥ 99% | ≥ 99.5% |
| Checkout completion | ≥ 60% | ≥ 75% |
| Payment verify success | ≥ 95% | ≥ 98% |
| OTP delivery | ≥ 90% در ۳۰s | ≥ 95% |
| P0 bugs باز | 0 | 0 |
| زمان پاسخ PLP p95 | < 2s | < 1.5s |

---

## 14. مسیر بحرانی (Critical Path)

```text
F0 env OK
  → F1 OTP fix + smoke E2E
    → F2 catalog import
      → F3 staging HTTPS + QA
        → F4 Zarinpal + Kavenegar + deploy
          → LAUNCH
```

**طولانی‌ترین مسیر:** import داده (F2) و یکپارچه‌سازی پرداخت/SMS (F4) — موازی‌سازی توصیه می‌شود:
- فرانت F1 همزمان با آماده‌سازی CSV
- staging F3 همزمان با تکمیل import

---

## 15. تعریف Done نهایی — «وبسایت اجرایی است»

پروژه وقتی **اجرایی** محسوب می‌شود که **همه** موارد زیر برقرار باشد:

1. **Storefront** روی دامنه HTTPS با `USE_MOCK=false` قابل خرید است.
2. **Admin** سفارش‌ها، کاتالوگ، استعلام، و refund را مدیریت می‌کند.
3. **کاتالوگ واقعی** (نه فقط seed dev) در PLP/PDP نمایش داده می‌شود.
4. **OTP SMS** و **پرداخت Zarinpal** در production تست شده‌اند.
5. **Backup روزانه** + restore تست‌شده وجود دارد.
6. **مانیتورینگ** `/ready` + alerts فعال است.
7. **مستندات** runbook و incident response در دسترس on-call است.
8. **چک‌لیست F1–F4** تیک خورده است.

---

## 16. پیوست — دستورات سریع

### راه‌اندازی محلی (کامل)

```bash
# Terminal 1 — API
cd Karzar && source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Storefront
cd frontend/Storefront
NEXT_PUBLIC_USE_MOCK=false npm run dev -- --port 3000

# Terminal 3 — Admin
cd frontend/admin-panel
NEXT_PUBLIC_USE_MOCK=false npm run dev -- --port 3001
```

### Staging deploy

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build
docker compose exec app alembic upgrade head
curl -sf https://api.staging.example.com/ready
```

### پس از Launch — پشتیبانی روزانه

- بررسی `/ready` و error logs
- بررسی تراکنش‌های ناموفق پرداخت
- بررسی صف SMS/OTP
- backup موفق شبانه

---

*این سند برنامه اجرایی زنده است — پس از هر فاز، وضعیت checkboxها و درصد آمادگی را به‌روز کنید.*

**نگهداری:** با هر release بک‌اند، بخش §3 و §6.3 را بازبینی کنید.
