# Karzar Product Status Report — 2026-09-24

**Snapshot time (UTC):** 2026-09-24T07:43:42Z
**PRODUCTION_IDENTITY_PROVEN:** YES
**READ_ONLY_PROVEN:** YES
**PRODUCTION MUTATION:** NO

## Executive Summary

Live catalog holds **6536** products (1 soft-deleted). **1368** are storefront-visible; **716** are sellable (active + available + priced + real image).

| Metric | Current | Historical anchor | Δ |
| --- | ---: | ---: | ---: |
| live_products | 6536 | 6536 | +0 |
| active | 1585 | 1585 | +0 |
| visible | 1368 | 1368 | +0 |
| sellable | 716 | 716 | +0 |
| total_product_image_rows | 1492 | 1492 | +0 |

## Global Catalog Health

### Predicates (re-derived from current code)

```text
LIVE                 = deleted_at IS NULL
ACTIVE               = LIVE AND is_active
AVAILABLE            = LIVE AND is_available
PRICED               = LIVE AND base_price IS NOT NULL AND base_price > 0
IMAGED               = EXISTS non-placeholder product_images.image_url
API/STOREFRONT_VISIBLE = LIVE AND is_active AND IMAGED
PURCHASE_ELIGIBLE    = LIVE AND is_active AND base_price IS NOT NULL
SELLABLE             = VISIBLE AND is_available AND PRICED
```

- products (live): 6536
- active / inactive: 1585 / 4951 (24.3%)
- available / unavailable: 3755 / 2781
- priced / unpriced / zero: 4552 / 1984 / 0
- original_price present / discounted: 7 / 7
- with_image / without: 1464 / 5072
- product_image_rows: 1492
- visible / not: 1368 / 5168
- sellable / not: 716 / 5820
- with_brand / brandless: 6241 / 295
- with_category / without: 6536 / 0
- with_product_type / without: 15 / 6521

### Identity

- database: `karzar_staging`
- user: `karzar_staging`
- alembic: `s2t3u4v5w6x7`
- APP_ENV: `staging`
- KARZAR_DATA_PLANE: `None`
- transaction_read_only: `on`

## Brand-by-Brand Status

See `KARZAR_BRAND_STATUS_2026-09-24.csv` for full metrics. Top brands by total:

| Brand | Total | Priced | Imaged | Avail | Active | Visible | Sellable | T0 | T1 | T2 | T3 | T4 | T5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ASTPOWER | ای اس تی پاور | 975 | 819 | 143 | 752 | 143 | 143 | 83 | 0 | 975 | 0 | 0 | 0 | 0 |
| INSIZE | اینسایز | 872 | 487 | 643 | 159 | 643 | 643 | 159 | 1 | 856 | 0 | 0 | 15 | 0 |
| Dasqua | داسکوا | 727 | 727 | 53 | 488 | 270 | 53 | 31 | 72 | 655 | 0 | 0 | 0 | 0 |
| ZCC.CT | زد سی‌سی | 583 | 258 | 247 | 175 | 175 | 175 | 175 | 0 | 583 | 0 | 0 | 0 | 0 |
| TIGER TEC | تایگرتک | 517 | 517 | 0 | 517 | 0 | 0 | 0 | 0 | 517 | 0 | 0 | 0 | 0 |
| YOWAX | یواکس | 353 | 350 | 0 | 350 | 0 | 0 | 0 | 0 | 353 | 0 | 0 | 0 | 0 |
| Chumpower | چام‌پاور | 347 | 315 | 0 | 315 | 0 | 0 | 0 | 0 | 347 | 0 | 0 | 0 | 0 |
| SAN OU | سانو | 317 | 141 | 86 | 85 | 62 | 62 | 22 | 0 | 317 | 0 | 0 | 0 | 0 |
| TERMA | ترما | 312 | 312 | 181 | 308 | 181 | 181 | 177 | 0 | 312 | 0 | 0 | 0 | 0 |
| Mitutoyo | میتوتویو | 304 | 190 | 111 | 174 | 111 | 111 | 69 | 0 | 304 | 0 | 0 | 0 | 0 |
| [NO BRAND] | 295 | 7 | 0 | 7 | 0 | 0 | 0 | 0 | 295 | 0 | 0 | 0 | 0 |
| ASIMETO | آسیمتو | 235 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 235 | 0 | 0 | 0 | 0 |
| ET | ای تی | 227 | 221 | 0 | 221 | 0 | 0 | 0 | 0 | 227 | 0 | 0 | 0 | 0 |
| Mighty Seven | مایتی سون | 182 | 182 | 0 | 182 | 0 | 0 | 0 | 0 | 182 | 0 | 0 | 0 | 0 |
| Groz | گروز | 127 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 127 | 0 | 0 | 0 | 0 |
| Chagan | چاگان | 27 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 27 | 0 | 0 | 0 | 0 |
| SHAMS | شمس | 27 | 26 | 0 | 22 | 0 | 0 | 0 | 8 | 19 | 0 | 0 | 0 | 0 |
| Winstar | وینستار | 21 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 0 | 0 | 0 | 0 |
| MPA | ام پی ای | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 0 | 0 | 0 | 0 |
| Transmex | ترنمکس | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 0 | 0 |
| 3Keego | کیگو | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 |
| Vertex | ورتکس | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 |
| Viyer | ویر | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 |
| ZPS | زد پی‌اس | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 |
| Narex | نارکس | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |

## Commercial Readiness

Sellable now: **716**. One-field unlocks: **330**. Two-field unlocks: **3659**.

One-field blocker breakdown:
- availability: 330

## Price Coverage

Priced 4552 (69.6%); unpriced 1984; zero/invalid 0.
Inverted original_price < base_price rows: 0.
Extreme outliers reported: 0 (see SUMMARY.json).

## Image Coverage

DB image rows: 1492
Products with real image: 1464
Referenced files present/missing (probed): 1464 / 0
Unreferenced media files: 32

## Availability

Available 3755 / unavailable 2781.

## Activation / Visibility / Sellability

Active 1585; visible 1368; sellable 716.

## Technical Specifications

Legacy specs present: 6455 (98.8%).
Legacy JSON presence ≠ authoritative technical completeness.

## Knowledge Base Coverage

- KB facts present: 15
- Product type assigned: 15
- Required KB complete: 15
- Required KB evidenced: 15
- Conflict/review (T5): 0

## Content Completeness

See brand CSV columns `with_description` / `with_short_description`.

## Category Health

Top categories by product count:
- سه نظام و لوازم جانبی: 571
- اینسرت تراش CNC: 448
- انواع کولیس: 446
- انواع میکرومتر: 440
- ساعت اندیکاتور: 326
- انگشتی سرتخت کارباید: 270
- مته کارباید(الماس): 260
- قلاویز ماشینی صاف: 255
- انواع گیج: 244
- اینسرت فرز CNC: 213
- دستگاه کُر گیری (کُر دریل): 199
- ابزار دستی عمومی: 196
- متر: 152
- دستگاه ابزار تیزکن: 137
- عمق سنج: 132
- انگشتی سر گرد کارباید(بال نوز): 111
- رو تراش: 107
- زاویه سنج: 98
- اینسرت رزوه‌زنی: 98
- کولت BT و فشنگی و آچار: 97

## SKU / Identity Integrity

- Exact duplicate SKU groups: 0
- Case-insensitive collision groups: 0
- Trim-normalized collision groups: 0
- Empty SKU: 0
- Cross-brand dups: 0
- UFR-L02 / UFR/L02 suspect present: 2 [{'id': 3142, 'sku': 'UFR-L02', 'brand_id': None}, {'id': 6217, 'sku': 'UFR/L02', 'brand_id': 13}]

## INSIZE

- total: 872 (historical DB 872, Δ +0)
- active / available / priced / imaged: 643 / 159 / 487 / 643
- visible / sellable: 643 / 159 (historical visible 643, sellable 159)
- legacy / KB / PT / req complete / evidenced: 871 / 15 / 15 / 15 / 15
- maturity T0–T5: 1/856/0/0/15/0

## ZCC.CT

- total: 583 (historical 583, Δ +0)
- active / available / priced / imaged / visible / sellable: 175 / 175 / 258 / 247 / 175 / 175
- historical active cohort 7116–7290: {'total': 175, 'priced': 175, 'unpriced': 0, 'imaged': 175, 'unimaged': 0, 'available': 175, 'active': 175, 'visible': 175, 'sellable': 175}
- historical draft cohort 7291–7599: {'total': 309, 'priced': 0, 'unpriced': 309, 'imaged': 0, 'unimaged': 309, 'available': 0, 'active': 0, 'visible': 0, 'sellable': 0}
- SAFE_CREATE wave resolution: `ZCC_id_gt_7599_actual_n=99` → {'total': 99, 'priced': 83, 'unpriced': 16, 'imaged': 72, 'unimaged': 27, 'available': 0, 'active': 0, 'visible': 0, 'sellable': 0}
  Historical expected after waves: total=135 priced=113 unpriced=22 imaged=96 unimaged=39 available=0 active=0 visible=0 sellable=0
  **DIVERGENCE:** total: current=99 expected=135; priced: current=83 expected=113; unpriced: current=16 expected=22; imaged: current=72 expected=96; unimaged: current=27 expected=39

## SAN OU

- total: 317 (historical 317, Δ +0)
- active / priced / imaged / available / visible / sellable: 62 / 141 / 86 / 85 / 62 / 22

## STC

STC products = 0 (matches historical expectation).

## Brandless Products

- count: 295 (historical ~295, Δ +0)
- active / available / priced / imaged / visible / sellable: 0 / 7 / 7 / 0 / 0 / 0
- sample SKUs/names:
  - 311-12-0: کولیس فک بلند ( مونو بلاک ) سری 311
  - 360: دستگاه قلاویز زن برقی موتور سرو NC
  - 364: ماشین قلاویز زن برقی بازویی موتور سرو (NC – Servo)
  - 483: قلاویز ماشینی مستقیم فرم B
  - 484: قلاویز ماشینی مارپیچ سر تخت 35 درجه میلیمتری
  - 485: قلاویز ماشینی مارپیچ نوک تیز 35 درجه میلیمتری
  - 486: قلاویز ماشینی مستقیم فرم C میلیمتری
  - 487: قلاویز ماشینی فرمینگ ( باکالیت )
  - 51609-16-18LH: قلاویز ماشینی مارپیچ UNF اینچی
  - 489: قلاویز ماشینی BSW مستقیم اینچی
  - 490: قلاویز ماشینی مخصوص چدن ( چهارپر )
  - 491: قلاویز ماشینی مارپیچ سر تخت 15 درجه میلیمتری
  - 492: قلاویز ماشینی مستقیم PM میلیمتری
  - 906: حدیده میلیمتری فرا یوگوسلاوی اصل
  - 908: حدیده Tr فرا یوگوسلاوی اصل

## Highest-Impact Gaps

- Become sellable with 1 missing field: 330
  by field: {'availability': 330}
  top brands: [('INSIZE | اینسایز', 226), ('ASTPOWER | ای اس تی پاور', 53), ('SAN OU | سانو', 24), ('Dasqua | داسکوا', 22), ('TERMA | ترما', 4), ('Mitutoyo | میتوتویو', 1)]
- Become sellable with 2 missing fields: 3659
- Active blocked by image: 217
- Active blocked by price: 322
- Priced+imaged blocked only by availability: 330
- Sellable but technically weak (not T3/T4): 706

## Recommended Next Waves

1. **One-field activation unlocks** — activate products already available+priced+imaged.
2. **One-field availability unlocks** — confirm Hesabfa/supplier stock for active+priced+imaged.
3. **Image backfill** for active+priced products missing real images.
4. **Price backfill** for active+imaged products.
5. **KB enrichment** for currently sellable SKUs still in T0/T1/T2.

Do NOT execute changes from this report. READ-ONLY audit only.

## Current vs Historical

| metric | previous | current | delta | reason/evidence |
| --- | ---: | ---: | ---: | --- |
| live products | 6536 | 6536 | +0 | recount from Production snapshot; cause not attributed without change log |
| active | 1585 | 1585 | +0 | recount from Production snapshot; cause not attributed without change log |
| visible | 1368 | 1368 | +0 | recount from Production snapshot; cause not attributed without change log |
| sellable | 716 | 716 | +0 | recount from Production snapshot; cause not attributed without change log |
| image rows | 1492 | 1492 | +0 | recount from Production snapshot; cause not attributed without change log |
| ZCC.CT | 583 | 583 | +0 | recount from Production snapshot; cause not attributed without change log |
| SAN OU | 317 | 317 | +0 | recount from Production snapshot; cause not attributed without change log |
| INSIZE | 872 | 872 | +0 | recount from Production snapshot; cause not attributed without change log |
| brandless | 295 | 295 | +0 | recount from Production snapshot; cause not attributed without change log |

## Artifacts

- `audit/KARZAR_PRODUCT_STATUS_REPORT_2026-09-24.md`
- `audit/KARZAR_BRAND_STATUS_2026-09-24.csv`
- `audit/KARZAR_PRODUCT_STATUS_MASTER_2026-09-24.csv`
- `audit/KARZAR_COMMERCIAL_GAPS_2026-09-24.csv`
- `audit/KARZAR_TECHNICAL_GAPS_2026-09-24.csv`

