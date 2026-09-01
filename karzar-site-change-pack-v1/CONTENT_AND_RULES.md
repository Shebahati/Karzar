# Karzar content and business rules

This file is authoritative for this implementation batch.

## 1. Hero slides

All visible Persian copy must remain HTML. Never rasterize text, buttons, labels, icons, or the Karzar logo into the hero images.

| Slide key | Desktop asset | Mobile asset | Headline | Supporting text | CTA |
|---|---|---|---|---|---|
| special-offers | `assets/heroes/desktop/hero-special-offers.png` | `assets/heroes/mobile/hero-special-offers-mobile.png` | تخفیف‌های ویژه کارزار | فرصت‌های منتخب خرید ابزار و تجهیزات صنعتی | مشاهده تخفیف‌ها |
| precision-measurement | `assets/heroes/desktop/hero-precision-measurement.png` | `assets/heroes/mobile/hero-precision-measurement-mobile.png` | اندازه‌گیری دقیق | ابزارهای سنجش و کنترل ابعادی برای کارگاه و کنترل کیفیت | مشاهده ابزارهای اندازه‌گیری |
| workholding | `assets/heroes/desktop/hero-workholding.png` | `assets/heroes/mobile/hero-workholding-mobile.png` | ثبات کاری حرفه‌ای | راهکارهای دقیق مهار قطعه برای ماشین‌کاری مطمئن و پایدار | مشاهده ابزارهای گیرشی |
| carbide-inserts | `assets/heroes/desktop/hero-carbide-inserts.png` | `assets/heroes/mobile/hero-carbide-inserts-mobile.png` | اینسرت کاربیدی | انتخاب هندسه و گرید متناسب با جنس قطعه و عملیات ماشین‌کاری | مشاهده اینسرت‌ها |
| indexable-tools | `assets/heroes/desktop/hero-indexable-tools.png` | `assets/heroes/mobile/hero-indexable-tools-mobile.png` | ابزارهای اینسرتی | هلدرها و سیستم‌های تعویض‌پذیر برای تراش و فرز | مشاهده ابزارهای اینسرتی |
| cnc-machines | `assets/heroes/desktop/hero-cnc-machines.png` | `assets/heroes/mobile/hero-cnc-machines-mobile.png` | ظرفیت کارگاه را ارتقا دهید | دستگاه‌ها و تجهیزات صنعتی برای توسعه تولید | مشاهده دستگاه‌ها |

CTA destinations must be resolved from existing routes/category records. Do not invent slugs.

## 2. Global navigation labels

- Replace the visible label `درباره` with `درباره ما` in the desktop header, mobile navigation, footer, breadcrumb where appropriate, and accessibility labels.
- Replace the visible label `تماس` with `تماس با ما` in the same surfaces.
- Do not change canonical route paths solely for this label update.

## 3. About-us page: exact approved copy

Remove the entire statistics/brand-overview block, including:

- `نمای کلی برند — آمار رسمی داشبورد یا گزارش سروری نیست`
- `۱۲+ سال تجربه`
- `۸٬۰۰۰+ مشتری وفادار`
- `۵۰+ برند معتبر`
- `۱۰۰٪ ضمانت اصالت`

Remove the entire `مسیر ما` timeline and every year/history item.

The card is removed, but `ضمانت اصالت` remains a valid business claim elsewhere.

### Hero

Eyebrow:

`درباره ما`

H1:

`ابزار درست، در دستان حرفه‌ای‌ها`

Lead:

`کارزار فروشگاهی تخصصی برای انتخاب و تأمین ابزارآلات صنعتی، تراشکاری و اندازه‌گیری است. هدف ما این است که مسیر پیدا کردن ابزار مناسب، بررسی مشخصات، دریافت مشاوره و خرید برای صنعتگران، کارگاه‌ها و مجموعه‌های تولیدی روشن، دقیق و قابل‌اعتماد باشد.`

Primary CTA:

`مشاهده محصولات`

Secondary CTA:

`دریافت مشاوره`

Use the existing official Karzar logo from the repository. On desktop, place the logo visually opposite the H1 within the hero composition. On mobile, stack the logo and text with correct RTL flow, comfortable spacing, and no overlap.

### Section: انتخاب فنی، نه صرفاً خرید کالا

Heading:

`انتخاب فنی، نه صرفاً خرید کالا`

Body:

`در خرید ابزار صنعتی، نام محصول به‌تنهایی کافی نیست. نوع عملیات، جنس قطعه، دستگاه، دقت موردنیاز و شرایط کار تعیین می‌کند کدام انتخاب مناسب است. کارزار در کنار تنوع محصول، اطلاعات فنی و امکان دریافت مشاوره را فراهم می‌کند تا انتخاب بر اساس نیاز واقعی انجام شود.`

### Section: آنچه از کارزار دریافت می‌کنید

#### اصالت و کیفیت

`محصولات از نمایندگی‌ها و تأمین‌کنندگان معتبر تهیه می‌شوند و اصالت کالا در فرایند تأمین و فروش بررسی می‌شود.`

#### مشاوره تخصصی

`برای انتخاب ابزار، تجهیزات کارگاهی و طراحی یا توسعه خط تولید می‌توانید از راهنمایی فنی کارزار استفاده کنید.`

#### تأمین تجهیزات کارگاهی

`نیاز کارگاه، پروژه یا مجموعه تولیدی خود را اعلام کنید تا گزینه‌های مناسب از نظر مشخصات، زمان تأمین و شرایط خرید بررسی شوند.`

#### خرید سازمانی

`کسب‌وکارها و مجموعه‌های صنعتی می‌توانند برای خرید سازمانی، استعلام و پیگیری متمرکز درخواست همکاری ثبت کنند.`

#### پیش‌فاکتور رسمی

`امکان ثبت اقلام و دریافت پیش‌فاکتور رسمی، مسیر استعلام و خرید را برای واحدهای فنی و مالی شفاف‌تر می‌کند.`

#### ارسال سراسری

`سفارش‌ها با امکان ارسال به سراسر کشور و پیگیری فرایند تأمین و تحویل ارائه می‌شوند.`

### Closing CTA

Heading:

`برای تصمیم‌های فنی شما کنار کاریم`

Body:

`چه به‌دنبال جایگزینی یک ابزار مصرفی باشید، چه برای تجهیز کارگاه یا توسعه تولید برنامه‌ریزی کنید، کارزار مسیر بررسی، انتخاب و تأمین را یکپارچه می‌کند.`

Primary CTA:

`ورود به فروشگاه`

Secondary CTA:

`تماس با ما`

Do not add dates, founder stories, customer counts, years of experience, fabricated testimonials, awards, market-leadership claims, or numerical guarantees.

## 4. Contact information

Update contact information globally wherever business contact data is intended to appear: contact page, header or drawer where applicable, footer, support blocks, click-to-call links, JSON-LD/structured data, metadata, and shared configuration.

Landline display:

`۰۲۱ ۶۶۴۷ ۹۴۷۷`

Landline link:

`tel:+982166479477`

Mobile display:

`۰۹۹۱ ۲۴۸ ۰۰۸۷`

Mobile link:

`tel:+989912480087`

Contact page H1 and all navigation labels must use `تماس با ما`.

Do not remove the existing email, address, map, social links, or support form unless they are demonstrably broken. Preserve existing verified values.

## 5. Product availability ordering

The business has exactly two public availability states: `موجود` and `ناموجود`. Use the canonical existing model/enum/field after inspecting the backend; do not infer availability from price.

Rules:

1. On every public product collection, available products come before unavailable products.
2. This availability partition remains the primary order even when the user selects newest, oldest, cheapest, most expensive, popularity, discount, or any other supported sort.
3. The selected sort remains stable inside the available partition and separately inside the unavailable partition.
4. Apply the rule at the backend/query/service level where possible, not by re-sorting only the currently loaded frontend page.
5. Cover catalog, category, search, brand, homepage collections, discount lists, related products, and any other public product list.
6. Admin lists are not subject to this rule unless their existing UX explicitly uses storefront ordering.

## 6. Products without images

Products without a real public image must be hidden from the public storefront while remaining present and editable in the database and admin panel.

Treat as missing when the canonical primary/public image relation or URL is null/empty, or when the product uses a known generic placeholder. If the existing media system has a validated broken/failed status, treat that status as missing too. Do not perform a remote HTTP probe on every storefront request.

Hide such products from:

- public catalog/category/brand/search lists;
- homepage product collections;
- related/recommended products;
- public sitemap and product structured data;
- direct public product rendering, using the project's standard not-found/unavailable behavior without deleting the record.

When a valid public image is later assigned, the product should automatically become eligible for public display again. Do not set the database product itself inactive solely because its image is missing.

## 7. Sales metric

The admin dashboard `فروش` metric represents sales originating from this website only. The site has had no sale yet, so correct production-equivalent data should currently calculate to zero.

Do not hardcode zero and do not delete financial/order records. Compute the metric from website orders with successful/settled payment, net of cancelled/refunded transactions according to existing status semantics. Do not count imported Hesabfa turnover, quotes, abandoned carts, unpaid orders, failed payments, test fixtures, seed data, or manually created accounting records.

## 8. Open orders and open quotes

Repair backend endpoints and frontend consumers together. Derive open/closed status sets from canonical enums/workflow. An item is open only while actionable and not completed, rejected, cancelled, expired, fully refunded, or otherwise terminal. Do not silently swallow API errors or replace real values with zeros.

Move the navigation entries for orders and quotes under the admin group `فروش و مالی`; do not change their route identity merely to move the menu items.

## 9. Users and customers

Inspect the current `مشتریان` page and API.

- If it already includes every registered website account, including accounts with zero orders, do not create a duplicate `کاربران` module. Clarify the visible labeling/counts so this coverage is evident.
- If it excludes registered accounts with zero orders, add a `کاربران` page/API that lists all registered website accounts regardless of order history. Preserve `مشتریان` for customer/order-centric reporting.

Never expose password hashes, tokens, secrets, or excessive personal data. Respect existing admin authorization.

## 10. Abandoned carts

Create a separate admin view named `سبدهای رهاشده` under `فروش و مالی`; do not turn carts into orders and do not mix them into the order list.

Default rule:

- cart belongs to an authenticated registered user;
- cart contains at least one item;
- last cart activity is at least 24 hours old;
- cart has not converted into a successful order;
- cart has not been explicitly cleared or superseded.

Display only data already collected for legitimate account/cart operation: customer identity/contact available to the admin, item count, current computed value, last activity time, and cart detail. Do not add automated marketing messages, tracking pixels, guest fingerprinting, or new external communication.

## 11. Hesabfa disconnection and category mapping

The website–Hesabfa integration must be disabled for now.

Disconnection rules:

- no product, category, inventory, price, order, invoice, or customer writes to Hesabfa;
- no destructive remote API call;
- no remote product/category deletion or deactivation;
- products already sent from the site to Hesabfa must remain untouched in Hesabfa;
- preserve existing integration code, credentials configuration schema, remote ids, historical links, logs, and mapping records for a future controlled reconnection;
- scheduled sync jobs/workers must not run while disabled;
- use one explicit central feature flag/configuration gate rather than scattered ad-hoc conditions;
- default local/example configuration to disabled without committing real secrets.

Do not call the live Hesabfa API during this local implementation.

Category rules:

- website taxonomy remains independent;
- Hesabfa taxonomy remains completely unchanged;
- every website category may have exactly one default Hesabfa category reference;
- multiple website categories may point to the same Hesabfa category;
- an optional product-level Hesabfa category override may be used when a product must be placed differently from its website-category default;
- the product-level override wins over the category default;
- mappings are preserved while sync is disabled and must not trigger any remote mutation.

Activating products inside the live Hesabfa account is intentionally outside this local code execution. It requires a separate reviewed reconciliation/dry-run before any external write.

