# Owner Architecture Decision — ARCH-7-L1-ROOTS

| Field | Value |
|-------|-------|
| **Journal entry** | `OWNER-ARCH-DECISION-001` |
| **DECISION_ID** | `ARCH-7-L1-ROOTS` |
| **DECISION_DATE** | 2026-10-18 |
| **DECISION_TYPE** | `CONDITIONAL_ARCHITECTURE_ACCEPTANCE` |
| **B2 link** | `audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18/` → group `ARCH-7-L1-ROOTS` |
| **Prerequisite gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |

## Owner statement (FA)

«به‌عنوان مالک، هفت ریشهٔ معماری پیشنهادی را به‌صورت مشروط می‌پذیرم، اما نام‌های نمایشی، عناوین سئو و URLها را هنوز تأیید نمی‌کنم. تحقیق نام‌گذاری بازار ایران را به‌عنوان یک گیت مستقل ثبت کنیم؛ هیچ APPLY یا Deploy مجاز نیست.»

## Approved scope (structural)

- Seven buyer-facing L1 commerce roots (distinct from seven scientific domains).
- Codes:
- `KZ.CAT.BUYER_CUTTING_TOOLS`
- `KZ.CAT.BUYER_FLUIDS`
- `KZ.CAT.BUYER_MACHINES`
- `KZ.CAT.BUYER_METROLOGY`
- `KZ.CAT.BUYER_THREAD_REPAIR`
- `KZ.CAT.BUYER_TOOLHOLDING`
- `KZ.CAT.BUYER_WORKHOLDING`

## Explicitly NOT approved

- Final Persian/English display names, menu labels, H1, metadata/SEO copy.
- Slugs, URLs, canonical/redirect decisions.
- Product category reassignment, runtime category create/delete.
- `CATEGORY_APPLY`, production deploy, SEO deploy.

## B2 snapshot policy

Merged B2 remains an immutable historical review artifact. `C-GROUPED-OWNER-DECISION-REGISTER.csv` still shows `PENDING` for this group; this journal entry is the authoritative Owner record for conditional acceptance.

## Other B2 groups

Nine decision groups remain `PENDING` — see `04-B2-REMAINING-PENDING-DECISION-GROUPS.csv`.