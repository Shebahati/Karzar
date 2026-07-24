# راهنمای استقرار برای همکار فرانت (GitHub Actions)

ریپوی یکپارچه: [Shebahati/Karzar](https://github.com/Shebahati/Karzar)

```
Karzar/
  app/                 # بک‌اند FastAPI
  deploy/staging/      # اسکریپت‌های VPS
  frontend/
    Storefront/
    admin-panel/
  .github/workflows/
    deploy-staging.yml
    deploy-production.yml
```

روی سرور فعلاً یک محیط است (`karzartools.com`). مسیرها:
- بک‌اند: `/opt/karzar/Karzar`
- فرانت: `/opt/karzar/frontend`

## استقرار Staging (خودکار)

1. روی `main` کار کنید (یا PR بزنید و بعد از merge).
2. تغییر در `frontend/**` یا بک‌اند را push کنید.
3. Actions → **Deploy Staging** باید سبز شود.
4. دستی: Actions → Deploy Staging → **Run workflow**.

چک سریع بعد از دیپلوی:
- https://www.karzartools.com/
- https://admin.karzartools.com/
- https://api.karzartools.com/ready

## استقرار Production

تا وقتی سرور جدا برای production نداریم، workflow **Deploy Production** همان VPS را هدف می‌گیرد ولی پشت GitHub Environment `production` است (باید reviewer تأیید کند).

راه‌اندازی دستی:
1. Actions → **Deploy Production** → Run workflow
2. یا push به شاخه `production` / تگ `v*`

**توصیه:** تا جداسازی واقعی host، production را فقط با workflow_dispatch + approval بزنید.

## کار روزمره طراح فرانت

```bash
git clone https://github.com/Shebahati/Karzar.git
cd Karzar/frontend/Storefront   # یا admin-panel
# ... ویرایش ...
git checkout -b feat/ui-...
git add -A && git commit -m "feat(ui): ..."
git push -u origin HEAD
# PR به main → بعد از merge، Staging خودکار دیپلوی می‌شود
```

هرگز این‌ها را commit نکنید: `.env`، `.env.local`، `.deploy-secrets`، کلید SSH.

## Secrets لازم (Repo / Environment)

| Secret | توضیح |
|--------|--------|
| `SSH_HOST` | IP یا hostname VPS |
| `SSH_USER` | معمولاً `root` |
| `SSH_PRIVATE_KEY` | کلید خصوصی Ed25519 با دسترسی SSH |
| `SSH_PORT` | اختیاری؛ پیش‌فرض 22 |

`ADMIN_SESSION_SECRET` روی خود سرور در `/opt/karzar/.deploy-secrets` نگه داشته می‌شود و در workflow چاپ نمی‌شود.
