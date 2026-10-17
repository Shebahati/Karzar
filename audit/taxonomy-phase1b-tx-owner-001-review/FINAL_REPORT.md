# TX-OWNER-001 — Product-level semantic review


## خلاصه اجرایی (فارسی)

این موج **بررسی معنایی محصول‌محور TX-OWNER-001** است و بر اساس سرشمار تاریخ‌دار **2026-10-15T09:34:39Z** انجام شده؛ وضعیت زندهٔ امروز کاتالوگ را اثبات نمی‌کند.

- **جمعیت بررسی:** 262 محصول یکتا در دسته‌های ۱۵۸ و ۱۶۰.
- **پیشنهاد خروج از کاتالوگ:** 242 مورد.
- **تعارض معنایی (primary):** 0 مورد.
- **استثناء صنعتی (primary):** 1 مورد — **بدون مجوز rehome**.
- **نیاز به تصمیم مالک (primary):** 1 مورد.
- **شواهد ناکافی:** 18 مورد.
- **صف تأیید مالک:** 262 ردیف (شامل همهٔ پیشنهادها).

هیچ APPLY، حذف، یا انتقال خودکار انجام نشده است. گام بعدی: تأیید مالک روی پیشنهادهای سطح محصول.


## Identity

- Git HEAD: `d0ad0a4107af619483f73b220e63a0b0a8f893d7`
- Baseline PR #498 reviewed HEAD: `156e46e4c4d23e470c93108b1d2009571883f969`
- Historical census: `/home/shebahati/Projects/Karzar/audit/taxonomy-phase1b-baseline-2026-10-15/02-PRODUCT-CATEGORY-CENSUS.csv` (collected 2026-10-15T09:34:39Z)

## Disposition distribution

{
  "NEEDS_MORE_EVIDENCE": 18,
  "CATALOG_EXIT_CANDIDATE": 242,
  "INDUSTRIAL_EXCEPTION_CANDIDATE": 1,
  "OWNER_DECISION_REQUIRED": 1,
  "SEMANTIC_CONFLICT": 0
}

## Owner decision queue

Full queue: `05-OWNER-DECISION-QUEUE.csv` (262 rows). Industrial exceptions are **not** auto-approved.

## Correction notes (vs d0ad0a41)

- Removed broad metalworking inference from CNC/تیغ/شیارزن tokens alone.
- Mighty Seven QA-210/211 documented as Air Die Grinders (OEM) → workshop exit, not Toolholding.
- BladeKat-style router bits treated as woodworking CNC tooling (exit), not Cutting Tools inserts.
- Grooving/finishing blades without OEM context → NEEDS_MORE_EVIDENCE.

## Safety

All proposals are review-only. No production mutation, no manifest rewrite, no megamenu/SEO changes.

## Next gate

Owner approval of proposed product-level dispositions before any Phase 1B APPLY authorization.
