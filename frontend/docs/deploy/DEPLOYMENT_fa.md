# راهنمای دیپلویمنت کارزار (فارسی ساده)

**تاریخ:** ۱۸ ژوئیه ۲۰۲۶  
**شامل:** API (`Karzar-main`) + فروشگاه + پنل ادمین (`karzar-frontend`)

---

## ۱) چه چیزهایی لازم است روی سرور؟

| جزء | پیشنهاد | نقش |
|-----|---------|-----|
| سیستم‌عامل | Ubuntu 22.04/24.04 LTS | میزبان |
| Docker + Compose | برای API، Postgres، Redis | بک‌اند یکپارچه |
| Node.js 20 LTS | بیلد/اجرای Next.js (یا فقط بیلد + `node` برای `next start`) | فرانت |
| وب‌سرور معکوس | **Nginx** (پیشنهادی) یا Caddy | SSL، دامنه، پروکسی |
| دامنه | مثلاً `shop.example.com` و `admin.example.com` و `api.example.com` | سه زیریه جدا |
| TLS | Let's Encrypt (Certbot یا Caddy) | HTTPS اجباری |
| فضای دیسک | SSD؛ بکاپ DB جدا | آپلود تصویر + لاگ |
| RAM پیشنهادی | حداقل ۴GB برای استیج؛ ۸GB+ برای پرود با دو Next + API | جلوگیری از OOM |

---

## ۲) معماری پیشنهادی (ساده)

```text
اینترنت
   │
   ▼
Nginx (443)
   ├─ shop.example.com     → Storefront :3000
   ├─ admin.example.com    → Admin :3001
   └─ api.example.com      → API Docker :8000
                              ├─ Postgres
                              └─ Redis
```

فروشگاه و ادمین را روی دو ساب‌دامین جدا نگه دارید تا CORS و کوکی تمیز بماند.

---

## ۳) مراحل دیپلوی (ترتیب کار)

### مرحله A — آماده‌سازی سرور
1. آپدیت سیستم، فایروال (`ufw`): فقط `22`, `80`, `443`.  
2. نصب Docker، Compose، Nginx، Certbot، Node 20.  
3. کاربر غیر root برای دیپلوی؛ کلید SSH؛ غیرفعال کردن پسورد لاگین در صورت امکان.

### مرحله B — بک‌اند
1. کلون `Karzar-main` روی سرور.  
2. از `.env.example` / `.env.staging.example` یک `.env` پرود بسازید (**رمزها را قوی کنید**).  
3. تنظیمات حیاتی پرود:
   - `DEBUG=False`
   - `OTP_DEV_ECHO=False`
   - `ALLOW_PUBLIC_REGISTER=False` (مگر سیاست خلاف باشد)
   - `ENABLE_API_DOCS=False` (یا فقط IP داخلی)
   - `PAYMENT_PROVIDER=zarinpal` + Merchant واقعی
   - `SMS_PROVIDER=kavenegar` + کلید واقعی
   - `CORS_ORIGINS=https://shop...,https://admin...`
   - `TRUSTED_HOSTS=api.example.com`
   - `ENFORCE_HTTPS=True`
   - `SECRET_KEY` تصادفی ≥۳۲ کاراکتر
   - `ADMIN_STEP_UP_PIN` قوی و محرمانه
   - URLهای پرداخت روی دامنهٔ واقعی فروشگاه
4. `docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build` (یا معادل پرود).  
5. چک: `/health` و `/ready` باید ۲۰۰ باشند.

### مرحله C — فرانت
1. کلون `karzar-frontend`.  
2. در هر اپ `.env.production` / env بیلد:
   - `NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1`
   - `NEXT_PUBLIC_USE_MOCK=false`
3. بیلد:
   - `cd Storefront && npm ci && npm run build`
   - `cd admin-panel && npm ci && npm run build`
4. اجرا با `npm run start -- -p 3000` و `-p 3001` یا **PM2**/systemd.  
5. بهتر: `output: 'standalone'` در Next و کپی `.next/standalone` (اگر در پروژه فعال شد).

### مرحله D — Nginx + SSL
1. پروکسی سه دامنه به پورت‌های بالا.  
2. هدرها: `Host`, `X-Forwarded-For`, `X-Forwarded-Proto`.  
3. Certbot برای هر دامنه.  
4. ریدایرکت HTTP→HTTPS.

### مرحله E — دود آزمون
- فروشگاه لود شود و کاتالوگ از API بیاید.  
- OTP واقعی SMS کار کند.  
- پرداخت sandbox/live یک بار end-to-end.  
- لاگین ادمین + یک اقدام step-up.  
- آپلود تصویر محصول.

---

## ۴) نمونهٔ مفهومی کانفیگ Nginx

```nginx
server {
  server_name api.example.com;
  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 20m;  # آپلود تصویر
  }
}

server {
  server_name shop.example.com;
  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}

server {
  server_name admin.example.com;
  location / {
    proxy_pass http://127.0.0.1:3001;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

بعد از این، Certbot را اجرا کنید.

---

## ۵) ابزارهای پیشنهادی

| حوزه | ابزار |
|------|--------|
| پروسه فرانت | **PM2** یا systemd |
| کانتینر | Docker Compose |
| SSL | Certbot / Caddy |
| مانیتورینگ | Uptime Kuma + (اختیاری) Prometheus روی `/metrics` |
| لاگ | Docker logs + فایل لاگ API؛ بهتر Loki/Grafana در مقیاس بالاتر |
| بکاپ | `pg_dump` روزانه + نگهداری آپلودها |
| CI | GitHub Actions: lint/tsc/build روی push |
| سکرت | Docker secrets / env فایل با دسترسی `600` — نه داخل گیت |

---

## ۶) اقدامات امنیتی لازم (چک‌لیست)

- [ ] `OTP_DEV_ECHO` و mock payment در پرود خاموش  
- [ ] `ENABLE_API_DOCS=false` در اینترنت عمومی  
- [ ] رمز DB، `SECRET_KEY`، PIN ادمین، کلید SMS/Zarinpal قوی و چرخش‌پذیر  
- [ ] CORS فقط دامنه‌های واقعی  
- [ ] فایروال؛ SSH با کلید؛ fail2ban اختیاری  
- [ ] Rate limit عمومی تماس/OTP (در بک از قبل هست — Redis در پرود لازم است)  
- [ ] آپدیت منظم OS و ایمیج‌ها  
- [ ] بکاپ تست‌شدهٔ restore  
- [ ] ادمین روی ساب‌دامین جدا؛ در صورت نیاز IP allowlist  
- [ ] هدرهای امنیتی Nginx: `Strict-Transport-Security`, جلوگیری از clickjacking  
- [ ] هرگز `.env` و credential را در گیت نگذارید  

---

## ۷) مقیاس کوچک vs رشد

**شروع:** یک VPS + Docker Compose + Nginx کافی است.  
**رشد:** API و DB را جدا کنید، Redis managed، CDN برای استاتیک/تصاویر، و بیلد فرانت روی CI با artifact.

---

*نسخهٔ انگلیسی فنی: `docs/deploy/DEPLOYMENT_en.md`*
