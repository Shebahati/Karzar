# متن آماده برای ارسال به همکار فرانت

کپی **فقط بلوک بین دو خط `---`** را بفرستید (بعد از: دعوت Write پذیرفته شد + PR منشور روی `main` + Branch protection طبق Owner checklist).

---

سلام مهراب.

دسترسی **Write** روی ریپوی یکپارچه داری:
https://github.com/Shebahati/Karzar

از این لحظه **بدون ریویو من** کار می‌کنی: خودت PR می‌زنی، وقتی CI سبز شد خودت **Squash merge** می‌کنی، خودت **Deploy Staging** می‌زنی.
Production را لمس نکن.

منشور الزامی (همه‌چیز اینجاست):
https://github.com/Shebahati/Karzar/blob/main/docs/FRONTEND_COLLABORATOR_CHARTER.md

دیپلوی:
https://github.com/Shebahati/Karzar/blob/main/docs/COLLABORATOR_DEPLOY.md

────────────────
قانون طلایی (اگر فقط یک چیز یادت بماند)
────────────────
سایت زنده را خراب نکن و با سیستم فعلی تضاد نساز.

معیار صحت به‌ترتیب:
1) کد فعلی داخل همان اپ (as-built / sibling components)
2) قرارداد API: `openapi/v1.json` + `docs/FRONTEND_INTEGRATION.md`
3) فقط ردیف‌های Accepted/Binding در `docs/architecture/CANON-LOCK.md`

اگر یکی از این‌ها با کار تو نمی‌خواند یا چیزی مبهم است → **همان‌جا متوقف شو و به من پیام بده.** حدس نزن. فیلد API اختراع نکن.

────────────────
گردش کار روزمره (همین را انجام بده)
────────────────
1) `git fetch origin && git checkout main && git pull origin main`
2) `git checkout -b feature/<نام-کوتاه-انگلیسی>`
   پیشوند مجاز: `feature/` یا `fix/` یا `hotfix/` یا `chore/`
   مستقیم روی `main` کامیت نکن.
3) فقط این مسیرها را عوض کن:
   - `frontend/Storefront/**`
   - `frontend/admin-panel/**`
4) محلی، داخل همان اپی که دست زدی:
   ```bash
   npm ci
   npx tsc --noEmit
   npm run lint
   npm test
   ```
   اگر Storefront بود و e2e مربوط است: `npm run test:e2e` با `NEXT_PUBLIC_USE_MOCK=true`
5) commit واضح + push + PR به `main`
6) صبر کن تا هر سه چک سبز شوند:
   - `storefront`
   - `admin-panel`
   - `Collaborator Scope Gate`
   (و اگر `storefront-e2e` در protection اجباری شد، آن هم)
7) **بدون منتظر من ماندن:** Squash and merge
8) GitHub → Actions → **Deploy Staging** → Run workflow از شاخه `main`
9) فوراً smoke:
   - https://www.karzartools.com/
   - https://admin.karzartools.com/
   - https://api.karzartools.com/ready
   + همان صفحه‌ای که عوض کردی روی دسکتاپ و موبایل

اگر بعد از دیپلوی چیزی شکست: همان PR را revert کن یا hotfix بزن و دوباره Deploy Staging.

⚠️ Staging = همان سرور زنده `karzartools.com`. Merge+Deploy یعنی کاربر واقعی می‌بیند.

────────────────
ممنوع قطعی (CI یا من رد می‌کنیم / سایت می‌شکند)
────────────────
خارج از فرانت:
- `app/` `alembic/` `openapi/` `docs/architecture/` `aods/` `deploy/` `.github/` `scripts/` `tests/` بک‌اند

داخل فرانت هم بدون پیام کتبی من:
- تغییر `package.json` / `package-lock.json` (dependency جدید یا upgrade)
- ساختن endpoint/فیلد که در OpenAPI نیست
- dual-write مشخصات↔Facts · UI انتشار Fact · RAG
- ادیتور Taxonomy / Property Dictionary
- یال یا UI برای `PRODUCT_CLASSIFIED_AS`
- Deploy Production
- commit کردن `.env` / `.env.local` / کلید / توکن
- خواندن یا استناد به این‌ها به‌عنوان حقیقت:
  `frontend/AI_CONTEXT.md`
  `frontend/BACKEND_NON_COMPLIANCE.md`
  `docs/FRONTEND_IMPLEMENTATION_GUIDE.md`

Knowledge ادمین: فقط مصرف read-only از APIهای موجود `/api/v1/knowledge/*` و فقط سه نوع یال:
`PRODUCT_BELONGS_TO_CATEGORY` · `PRODUCT_BRANDED_AS` · `ARTICLE_EXPLAINS_PRODUCT`

URL:
- PDP کانونیکال: `/product/{slug}` (نه `/products/...` به‌عنوان هدف)
- Brand Hub: `/brands/{slug}`
- اسلات PDF و لوازم جانبی را برای حالت خالی مخفی نکن

────────────────
یک PR = یک موضوع
────────────────
PR بزرگ قاطی‌پاتی نزن. اگر Scope Gate قرمز شد، فایلی بیرون از allowlist لمس شده — برگردان.

در بدنهٔ PR حداقل این را بگذار:

```text
Canon Lock: docs/architecture/CANON-LOCK.md (Wave-1)
Refs:
Packs: docs/FRONTEND_INTEGRATION.md · openapi/v1.json
Authority: docs/FRONTEND_COLLABORATOR_CHARTER.md
Rollback: <!-- revert merge SHA یا hotfix -->
```

────────────────
خلاصه یک خطی
────────────────
فرانت را قشنگ جلو ببر؛ قرارداد و کد فعلی را نشکن؛ CI سبز → خودت merge → خودت Deploy Staging → smoke؛ شک داشتی بایست.

---
