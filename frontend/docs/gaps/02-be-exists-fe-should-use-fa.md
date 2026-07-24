# بک زده — فرانت باید مصرف کند (یا هنوز کامل مصرف نکرده)

**تاریخ:** ۲۴ ژوئیه ۲۰۲۶  
**مخاطب:** تیم فرانت / QA  
**هدف:** APIهایی که در بک‌اند هستند ولی یا هنوز در UI نیستند، یا فقط ناقص وصل شده‌اند.

---

## جمع‌بندی یک‌خطی

عمیق‌سازی ژوئیه ۲۰۲۶ انجام شد: سبد سرور قبل از چک‌اوت، آمار Reports از `/products/statistics`، فیلتر change-log، لینک ممیزی از سفارش/مشتری، دلیل اجباری bulk stock، و نوار `/health`+`/ready` در داشبورد ادمین.

---

## ۱) عمداً استفاده نشده / ops خارج از فروشگاه

| API بک‌اند | معنی | وضعیت فرانت |
|------------|------|-------------|
| `POST /auth/register` | ثبت‌نام با پسورد | نیست — محصول OTP-primary است؛ `ALLOW_PUBLIC_REGISTER=false` |
| `GET /articles/` و `GET /articles/{slug}` | alias بلاگ | فرانت از `/blog/` استفاده می‌کند |
| `GET /metrics` | Prometheus | مانیتورینگ زیرساختی — نه UI محصول |
| `GET /` و `GET /api/v1` | ایندکس API | فقط دیباگ |

---

## ۲) عمیق‌سازی انجام‌شده (چک QA)

| API | کار انجام‌شده |
|-----|----------------|
| `GET/PUT/DELETE /cart` | همگام‌سازی در سبد + reconcile قبل از چک‌اوت خرید + هشدار ناموجودی |
| `GET /orders/track` + timeline | برچسب «تخمینی» وقتی timeline سرور خالی است |
| `GET /products/statistics` | داشبورد + صفحه Reports از آمار سرور |
| `GET /health` ، `GET /ready` | نوار وضعیت در داشبورد ادمین |
| `POST …/bulk/stock-adjust` | انتخاب چندصفحه‌ای + دلیل اجباری |
| `GET …/change-log` | فیلتر قیمت / موجودی / سایر |
| `GET /users/audit-logs/list` | فیلتر `entity_id` + لینک از سفارش و مشتری |
| `POST /auth/password-reset/*` و `change-password` | لینک از لاگین + پیام خطای واضح‌تر |

---

## ۳) چیزهایی که عمداً مصرف نمی‌کنیم

| API | دلیل |
|-----|------|
| Admin write از Storefront | جداسازی نقش |
| Refund از Storefront | فقط ادمین + step-up |
| `/cms/*` از Storefront | محتوای عمومی از `/blog` و `/hero-slides` |

---

*همراه انگلیسی فنی: `docs/gaps/02-be-exists-fe-should-use-en.md`*
