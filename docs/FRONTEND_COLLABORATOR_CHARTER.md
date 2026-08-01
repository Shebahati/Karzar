# منشور همکار فرانت — Karzar (`mhrbzandi-Designer`)

**Status:** Operational (Owner-delegated) · **Not** Canon Accept  
**Audience:** Frontend collaborator with Write on `Shebahati/Karzar`  
**Companion:** [`COLLABORATOR_DEPLOY.md`](./COLLABORATOR_DEPLOY.md) · Owner setup: [`OWNER_GITHUB_FRONTEND_ACCESS.md`](./OWNER_GITHUB_FRONTEND_ACCESS.md)

این سند معیار کار روزمره است. اگر با کد as-built یا `openapi/v1.json` یا ردیف Accepted در Canon Lock تضاد داشت، **توقف** کنید و از Owner بپرسید — حدس نزنید.

---

## 1. نقش و دسترسی

**سیاست Owner (2026-08-01):** همکار فرانت **بدون ریویو Owner** merge و Deploy Staging می‌کند. ایمنی = Scope Gate + Frontend CI + smoke اجباری بعد از دیپلوی.

| کار | مجاز؟ | شرط |
|-----|--------|-----|
| Branch + PR روی فرانت | بله | پیشوند `feature/*` \| `fix/*` \| `hotfix/*` \| `chore/*` |
| Merge به `main` | بله — **بدون Approve Owner** | همهٔ status checkهای اجباری سبز + فقط مسیر allowlist + up-to-date با `main` |
| Deploy Staging | بله | فقط بعد از merge؛ Actions → **Deploy Staging** → Run workflow روی `main` → سپس smoke |
| Deploy Production | خیر | فقط Owner (`confirm` + Environment `production`) |
| تغییر بک‌اند / DB / OpenAPI / Canon / lockfile | خیر | PR جدا با Owner؛ scope-gate قرمز می‌شود |

**هشدار محیط:** Staging = همان VPS زنده (`karzartools.com`). هر Deploy Staging روی سایت عمومی اثر دارد. مسئولیت smoke بعد از دیپلوی با همکار فرانت است.

---

## 2. محدودهٔ فایل (allowlist)

### مجاز بدون هماهنگی جدا

- `frontend/Storefront/**` و `frontend/admin-panel/**` به‌جز فایل‌های قفل‌شدهٔ زیر
- `frontend/README.md`, `frontend/FRONTEND_CHANGES.md`, `frontend/INTEGRATION_RUNTIME_NOTES.md`, `frontend/LOCAL_STACK_ACCESS.md`

### ممنوع (scope-gate برای actor غیر از Owner fail می‌کند)

- هر مسیر بیرون از allowlist بالا (از جمله `app/**`, `alembic/**`, `openapi/**`, `docs/architecture/**`, `aods/**`, `.github/**`, `deploy/**`, `scripts/**`)
- **حتی داخل فرانت:** `package.json` و `package-lock.json` (dependency فقط با Owner)

اگر برای UI به فیلد API نیاز دارید که در OpenAPI نیست: **UI را جعل نکنید** — از Owner/بک‌اند بخواهید.

---

## 3. اسناد — بخوانید / نخوانید

### بخوانید و معیار قرار دهید

1. [`docs/architecture/CANON-LOCK.md`](./architecture/CANON-LOCK.md) — فقط ردیف‌های **Accepted** / **Binding**
2. [`openapi/v1.json`](../openapi/v1.json) و در صورت نیاز live `/api/openapi.json`
3. [`docs/FRONTEND_INTEGRATION.md`](./FRONTEND_INTEGRATION.md)
4. [`docs/development/standards/frontend-change-rules.md`](./development/standards/frontend-change-rules.md)
5. [`docs/development/standards/pr-checklist.md`](./development/standards/pr-checklist.md)
6. [`docs/development/git-development-workflow.md`](./development/git-development-workflow.md)
7. مسیرهای sibling در همان اپ (الگوی as-built بر اسناد کهنه ارجح است)

### هرگز به‌عنوان منبع حقیقت نخوانید / معیار merge نکنید

- `frontend/AI_CONTEXT.md`
- `frontend/BACKEND_NON_COMPLIANCE.md`
- `docs/FRONTEND_IMPLEMENTATION_GUIDE.md`
- اسناد Phase1–3 knowledge به‌عنوان SoT زنده
- هر سند فقط-Proposed به‌تنهایی برای توجیه merge (بدون Accepted Canon)

---

## 4. قرمزهای محصول / Knowledge (بدون استثنا تا Board جدا)

- بدون dual-write بین `products.specifications` و Facts
- بدون UI برای assert/publish Facts
- بدون RAG / پاسخ generative مشتری‌رو
- بدون ویرایشگر Taxonomy / Property Dictionary در ادمین
- بدون یال یا projector برای `PRODUCT_CLASSIFIED_AS`
- Knowledge ادمین: فقط مصرف read-only APIهای موجود (`/api/v1/knowledge/*`) روی **سه** نوع یال یخ‌زده:
  - `PRODUCT_BELONGS_TO_CATEGORY`
  - `PRODUCT_BRANDED_AS`
  - `ARTICLE_EXPLAINS_PRODUCT`
- URL: PDP کانونیکال `/product/{slug}`؛ Brand Hub `/brands/{slug}`؛ بدون hub فست نامحدود
- اسلات PDF و لوازم جانبی: empty صادقانه — پنهان نکنید

---

## 5. گردش کار اجباری

```text
1. git fetch origin && git checkout main && git pull origin main
2. git checkout -b feature/<short-name>
3. فقط allowlist را لمس کنید
4. محلی:
   cd frontend/Storefront   # یا admin-panel
   npm ci && npx tsc --noEmit && npm run lint && npm test
5. commit واضح · push · PR به main
6. قالب PR را کامل کنید (Canon citations + rollback + test plan)
7. منتظر CI سبز: Frontend CI + Collaborator Scope Gate (+ e2e اگر required باشد)
8. **بدون منتظر Owner:** Squash-merge
9. Actions → Deploy Staging → Run workflow (branch: main)
10. Smoke فوری:
    https://www.karzartools.com/
    https://admin.karzartools.com/
    https://api.karzartools.com/ready
    + صفحهٔ تغییرکرده (دسکتاپ/موبایل). اگر شکست: revert یا hotfix + Deploy دوباره.
```

هرگز commit نکنید: `.env`, `.env.local`, `.deploy-secrets`, کلید SSH، توکن.

---

## 6. چک‌لیست خوداظهاری قبل از merge (بدون Owner review)

- [ ] یک concern در این PR
- [ ] فقط مسیرهای allowlist — بدون `package.json` / lockfile
- [ ] OpenAPI/as-built نقض نشده
- [ ] اسناد ممنوع استناد نشده
- [ ] بدون Facts / dual-write / RAG / taxonomy editor
- [ ] URL/SEO در صورت تغییر: ADR-010 + RFC-004/005 در بدنهٔ PR
- [ ] typecheck + lint + test محلی سبز
- [ ] CI روی PR سبز
- [ ] rollback نوشته شده
- [ ] secret نیست
- [ ] بعد از merge: Deploy Staging + smoke برنامه‌ریزی شده

---

## 7. تعارض و توقف

اگر دو منبع Accepted با هم نخوانند، یا OpenAPI با UI فعلی نخواند: **PR را باز نکنید / merge نکنید** — به Owner گزارش دهید. انتخاب خاموش یک «برنده» ممنوع است.

---

## 8. استناد حداقلی برای PRهای فرانت

```text
Canon Lock: docs/architecture/CANON-LOCK.md (Wave-1)
Refs: <!-- مثلاً ADR-010, RFC-004, RFC-005 در صورت URL/SEO -->
Packs: docs/FRONTEND_INTEGRATION.md · openapi/v1.json
Authority: docs/FRONTEND_COLLABORATOR_CHARTER.md
```
