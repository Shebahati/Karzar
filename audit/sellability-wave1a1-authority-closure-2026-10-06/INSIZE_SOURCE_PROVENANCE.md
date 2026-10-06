# INSIZE Source Provenance — Wave 1A.1

## Question

Wave 1A interpreted filename `11 شهریور` as Jalali **1405-06-11 → 2026-09-02**.
Is the year independently proven?

## Evidence searched

- Wave 1A `SOURCE_MANIFEST.json` / `SOURCE_INVENTORY.csv` (explicitly notes year was resolved from operational context — a guess)
- Local root `/home/shebahati/KaZar` + `Product and Data Complete/اندازه گیری/اینسایز/`
- `DOCS/Price/` workbook variants (20%, 12%, rial-format)
- Dirty-tree audit copies `audit/insize-price-20-workbook/WORKBOOK_65a92337.xlsx` (SHA256=`65a92337…` = root 20% file)
- OOXML `docProps/core.xml` for primary + variants
- Filename / SHA256 cross-compare to Wave 1A primary `8cecb478…`

## SHA256 results (selected)

| File | SHA256 | vs Wave 1A primary |
| --- | --- | --- |
| `…/موجودی توزیع کننده 11 شهریور (2).xlsx` | `8cecb478a4e48166436b9c526ebace54430800925819e3e062e631ad56eee3a4` | SAME (Wave 1A primary) |
| root `… افزایش 20 درصدی.xlsx` | `65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a` | DIFFERENT content |
| audit `WORKBOOK_65a92337.xlsx` | `65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a` | copy of root 20% |

## OOXML metadata

Primary workbook `dcterms:modified` = `2026-09-03T09:08:31Z`; `dcterms:created` = `2015-06-05` (template noise).
Office modified timestamp is **not** accepted as document source-year proof (same plane as mtime prohibition).

## Verdict

```text
SOURCE_YEAR_UNPROVEN
```

No SHA256 record, manifest, workbook cell, or independent Owner citation found that
**proves** Jalali year 1405 for `11 شهریور`. Wave 1A date `2026-09-02` remains a
contextual guess and is **not** promoted to proven in Wave 1A.1.

## Newer stock than 2026-09-02?

All discovered INSIZE distributor inventory workbooks share the `11 شهریور` name
family (or price-format derivatives). No inventory authority with a **later
document source date** was found.

```text
LATEST_AUTHORITATIVE_INSIZE_STOCK=2026-09-02  # Wave 1A claimed date; year UNPROVEN
CURRENT_ENOUGH_SOURCE_AVAILABLE=NO
```

(As-of 2026-10-06; CURRENT_ENOUGH ≤14d would require a source dated ≥2026-09-22.)
