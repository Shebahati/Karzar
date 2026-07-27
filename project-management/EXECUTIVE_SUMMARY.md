# Executive Summary — Karzar to 31 Shahrivar ۱۴۰۵

**Date:** 2026-07-27  
**Checkpoint:** 2026-09-22 (~57 days / ~8 weeks)

## Direct answers (required before execution)

### چند ساعت کار لازم است؟
- **P0 only (recommended freeze set):** ≈ **170 hours** eng+content hybrid  
- **Full tracked backlog (P0–P2):** ≈ **300 hours**  
- **With AI leverage (drafting/codegen):** wall-clock can compress ~30–40%, but **QA + publish + CWV** still human-bound  
- **Team assumption:** 1–2 focused engineers + content QA ≈ **15–25 h/week** → P0 fits; full backlog is tight

### چند هزار خط کد احتمالاً تغییر می‌کند؟
- P0 path: **~8–15k LOC** net churn (FE heavy)  
- Full path incl. knowledge graph: **~20–40k LOC**

### چند فایل باید ایجاد یا ویرایش شود؟
- P0: **~60–120 files**  
- Full: **~150–250 files** (incl. content markdown/MDX)

### چند مقاله باید نوشته شود؟
- **24** buyer-intent articles to checkpoint (SEO-003) — realistic quality bar  
- **Not** hundreds; mid-tail clusters beat thin volume for «کولیس» head terms

### چند اسکیما باید اضافه شود؟
- **8–12** JSON-LD types/patterns: `Organization`, `WebSite`, `BreadcrumbList`, `Product`, `Offer`, `AggregateRating` (if real), `FAQPage`, `ItemList`, `Article`, `CollectionPage`

### چند تست باید نوشته شود؟
- **25–50** automated cases (API contract + storefront unit/e2e smoke for SEO/CWV-critical paths)

### آیا رسیدن به «بهترین حالت ممکن سایت» تا ۳۱ شهریور واقع‌بینانه است؟
- **بله برای:** فروشگاه پایدار، UX قوی، CWV قابل قبول، SEO foundation، ۲۴ مقالهٔ باکیفیت، schema درست، catalog hygiene  
- **خیر برای:** رنک ۱ گوگل روی «کولیس» / «ابزار تراش»، knowledge platform کامل، صفر tech debt، همه enrichment برندها

### اگر نیست — اولویت تا checkpoint / فاز بعد

**Keep (P0) to 31 Shahrivar**
- [x] SEO-001 Schema Product/Offer/Breadcrumb (#88)
- [x] SEO-002 Hub intros + internal links (#91)
- [ ] SEO-003 24 articles
- [x] SEO-004 Technical SEO hygiene (#94)
- [x] UX-002 PDP specs/trust (#96)
- [x] PERF-001 CWV home/PDP/PLP (#99)
- [ ] REL-001 Release freeze

**Move to بعد از ۳۱ شهریور (P2+)**
- [ ] KB-001 Knowledge graph phase-1
- [ ] Broad brand enrichment beyond content-safe merges
- [ ] Design-system mega-refactor
- [ ] Rank-chasing for head terms as primary KPI

## Current portfolio snapshot
- Live: homepage mega/hero, taxonomy metrology promote, admin megamenu controls, SEO short_description plumbing
- Open historically: enrichment PRs, workflow #81, INSIZE apply paused

## Decision
> Checkpoint KPI = **quality + indexable mid-tail + CWV**, not **#1 head-term rank**.
