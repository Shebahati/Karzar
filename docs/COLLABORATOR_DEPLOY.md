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
    backend-ci.yml
```

## محیط‌ها (مهم)

| محیط | شاخه / تریگر | سرور | تأیید |
|------|---------------|------|--------|
| **Staging** | **فقط** `workflow_dispatch` (Actions → Run workflow روی `main`) | همان VPS زنده (`karzartools.com`) | Environment `staging` (فقط شاخه `main`) |
| **Production** | **فقط** `workflow_dispatch` با تأیید متنی `deploy-production` | فعلاً **همان VPS** (جدا نشده) | Environment `production` + reviewer `Shebahati` + wait timer |

تا وقتی host جدا برای production نداریم، هر دیپلوی به این VPS **زنده** است. از ۱۴۰۵/۰۵/۰۸ (`CR-011` Option B) merge به `main` دیگر Deploy Staging را خودکار اجرا نمی‌کند — باید دستی Run workflow بزنید.

مسیرها روی سرور:
- بک‌اند: `/opt/karzar/Karzar`
- فرانت: `/opt/karzar/frontend`
- Runner خودمیزبان: لیبل `karzar-vps`

> چرا self-hosted؟ از GitHub-hosted به SSH این VPS timeout می‌شود. چرا artifact؟ از خود VPS به `github.com` گاهی 504 می‌دهد؛ بنابراین checkout روی `ubuntu-latest` است و فقط artifact روی runner سرور پیاده می‌شود.

## استقرار Staging (دستی — `CR-011` Option B)

1. روی شاخه فیچر کار کنید → PR به `main` بزنید (نیاز به CI سبز + review rules).
2. بعد از merge به `main`، **دیپلوی خودکار نیست**.
3. دستی: Actions → **Deploy Staging** → **Run workflow** (از شاخه `main`) — این همان VPS زنده است (HC-11/HC-12).

چک سریع بعد از دیپلوی:
- https://www.karzartools.com/
- https://admin.karzartools.com/
- https://api.karzartools.com/ready

## استقرار Production (خطرناک تا جداسازی host)

1. Actions → **Deploy Production** → Run workflow
2. در ورودی `confirm` بنویسید: `deploy-production`
3. منتظر Approve از `Shebahati` (+ تایمر انتظار) بمانید

**push به شاخه یا تگ دیگر دیگر Production را خودکار تریگر نمی‌کند.**

## کار روزمره طراح فرانت

```bash
git clone https://github.com/Shebahati/Karzar.git
cd Karzar/frontend/Storefront   # یا admin-panel
# ... ویرایش ...
git checkout -b feature/ui-...
git add -A && git commit -m "feat(ui): ..."
git push -u origin HEAD
# PR به main → بعد از merge، در صورت نیاز Actions → Deploy Staging → Run workflow (دستی؛ CR-011 B)
```

هرگز این‌ها را commit نکنید: `.env`، `.env.local`، `.deploy-secrets`، کلید SSH.

## Secrets / Infrastructure

برای workflowهای فعلی (self-hosted + artifact) معمولاً نیازی به `SSH_*` در runtime نیست؛ runner روی خود VPS است.
نام‌های secret موجود در ریپو برای مسیر جایگزین GitHub-hosted+SSH نگه داشته شده‌اند:

| Secret | توضیح |
|--------|--------|
| `SSH_HOST` | IP یا hostname VPS |
| `SSH_USER` | معمولاً `root` |
| `SSH_PRIVATE_KEY` | کلید خصوصی با دسترسی SSH |
| `SSH_PORT` | اختیاری؛ پیش‌فرض 22 |

`ADMIN_SESSION_SECRET` روی سرور در `/opt/karzar/.deploy-secrets` (یا `.env` بک‌اند) نگه داشته می‌شود.
