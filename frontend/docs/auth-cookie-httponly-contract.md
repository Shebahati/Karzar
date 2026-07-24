# قرارداد نشست Cookie / HttpOnly

وضعیت پیاده‌سازی (به‌روز):

## بک‌اند
- `POST /auth/login`, `POST /auth/otp/verify`, `POST /auth/refresh` علاوه بر JSON، کوکی‌های HttpOnly می‌گذارند:
  - `karzar_access` (Path=`/api/v1`)
  - `karzar_refresh` (Path=`/api/v1/auth`)
- `POST /auth/logout` کوکی‌ها را پاک و refreshها را revoke می‌کند
- `get_current_user` / `get_optional_current_user`: Bearer **یا** کوکی access
- `POST /auth/refresh`: body `refresh_token` اختیاری است اگر کوکی refresh موجود باشد
- تنظیمات: `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_DOMAIN`

## فرانت (live)
- `axios` با `withCredentials: true`
- JWT access/refresh دیگر در `localStorage` نوشته نمی‌شود (پاک‌سازی legacy هنگام boot)
- حافظهٔ موقت (memory) فقط برای Bearer dual-support در همان تب
- Guest cart: همچنان `karzar.storefront.cart_token` + هدر `X-Cart-Token`
- Step-up: هدر `X-Step-Up-Token` (نه cookie)

## ادمین — edge session
- `POST /api/session` بعد از login با Bearer، کوکی **HttpOnly امضاشده** `karzar_admin_session` می‌گذارد
- Middleware مقدار را با HMAC تأیید می‌کند (دیگر `=1` جعل‌پذیر نیست)
- مرز نقش همچنان `AuthGate` + `/auth/me` + `super_admin` است
- `ADMIN_SESSION_SECRET` (حداقل ۳۲ کاراکتر در production)

## CSRF / CORS
- `SameSite=Lax` روی کوکی‌های API
- CORS با `allow_credentials` وقتی origins لیست مشخص باشد (نه `*`)
