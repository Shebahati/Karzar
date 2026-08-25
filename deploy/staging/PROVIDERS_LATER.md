# بعد از خرید درگاه / SMS — با احتیاط

Staging الان با `PAYMENT_PROVIDER=mock` و `SMS_PROVIDER=console` اجرا می‌شود.

## 1) Zarinpal

برای زرین‌پال (provider از پیش پیاده‌شده) معمولاً فقط env و ری‌استارت کافی است:

```env
PAYMENT_PROVIDER=zarinpal
ZARINPAL_MERCHANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PAYMENT_CALLBACK_URL=https://api.YOUR_DOMAIN/api/v1/payments/callback
PAYMENT_SUCCESS_REDIRECT_URL=https://shop.YOUR_DOMAIN/checkout/success
PAYMENT_FAILURE_REDIRECT_URL=https://shop.YOUR_DOMAIN/checkout/payment/failed
```

```bash
cd /opt/karzar/Karzar
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d app
```

## 1b) SEP (سامان کیش) — بازنویسی لازم است

SEP **فقط با عوض‌کردن env فعال نمی‌شود**. پیاده‌سازی اختصاصی Token / POST callback / Verify /
retry در کد لازم است. مرجع عملیاتی: [`docs/SEP_PAYMENT_GATEWAY.md`](../../docs/SEP_PAYMENT_GATEWAY.md).

نمونهٔ env (شماره ترمینال واقعی را commit نکنید):

```env
PAYMENT_PROVIDER=sep
PAYMENT_CALLBACK_URL=https://api.YOUR_DOMAIN/api/v1/payments/callback/sep
PAYMENT_SUCCESS_REDIRECT_URL=https://www.YOUR_DOMAIN/checkout/success
PAYMENT_FAILURE_REDIRECT_URL=https://www.YOUR_DOMAIN/checkout/payment/failed
SEP_TERMINAL_ID=
SEP_TOKEN_URL=https://sep.shaparak.ir/OnlinePG/OnlinePG
SEP_SEND_TOKEN_URL=https://sep.shaparak.ir/OnlinePG/SendToken
SEP_VERIFY_URL=https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/VerifyTransaction
SEP_REVERSE_URL=https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/ReverseTransaction
SEP_TOKEN_EXPIRY_MINUTES=30
```

پیش‌نیاز: ثبت IP خروجی VPS نزد SEP، تأیید املای Verify endpoint با SEP، migration مربوطه، و smoke بدون پرداخت واقعی.

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
- برای `sep`: `SEP_TERMINAL_ID` الزامی
- `SMS_PROVIDER` غیر از `console`
- `ENABLE_API_DOCS=False`
- Redis اجباری

چک‌لیست کامل: [OPERATIONS.md](../../docs/OPERATIONS.md) و validators در `app/core/config.py`.

## پیچیدگی؟

- **Zarinpal / SMS:** اغلب فقط secrets و URLها.
- **SEP:** پیاده‌سازی در کد + migration + IP whitelist + تأیید endpoint با SEP؛ جزئیات در `docs/SEP_PAYMENT_GATEWAY.md`.
