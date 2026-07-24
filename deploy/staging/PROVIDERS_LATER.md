# بعد از خرید Zarinpal و SMS — بدون تغییر معماری

Staging الان با `PAYMENT_PROVIDER=mock` و `SMS_PROVIDER=console` اجرا می‌شود.
وقتی درگاه و SMS را خریدی، فقط env را عوض کن و container را ری‌استارت کن.

## 1) Zarinpal

در `.env` روی VPS:

```env
PAYMENT_PROVIDER=zarinpal
ZARINPAL_MERCHANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# در صورت نیاز URLهای request/verify را از داشبورد زرین‌پال ست کنید
PAYMENT_CALLBACK_URL=https://shop.YOUR_DOMAIN/checkout/payment/callback
PAYMENT_SUCCESS_REDIRECT_URL=https://shop.YOUR_DOMAIN/checkout/success
PAYMENT_FAILURE_REDIRECT_URL=https://shop.YOUR_DOMAIN/checkout/payment/failed
```

در پنل زرین‌پال، آدرس بازگشت/callback را مطابق قرارداد API ست کنید
(معمولاً مسیر عمومی بک‌اند: `https://api.YOUR_DOMAIN/api/v1/payments/callback`).

```bash
cd /opt/karzar/Karzar
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d app
```

یک خرید تست (sandbox اگر موجود است) انجام دهید و ledger را در ادمین چک کنید.

## 2) FarazSMS / IranPayamak (پیشنهادی فعلی)

مستندات: [docs.iranpayamak.com](https://docs.iranpayamak.com/) — احراز هویت با هدر `Api-Key`؛ username/password برای ارسال وب‌سرویس لازم نیست.

۱. در پنل یک **پترن OTP** بسازید و UID آن را بردارید (مثلاً `SJ3FgPrE0C`).
۲. شماره خط ارسال را از پنل بردارید.
۳. در `.env`:

```env
SMS_PROVIDER=faraz
SMS_FARAZ_API_KEY=...
SMS_FARAZ_LINE_NUMBER=9000...
SMS_FARAZ_OTP_PATTERN_CODE=...
SMS_FARAZ_OTP_ATTR=code
OTP_DEV_ECHO=False
```

```bash
cd /opt/karzar/Karzar
docker compose -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.image.yml up -d app
```

بدون پترن، کد به حالت `sms/simple` برمی‌گردد (ممکن است صف/تأخیر داشته باشد)؛ برای OTP حتماً پترن بسازید.

## 3) Kavenegar (جایگزین)

```env
SMS_PROVIDER=kavenegar
SMS_KAVENEGAR_API_KEY=...
SMS_KAVENEGAR_SENDER=...
SMS_KAVENEGAR_OTP_TEMPLATE=...
OTP_DEV_ECHO=False
```

## 4) رفتن به Production (فقط وقتی فروش واقعی می‌خواهید)

`APP_ENV=production` در کد اجبار می‌کند:

- `DEBUG=False`
- `ENFORCE_HTTPS=True`
- `TRUSTED_HOSTS` ست باشد
- `PAYMENT_PROVIDER` غیر از `mock`
- `SMS_PROVIDER` غیر از `console`
- `ENABLE_API_DOCS=False`
- Redis اجباری

چک‌لیست کامل: [OPERATIONS.md](../../docs/OPERATIONS.md) و validators در `app/core/config.py`.

## پیچیدگی؟

خیر — مسیر دوم (اول Staging، بعد provider) همان طراحی پروژه است.
بازنویسی فرانت/بک‌اند لازم نیست؛ فقط secrets و URLها.
