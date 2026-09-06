# KarZar — AI Project Context (quarantined stub)

# KarZar — AI Project Context (Full Handover)

> **⚠️ OBSOLETE AS SoT (2026-07-25 / audit v2 DOC finding).**  
> Do **not** trust §§1–20 of this file for current architecture. Confirmed false claims include: SQLAdmin `/admin`, “no refresh token”, missing checkout/OTP/blog/hero, ComingSoon admin pages, 5-digit migration head.  
> **Canonical sources instead:**  
> - `README.md` (cart/availability corrected 2026-07-25)  
> - `docs/API_CONTRACT.md`, `docs/HESABFA.md`, `docs/OPERATIONS.md`  
> - `docs/audits/v2/master-engineering-report-v2.md` + `docs/audits/v2/REMEDIATION-TO-9.md`  
> Only the remediation log near the end may still be historically useful. Rewrite of this file is Wave 1 of remediation.

> **هدف این سند (تاریخی):** دادن کانتکست به AI/توسعه‌دهنده.  
> **آخرین به‌روزرسانی معتبر برای SoT:** ۱۴۰۵/۰۵/۰۳ — بنر فوق را بخوانید.  
> **مسیر ریشه:** `/home/moahmmad/Projects/Karzar/Website/`

---

## Status (CR-015 / 2026-07-30)

This file is **quarantined**. Sections 1–20 contained confirmed-false architecture claims and were moved to:

[`docs/archive/AI_CONTEXT-2026-07-11.md`](../docs/archive/AI_CONTEXT-2026-07-11.md)

**Do not load the archive for agent context.** Prefer:

- `aods/README.md` + prompts under `aods/70-prompts/`
- `docs/architecture/CANON-LOCK.md`, `docs/API_CONTRACT.md`, `docs/OPERATIONS.md`
- App READMEs under `frontend/Storefront/` and `frontend/admin-panel/`

AODS marks this path `forbidden_context: true`.

---

## 21. اصلاحات فرانت فاز ۱–۵

برنامهٔ remediation (بدون بازنویسی بی‌جهت):

| فاز | موضوع | وضعیت |
|-----|--------|--------|
| **۱ Critical** | Idempotency پایدار؛ pending payment در session+local؛ sanitize `?next=`؛ refresh قبل از logout؛ bulk stock + step-up؛ بنر Reports؛ CSP `connect-src` لوکال | انجام‌شده |
| **۲ Session/Cart** | reconcile سبد بعد OTP؛ AuthGate + `/auth/me`؛ middleware نشانگر نرم؛ mock-api فقط dynamic import؛ قرارداد cookie HttpOnly (طراحی) | انجام‌شده |
| **۳ Honesty UX** | تایم‌لاین تخمینی؛ SMS نرم؛ تب purchase/inquiry؛ نام/تصویر کالا؛ moderation کامنت؛ `/terms`؛ رمز اختیاری فقط mock؛ حذف زنگ تزئینی؛ `error`/`loading` | انجام‌شده |
| **۴ SEO/Perf** | هوم RSC + prefetch؛ sitemap `/product/{id}`؛ PDP تنبل related/comments؛ allowlist تصویر | انجام‌شده |
| **۵ Hardening** | Vitest + Playwright دود؛ README/.env.example؛ CSP بدون `unsafe-eval` در production؛ skip-link + focus trap منو موبایل؛ به‌روزرسانی همین سند | انجام‌شده |

**خارج از محدوده تا آمادگی BE:** verify فقط با `authority`؛ نشست کاملاً cookie HttpOnly؛ category landing pages.

فایل قرارداد cookie: `frontend/docs/auth-cookie-httponly-contract.md`.

---

*این سند را هنگام تغییرات معماری یا اضافه شدن ماژول‌های جدید به‌روز کنید.*

