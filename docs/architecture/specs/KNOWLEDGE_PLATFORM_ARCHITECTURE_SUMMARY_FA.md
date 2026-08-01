---
id: KNOWLEDGE-PLATFORM-ARCHITECTURE-SUMMARY-FA
version: 0.1.0
status: Proposed
date: 2026-07-31
locale: fa
owner: Platform Architect
task_id: KB-001
pack: docs/architecture/specs/README.md
sources:
  - docs/architecture/specs/README.md
  - docs/architecture/specs/FULL_PLATFORM_ARCHITECTURE_AUDIT.md
  - docs/architecture/specs/FOUNDATION_ARCHITECTURE_REVIEW.md
  - docs/architecture/specs/SPEC-product-knowledge-entity-model.md
  - docs/architecture/specs/SPEC-industrial-taxonomy-model.md
  - docs/architecture/specs/SPEC-knowledge-graph-model.md
  - docs/architecture/specs/SPEC-product-import-enrichment-playbook.md
  - docs/architecture/specs/SPEC-domain-model.md
  - docs/architecture/specs/SPEC-property-dictionary-system.md
  - docs/architecture/specs/SPEC-industrial-taxonomy-master-seed.md
  - docs/architecture/specs/SPEC-knowledge-graph-registry.md
  - docs/architecture/specs/SPEC-data-transformation-architecture.md
  - docs/architecture/specs/KNOWLEDGE_PLATFORM_TARGET_ARCHITECTURE.md
  - docs/architecture/specs/FOUNDATION_IMPLEMENTATION_READINESS.md
---

# خلاصه دقیق معماری پلتفرم دانش کارزارتولز

**وضعیت:** پیشنهادی (Proposed) — هنوز Canon Lock / Accepted نیست  
**مخاطب:** هیئت معماری، مالک محصول، مهندسی  
**هدف این سند:** یک صفحهٔ مرجع فشرده از کل پک بنیاد دانش، بدون جایگزینی اسناد اصلی

---

## ۱. حکم یک‌خطی

کارزارتولز امروز یک **کاتالوگ تجارت صنعتی بالغ** است. برای تبدیل‌شدن به **پلتفرم دانش صنعتی** (در مقیاس Grainger / RS / Mitutoyo) باید لایهٔ دانش را **روی** سیستم فعلی اضافه کرد — نه جایگزین جداول تجارت، نه درخت دسته‌بندی دوم فروشگاهی.

---

## ۲. آنچه الان واقعاً وجود دارد (از کد)

| لایه | واقعیت مخزن |
|------|-------------|
| محصول تجارت | جدول `products`: SKU، slug، قیمت، موجودی/قابلیت فروش، JSONB مشخصات |
| دسته | درخت `categories` (حداکثر عمق ۳) + پرچم‌های مگامنو |
| برند | جدول `brands` — **سازنده جدا نیست** |
| محتوا | `articles` با لینک نرم `related_product_ids` |
| مشخصات فنی | JSONB آزاد + قالب‌های ادمین در کد (`spec_template_service`) |
| دانش | **وجود ندارد:** نه `app/knowledge/`، نه `/api/v1/knowledge/*` |
| SEO (Storefront) | `/product/{slug}`، `/categories/{slug}`، `/brands/{slug}` عمدتاً پیاده شده |
| ورود داده | اسکریپت‌های زیاد + سیاست ADR-012 (نوشتن روتین فقط لوکال) |

---

## ۳. تفکیک اجباری: تجارت ≠ دانش

| محصول تجارت (Commerce Product) | موجودیت دانش محصول (PKE) |
|--------------------------------|---------------------------|
| قیمت، مالیات، موجودی، سفارش‌پذیری | معنا، کلاس صنعتی، کاربرد |
| انبار / Hesabfa | مشخصات حکمرانی‌شده (Fact) |
| قرارگیری در Category فروشگاهی | روابط، استاندارد، آموزش |
| CTA خرید/استعلام | ماژول‌های دانش (overview، how-to، FAQ، …) |

**سازنده ≠ برند.** مثال: Manufacturer = Mitutoyo Corporation ؛ Brand = Mitutoyo ؛ SKU = 500-196-30 ؛ Model = CD-6 ASX.

---

## ۴. ستون فقرات معماری (وابستگی)

```text
موجودیت دانش محصول (PKE)
        │
        ▼
طبقه‌بندی صنعتی چندبُعدی (Taxonomy)
        │
        ▼
گراف دانش (Nodes + Edges + Provenance)
        │
        ▼
خط لوله ورود و غنی‌سازی (Import / Enrichment)
```

---

## ۵. مدل دامنه (خلاصه موجودیت‌ها)

### تجارت (حفظ شود)
- **Product** — پیشنهاد فروش/استعلام SKU  
- **Category** — درخت فروشگاهی (تنها درخت مرچندایزینگ)  
- **Brand** — برند بازاری  

### دانش (افزودنی)
- **PKE** — معنای صنعتی محصول  
- **Manufacturer** — سازمان سازنده  
- **TaxonomyNode** — گره دامنه/خانواده/کاربرد/صنعت  
- **Specification Definition / Template / Fact** — فرهنگ ویژگی + مقدار + واحد + شواهد  
- **Knowledge Module** — محتوای آموزشی متصل به موجودیت  
- **Document / Evidence Source** — PDF و منبع اثبات  
- **Standard / Certification** — انطباق (فقط با Evidence قابل انتشار)  
- **Knowledge Edge** — یال تایپ‌شده با provenance  

---

## ۶. تاکسونومی صنعتی (نه Category دوم)

تاکسونومی دانش **چندبُعدی** است و به این سؤال‌ها جواب می‌دهد:

| سؤال | بُعد |
|------|------|
| این چیست؟ | Domain → Family → Type |
| برای چه؟ | Application |
| کجا؟ | Industry |

**دامنه‌های بذر:** Measurement، Cutting Tools، Toolholding، Workholding، Safety، Automation، Electrical، Lubrication، Machines  

**نمونه Measurement:** Calipers / Micrometers / Height Gauges / Indicators  
**نمونه Cutting:** Inserts / End Mills / Drills  

درخت `categories` فروشگاهی **جایگزین نمی‌شود**؛ فقط به Domainهای دانش **پل** می‌خورد (مثلاً L1 «اندازه‌گیری دقیق» → `dom.measurement`).  
مگامنو فقط نمایش روی ریشه‌های L1 است (**D1**) — تاکسونومی نیست.

---

## ۷. سیستم فرهنگ ویژگی (Property Dictionary)

```text
Definition (مثلاً accuracy)
    → داخل Template (مثلاً Caliper Template)
        → Fact روی PKE: مقدار + واحد + وضعیت + منبع
```

- کلید کاننیکال انگلیسی (`measurement_range`)؛ برچسب FA/EN جدا  
- aliasهای فارسی/انگلیسی قدیمی (`دقت` / `accuracy`) به **یک** Definition می‌ریزند  
- JSONB فعلی تا تأیید Board برای dual-write **عملیاتی می‌ماند** (strangler)  
- AI حق **اختراع** عدد مشخصات / استاندارد / گواهی / قیمت را ندارد  

---

## ۸. گراف دانش (خلاصه یال‌های رسمی)

| یال | معنی | انتشار |
|-----|------|--------|
| `PRODUCT_BELONGS_TO_CATEGORY` | قرارگیری فروشگاهی | projection از DB |
| `PRODUCT_BRANDED_AS` | برند | projection |
| `PRODUCT_MANUFACTURED_BY` | سازنده | steward |
| `PRODUCT_CLASSIFIED_AS` | گره تاکسونومی دانش | برچسب‌های بسته |
| `PRODUCT_USED_FOR` / `USED_IN` | کاربرد / صنعت | پیشنهاد AI → بازبینی |
| `PRODUCT_COMPATIBLE_WITH` | سازگاری/لوازم | شواهد برای ایمنی |
| `PRODUCT_SIMILAR_TO` / `ALTERNATIVE_TO` | مشابه / جایگزین خرید | بدون auto-publish تجاری کور |
| `ARTICLE_EXPLAINS_PRODUCT` | مقاله توضیح می‌دهد | از `related_product_ids` |
| `PRODUCT_HAS_DOCUMENT` | دیتاشیت/کاتالوگ | checksum OEM ترجیح |
| `PRODUCT_MEETS_STANDARD` / `HAS_CERTIFICATION` | انطباق | **فقط با Evidence** |
| `FACT_SUPPORTED_BY` | شواهد Fact | شرط publish حساس |

گراف = **overlay منطقی** روی Postgres؛ جایگزین سبد/سفارش نیست.

---

## ۹. خط لوله داده

```text
داده تأمین‌کننده
 → Raw Deposit (checksum)
 → Validation
 → Normalization (SKU/مدل/برند/واحد)
 → Entity Resolution (جدید یا موجود؟)
 → Classification (Category + Taxonomy)
 → Property Mapping
 → Fact Creation
 → Graph Edges
 → Human Review (Low / Medium / High)
 → Production (Cat A لوکال → Cat B کنترل‌شده)
```

**AI مجاز:** طبقه‌بندی در برچسب بسته، پیش‌نویس متن، پیشنهاد رابطه  
**AI ممنوع:** اختراع مشخصات فنی، استاندارد، گواهی، قیمت؛ نوشتن production به‌عنوان Cat A

---

## ۱۰. صفحه محصول هدف (PDP)

`/product/{slug}` ثابت می‌ماند (ADR-010).

| بخش صفحه | منبع |
|----------|------|
| قیمت، موجودی، خرید/استعلام | تجارت |
| جدول مشخصات قابل‌مقایسه | Factهای published (یا JSONB موقت) |
| آموزش / FAQ / کاربرد | Knowledge Modules + مقالات |
| لوازم / جایگزین / مشابه | یال‌های گراف |
| استاندارد و گواهی | فقط با Evidence |
| Brand / Category | هاب‌های `/brands/{slug}` و `/categories/{slug}` |

اسلات خالی PDF/لوازم باید صادقانه خالی بماند — پر کردن جعلی ممنوع.

---

## ۱۱. آمادگی پیاده‌سازی (حکم مهندسی)

| کار | حکم |
|-----|-----|
| برنامه‌ریزی و spike پشت flag | آماده |
| DDL جداول دانش | بعد از Accept هیئت + ADR هویت/ذخیره (UD-02/05/06) |
| API `/knowledge/*` | بعد از همان + RFC قرارداد OpenAPI |
| ادمین دانش | بعد از بذر Dictionary و نقش steward |
| رسمی‌سازی import لوکال | بله، زیر ADR-012 |
| AI enrichment | فقط assist |
| هاب SEO نوع ابزار / کاربرد | **مسدود** تا UD-04 |
| KB-001 seed گراف حداقلی | با شرط: فقط یال‌های registry، بدون Category DAG دوم |

---

## ۱۲. تصمیم‌های باز که انسان باید بگیرد

| شناسه | سؤال |
|-------|------|
| **UD-01** | جداسازی Manufacturer از Brandهای فعلی چگونه مهاجرت شود؟ |
| **UD-02** | شناسه پایدار PKE: UUID جدا یا فعلاً `products.id`؟ |
| **UD-03** | بذر اول Dictionary فقط مترولوژی یا همه دامنه‌ها؟ |
| **UD-04** | آیا هاب عمومی Type/Application ایندکس می‌شود؟ با چه URL؟ |
| **UD-05** | ذخیره یال/Fact: فقط جدول رابطه‌ای یا بعداً موتور گراف؟ |
| **UD-06** | Accept این پک در Canon Lock؟ |
| **UD-07** | ارتقا به مسیرهای تاریخی `domain/` / `pim/` / `knowledge-graph/`؟ |
| **UD-08** | پیش‌نویس فارسی AI آیا هرگز auto-publish می‌شود؟ (پیشنهاد: خیر) |

---

## ۱۳. توالی پیشنهادی بعد از Accept

1. Accept هیئت + ردیف Canon Lock  
2. ADR سازنده / هویت PKE / ذخیره Edge+Fact  
3. KB-001: projection یال‌های Article↔Product↔Category  
4. بذر Git فرهنگ ویژگی مترولوژی (بدون dual-write)  
5. بارگذاری Taxonomy seed + نقشه طبقه‌بندی یک برند  
6. ادمین خواندن/ثبت Fact  
7. PDP مصرف Factهای published پشت flag  
8. فقط بعداً RFC dual-write و هاب‌های دانش جدید  

---

## ۱۴. فهرست اسناد کامل پک

| سند | نقش |
|-----|-----|
| `README.md` | فهرست + تحلیل اولیه + UDها |
| `FULL_PLATFORM_ARCHITECTURE_AUDIT.md` | ممیزی as-built |
| `FOUNDATION_ARCHITECTURE_REVIEW.md` | نقد foundation |
| `SPEC-product-knowledge-entity-model.md` | مدل PKE |
| `SPEC-industrial-taxonomy-model.md` | مدل تاکسونومی |
| `SPEC-knowledge-graph-model.md` | مدل گراف |
| `SPEC-product-import-enrichment-playbook.md` | پلی‌بوک ورود |
| `SPEC-domain-model.md` | ER دامنه |
| `SPEC-property-dictionary-system.md` | فرهنگ ویژگی |
| `SPEC-industrial-taxonomy-master-seed.md` | بذر گره‌ها |
| `SPEC-knowledge-graph-registry.md` | واژگان یال |
| `SPEC-data-transformation-architecture.md` | معماری تبدیل داده |
| `KNOWLEDGE_PLATFORM_TARGET_ARCHITECTURE.md` | معماری هدف + PDP |
| `FOUNDATION_IMPLEMENTATION_READINESS.md` | آمادگی پیاده‌سازی |
| **این سند** | خلاصه اجرایی فارسی |

PRها: foundation [#167](https://github.com/Shebahati/Karzar/pull/167) · completion [#168](https://github.com/Shebahati/Karzar/pull/168)

---

## ۱۵. اصول غیرقابل‌مذاکره

1. گسترش دسته بدون redesign اسکیما (گره + قالب، نه DDL شکل تاکسونومی)  
2. جداسازی تجارت و دانش  
3. هویت SEO پایدار (ADR-010)  
4. مقیاس هزاران محصول / میلیون‌ها رابطه  
5. AI کمکی + دقت انسانی  
6. بدون معماری مبتنی بر free-text کنترل‌نشده  
7. سازگاری آینده با PIM/KG  
8. بدون درخت Category فروشگاهی دوم  
9. بدون self-Accept به Canon Lock  
10. بدون تضعیف ADR-012 / نوشتن production روتین
