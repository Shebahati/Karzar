# TX-OWNER-001 — Product-level semantic review


## خلاصه اجرایی (فارسی)

این موج **بررسی معنایی محصول‌محور TX-OWNER-001** است و بر اساس سرشمار **۱۵ مهر ۱۴۰۴ (۲۰۲۶-۱۰-۱۵)** انجام شده؛ وضعیت زندهٔ امروز کاتالوگ را اثبات نمی‌کند.

- **جمعیت بررسی:** 262 محصول یکتا در دسته‌های ۱۵۸ و ۱۶۰ (زیرمجموعهٔ دامنهٔ رد‌شدهٔ ابزار دستی/نجاری).
- **پیشنهاد خروج از کاتالوگ:** 204 مورد (ابزار دستی/نجاری/کارگاهی).
- **تعارض معنایی (عنوان صنعتی در دستهٔ چوبی):** 35 مورد — عمدتاً تیغ/شیارزن CNC.
- **استثناء صنعتی پیشنهادی:** 15 مورد — **بدون مجوز rehome**.
- **نیاز به تصمیم مالک:** 8 مورد (مرز ابزارگیر/بادی/جک ماشین‌کاری).
- **شواهد ناکافی:** 0 مورد.

هیچ APPLY، حذف، یا انتقال خودکار انجام نشده است. گام بعدی: تأیید مالک روی پیشنهادهای سطح محصول.


## Identity

- Git HEAD: `64849323da4726dabdfad24eeded7a2874353e97`
- Baseline PR #498 reviewed HEAD: `156e46e4c4d23e470c93108b1d2009571883f969`
- Historical census: `/home/shebahati/Projects/Karzar/audit/taxonomy-phase1b-baseline-2026-10-15/02-PRODUCT-CATEGORY-CENSUS.csv` (collected 2026-10-15T09:34:39Z)

## Disposition distribution

{
  "SEMANTIC_CONFLICT": 35,
  "INDUSTRIAL_EXCEPTION_CANDIDATE": 15,
  "NEEDS_MORE_EVIDENCE": 0,
  "OWNER_DECISION_REQUIRED": 8,
  "CATALOG_EXIT_CANDIDATE": 204
}

## Owner decision queue (high level)

| Theme | Count | Owner question |
|-------|------:|----------------|
| Pneumatic die grinders with collet | 7 | Workshop pneumatic tool vs industrial metalworking accessory? |
| Machine jack | 1 | Workholding exception or catalog exit? |
| Semantic conflict (CNC inserts in woodworking category) | 35 | Approve industrial exception per SKU without auto-rehome? |

## Safety

All proposals are review-only. No production mutation, no manifest rewrite, no megamenu/SEO changes.

## Next gate

Owner approval of proposed product-level dispositions before any Phase 1B APPLY authorization.
