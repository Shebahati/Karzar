# فرانت جلوتر از بک — APIهایی که بک‌اند باید بسازد

**تاریخ:** ۱۸ ژوئیه ۲۰۲۶  
**مخاطب:** تیم بک‌اند / محصول  
**هدف:** هر جایی که UI کارزار الان به قابلیت نیاز دارد ولی اندپوینت واقعی نیست (یا ناقص است).

**normative_role:** `companion` (FA) — AODS `CR-020` / **D18**  
**translated_from:** `01-fe-ahead-be-needed-en.md` (EN = قرارداد هنجاری؛ هر دو باید در یک PR عوض شوند)

> نکته: بعضی قابلیت‌های جعلی در remediation اخیر از UI حذف یا «به‌زودی» شدند. این سند همان نیازهایی را می‌گوید که **اگر بخواهید محصول کامل شود** بک باید بزند.

> **CR-020:** مسیرهای API برای اندپوینتهای **ساخته‌نشده** فقط **پیشنهاد**اند و Canon نیستند. حقیقت زمان اجرا: `openapi/v1.json` + کد. تنظیمات سایت تا انتخاب یک مسیر توسط Backend Architect قرارداد نیست.

---

## جمع‌بندی یک‌خطی

فرانت برای فروش و سفارش اصلی کار می‌کند. برای «فروشگاه واقعی + پنل کامل»، بک باید چند سطح قابلیت اضافه کند: **تنظیمات سایت، اسناد، moderation، تیکت تماس، گزارش، آدرس مشتری، (اختیاری) wishlist و refund جزئی**.

---

## ۱) اولویت بالا — بدون این‌ها UI یا ناقص می‌ماند یا لوکال دروغ می‌گوید

| نیاز محصول | وضعیت فعلی فرانت | API پیشنهادی بک (غیرCanon) | قرارداد پیشنهادی (ساده) |
|------------|------------------|-----------------|-------------------------|
| تنظیمات سراسری فروشگاه | Settings ادمین فقط `localStorage`؛ فوتر/تماس هاردکد | **proposed / non-Canon** — طرح‌های تاریخی: EN `GET/PUT /api/v1/settings/site`؛ FA `GET/PUT /cms/site-settings` یا `/settings` — تا انتخاب Backend Architect هیچ‌کدام binding نیست | فیلدها (تصویری): نام، تلفن، ایمیل، آدرس، نقشه، `inquiry_enabled`، ساعات پاسخ |
| کتابخانه اسناد | صفحه Documents = به‌زودی | CRUD `/cms/documents` یا `/media` (پیشنهاد) | آپلود فایل، لیست، دانلود امن، حذف + step-up |
| وضعیت تیکت تماس | فقط لیست | `PATCH /cms/contact-submissions/{id}` (پیشنهاد) | وضعیت: `new` / `read` / `replied` / `archived` + note |
| تأیید نظرات محصول | کامنت بلافاصله عمومی | `PATCH /cms/product-comments/{id}` (پیشنهاد) | `pending` / `approved` / `rejected`؛ لیست عمومی فقط approved |
| گزارش واقعی ادمین | Reports از نمونهٔ محدود در مرورگر | `GET /reports/overview` (+ اختیاری سری زمانی) (پیشنهاد) | سفارش‌های نیازمند اقدام، درآمد، استعلام باز، موجودی کم |

---

## ۲) اولویت متوسط — تجربهٔ B2B کامل‌تر

| نیاز | چرا | API پیشنهادی |
|------|-----|--------------|
| دفترچه آدرس مشتری | چک‌اوت الان استان/شهر متن آزاد است | `GET/POST/PUT/DELETE /users/me/addresses` |
| فلگ صریح «فقط استعلام» روی محصول | الان UI از `base_price == null` حدس می‌زند | فیلد `pricing_mode: fixed \| inquiry` در product |
| بازپرداخت جزئی | الان فقط refund کامل | `POST /payments/refund` با `amount` اختیاری |
| فید تخفیف واقعی | پیشنهاد ویژه از newest فیلتر می‌شود | `sort=discount` یا `GET /products/?has_discount=1` |
| محتوای درباره ما / بلوک‌های مارکتینگ | About و بعضی نوارهای هوم استاتیک‌اند | CMS pages یا `GET /cms/pages/{slug}` |

---

## ۳) اولویت پایین / اختیاری

| نیاز | توضیح |
|------|--------|
| Wishlist | قلب قبلاً تزئینی بود و برداشته شد؛ اگر بخواهید: `GET/POST/DELETE /wishlist` |
| درخواست تماس/SMS از PDP | قبلاً جعلی بود و حذف شد؛ اگر برگردد: `POST /leads/callback` با rate-limit |
| پیش‌نویس استعلام ذخیره‌شده سمت سرور | الان بیشتر لوکال/pending است | `POST /inquiries/drafts` |

---

## ۴) قراردادهای مشترک که بک باید رعایت کند تا فرانت درست کار کند

1. همهٔ لیست‌ها `{ data, meta: { total_count, ... } }` — فرانت pagination را به `meta` وابسته کرده.  
2. `lane` / `mode`: `purchase` vs `inquiry` یکدست در cart، checkout، orders.  
3. تایم‌لاین سفارش در `track` و detail ادمین ترجیحاً همیشه از سرور بیاید.  
4. عملیات مخرب با `X-Step-Up-Token`.  
5. `Idempotency-Key` روی checkout و payment init حفظ شود.  
6. CORS فقط دامنه‌های واقعی فروشگاه و ادمین در پروداکشن.

---

## ۵) ترتیب پیشنهادی ساخت برای بک

1. Site settings (سریع‌ترین اثر روی اعتماد فروشگاه)  
2. Contact ticket status + comment moderation  
3. Documents library  
4. Reports overview  
5. Addresses + pricing_mode + partial refund  

---

*همراه انگلیسی فنی: `docs/gaps/01-fe-ahead-be-needed-en.md`*
