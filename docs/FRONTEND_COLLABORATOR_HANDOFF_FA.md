# متن آماده برای ارسال به همکار فرانت

کپی کامل بلوک زیر را برای `@mhrbzandi-Designer` بفرستید (بعد از Accept دعوت GitHub و merge شدن PR منشور).

---

سلام مهراب — دسترسی Write روی ریپوی یکپارچه `Shebahati/Karzar` برایت فعال می‌شود. از این به بعد merge (بعد از گیت‌ها) و Deploy Staging را خودت می‌توانی بزنی. Production فقط با من است.

## قانون طلایی
کد و UI تو نباید با **کد فعلی (as-built)**، **`openapi/v1.json`**، یا ردیف‌های **Accepted/Binding** در Canon Lock تضاد داشته باشد. اگر مبهم بود، حدس نزن — بپرس و متوقف شو.

منشور کامل (الزامی):  
https://github.com/Shebahati/Karzar/blob/main/docs/FRONTEND_COLLABORATOR_CHARTER.md  

دیپلوی:  
https://github.com/Shebahati/Karzar/blob/main/docs/COLLABORATOR_DEPLOY.md

## چه کارهایی مجوزی
1. فقط این مسیرها: `frontend/Storefront/**` و `frontend/admin-panel/**` (و چند فایل README فرانت طبق منشور).
2. Branch با پیشوند: `feature/*` یا `fix/*` یا `hotfix/*` یا `chore/*` — مستقیم روی `main` نه.
3. یک موضوع در هر PR.
4. قبل از push محلی: `npm ci` سپس `npx tsc --noEmit` و `npm run lint` و `npm test` داخل همان اپ.
5. PR به `main` → صبر برای CI سبز (`storefront` / `admin-panel` / `Collaborator Scope Gate`) → Approve از من → بعد **خودت Squash merge**.
6. بعد از merge: GitHub → Actions → **Deploy Staging** → Run workflow از شاخه `main`.
7. بعد از دیپلوی چک کن:  
   https://www.karzartools.com/  
   https://admin.karzartools.com/  
   https://api.karzartools.com/ready  

توجه: Staging همان سرور زنده سایت است؛ دیپلوی = اثر روی کاربر واقعی.

## چه کارهایی ممنوع
- دست زدن به `app/`، `alembic/`، `openapi/`، `docs/architecture/`، `aods/`، `deploy/`، `.github/workflows/`، `scripts/` بدون PR جدا که من راه می‌اندازم.
- افزودن/ارتقای پکیج npm بدون تأیید کتبی من.
- ساختن فیلد/endpoint که در OpenAPI نیست.
- dual-write مشخصات↔Facts، UI انتشار Fact، RAG، ادیتور Taxonomy/Dictionary، یال `PRODUCT_CLASSIFIED_AS`.
- Knowledge ادمین: فقط خواندن APIهای موجود؛ سه نوع یال یخ‌زده فقط.
- خواندن/استناد به این فایل‌ها به‌عنوان منبع حقیقت:  
  `frontend/AI_CONTEXT.md` · `frontend/BACKEND_NON_COMPLIANCE.md` · `docs/FRONTEND_IMPLEMENTATION_GUIDE.md`
- Deploy Production.
- Commit کردن `.env` / کلید / توکن.

## قرارداد و URL
- مرجع API: `openapi/v1.json` + `docs/FRONTEND_INTEGRATION.md`
- قوانین فرانت: `docs/development/standards/frontend-change-rules.md`
- PDP کانونیکال: `/product/{slug}` · Brand Hub: `/brands/{slug}`
- اسلات PDF و لوازم جانبی را برای empty مخفی نکن.

## قالب کوتاه PR
در بدنه PR این را پر کن (قالب ریپو را هم کامل کن):

```text
Canon Lock: docs/architecture/CANON-LOCK.md (Wave-1)
Refs:
Packs: docs/FRONTEND_INTEGRATION.md · openapi/v1.json
Authority: docs/FRONTEND_COLLABORATOR_CHARTER.md
```

اگر CI Scope Gate قرمز شد یعنی فایلی بیرون از allowlist لمس شده — همان را برگردان یا از من بخواه PR جدا.

---
