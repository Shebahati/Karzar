# استقرار Staging روی VPS — راهنمای اجرایی

**هدف این فاز:** سایت روی سرور با HTTPS، کاتالوگ واقعی، پرداخت mock و SMS console.  
**Zarinpal / Kavenegar زنده:** بعداً — ببین [PROVIDERS_LATER.md](PROVIDERS_LATER.md).

پیش‌فرض دامنه: `api.` / `shop.` / `admin.` (در قالب‌ها `example.com` را عوض کنید).

---

## 0) پیش‌نیاز

- VPS Ubuntu LTS (۴ هسته / ۸GB کافی است)
- سه رکورد DNS نوع A به IP سرور: `api`، `shop`، `admin`
- دسترسی SSH با sudo

---

## 1) Bootstrap سرور

روی VPS:

```bash
# از لپ‌تاپ: کد را بفرستید یا روی سرور clone کنید
sudo git clone https://github.com/Shebahati/Karzar.git /opt/karzar/Karzar
cd /opt/karzar/Karzar
sudo bash deploy/staging/scripts/bootstrap-vps.sh
```

نصب می‌کند: Docker، Nginx، Certbot، UFW (22/80/443).

---

## 2) Backend env

```bash
cd /opt/karzar/Karzar
cp deploy/staging/.env.staging.template .env
nano .env   # همه replace-me و example.com را پر کنید
```

حداقل‌ها:

| کلید | نکته |
|------|------|
| `TRUSTED_HOSTS` | فقط hostname API مثلاً `api.yourdomain.com` |
| `CORS_ORIGINS` | `https://shop...`, `https://admin...` |
| `SECRET_KEY` / `POSTGRES_PASSWORD` / `ADMIN_STEP_UP_PIN` | قوی و یکتا |
| `PAYMENT_PROVIDER=mock` | عمداً برای این فاز |
| `SMS_PROVIDER=console` | عمداً برای این فاز |
| `PAYMENT_*_URL` | به `https://shop...` |

```bash
chmod +x deploy/staging/scripts/*.sh scripts/backup_db.sh
bash deploy/staging/scripts/deploy-backend.sh
```

چک: `curl -s http://127.0.0.1:8000/ready`

---

## 3) انتقال کاتالوگ

روی لپ‌تاپ (DB پر):

```bash
cd /path/to/Karzar
bash deploy/staging/scripts/export-local-db.sh
scp backups/karzar_catalog_*.sql.gz user@VPS:/opt/karzar/Karzar/backups/
```

روی VPS:

```bash
cd /opt/karzar/Karzar
bash deploy/staging/scripts/restore-db-staging.sh backups/karzar_catalog_XXXX.sql.gz
```

بکاپ روزانه:

```bash
sudo bash deploy/staging/scripts/install-backup-cron.sh
./scripts/backup_db.sh   # یک‌بار دستی برای اطمینان
```

---

## 4) Nginx + TLS

```bash
sudo cp deploy/staging/nginx/karzar.conf.template /etc/nginx/sites-available/karzar
sudo nano /etc/nginx/sites-available/karzar   # دامنه واقعی
sudo ln -sf /etc/nginx/sites-available/karzar /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# بعد از سبز شدن DNS:
sudo certbot --nginx -d api.YOUR_DOMAIN -d shop.YOUR_DOMAIN -d admin.YOUR_DOMAIN
```

بعد از Certbot، بلاک‌های `ssl_certificate` معمولاً خودکار فعال می‌شوند؛ در غیر این صورت خطوط کامنت‌شده در قالب را باز کنید.

---

## 5) Frontend

فرانت را کنار بک‌اند قرار دهید (clone جدا یا scp):

```bash
# مثال ساختار
# /opt/karzar/frontend/Storefront
# /opt/karzar/frontend/admin-panel

export FRONTEND_ROOT=/opt/karzar/frontend
export NEXT_PUBLIC_API_BASE_URL=https://api.YOUR_DOMAIN/api/v1
export ADMIN_SESSION_SECRET="$(openssl rand -hex 32)"   # required: HMAC for admin edge cookie
cd /opt/karzar/Karzar
bash deploy/staging/scripts/deploy-frontend.sh
```

اسکریپت:

- `USE_MOCK=false` را در build می‌پزد
- در صورت نیاز `next.config` را برای CDNهای https باز می‌کند
- کانتینرهای `karzar_shop` / `karzar_admin` را روی `127.0.0.1:3000/3001` بالا می‌آورد

---

## 6) Smoke

```bash
API_BASE=https://api.YOUR_DOMAIN \
SHOP_BASE=https://shop.YOUR_DOMAIN \
ADMIN_BASE=https://admin.YOUR_DOMAIN \
  bash deploy/staging/scripts/smoke-staging.sh
```

دستی: PLP، سرچ SKU، login ادمین، یک checkout با پرداخت mock.

OTP در Staging با `console` در لاگ API دیده می‌شود:

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml logs -f app | grep -i sms
```

---

## 7) بعداً: درگاه و SMS

[PROVIDERS_LATER.md](PROVIDERS_LATER.md) — فقط تعویض env + restart.

---

## عیب‌یابی سریع

| علامت | اقدام |
|--------|--------|
| `/ready` 503 | Redis/DB؛ `docker compose ... ps` و logs |
| CORS در مرورگر | `CORS_ORIGINS` دقیقاً با origin فرانت یکی باشد (با https) |
| redirect loop HTTPS | Nginx باید `X-Forwarded-Proto` بفرستد (در قالب هست) |
| تصویر محصول کرش Next | اسکریپت frontend remotePatterns را patch می‌کند؛ rebuild |
| پورت 8000 از اینترنت باز است | staging compose با `127.0.0.1` bind می‌کند؛ firewall فقط 80/443 |

مرجع ops عمومی: [docs/OPERATIONS.md](../../docs/OPERATIONS.md)
