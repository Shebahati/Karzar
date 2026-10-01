# Phase 2C source extraction profiles

Read-only deterministic extraction (`scripts/build_phase2c_source_authority_registry.py`).
No OCR; image-only PDFs do not produce BACKFILL_EXACT-eligible rows.

## INSIZE

| Field | Value |
|-------|--------|
| brand | INSIZE |
| source_id | `insize.product_list` |
| source file | `اندازه گیری/اینسایز/لیست محصولات.pdf` |
| authority tier | 1 |
| document semantics | OEM distributor product list (لیست فروش محصولات اینسایز) |
| OEM identity field | **کد کالا** (verified in document header) |
| locator | `source_page_index` + `source_row` (pdftotext line) |
| raw code | Matched token preserved exactly from PDF text |
| extraction_method | `pdftotext_layout_line_scan` |

## DASQUA

| Field | Value |
|-------|--------|
| brand | DASQUA |
| source_id | `dasqua.price_list` |
| source file | `اندازه گیری/داسکوا/لیست قیمت داسکوا +10 درصد.pdf` |
| authority tier | 2 |
| document semantics | Authorized supplier price list |
| identity column | **کد کالا** (Dasqua order/product code column — not internal Karzar SKU) |
| locator | page index + line number |
| mapping_basis | `supplier_price_list_order_code_verified_column` |

## TERMA

| Field | Value |
|-------|--------|
| brand | TERMA |
| source_id | `terma.price_list` |
| source file | `اندازه گیری/ترما/لیست قیمت ترما +25درصد.pdf` |
| authority tier | 2 |
| document semantics | Authorized supplier price list |
| identity column | **کد کالا** |
| locator | page index + line number |

## ASTPOWER

| Field | Value |
|-------|--------|
| brand | ASTPOWER |
| source_ids | `ast.spade`, `ast.electric_tapping`, `ast.automatic_tapping` |
| source files | Cooperation PDFs under `آذرصنعت/AST Power/` |
| authority tier | 3 (supplier cooperation) |
| OEM identity field | **Not proven** — prior `sku_column` / `ast_supplier_enumerator` semantics rejected |
| text layer | Image-only on hp-g2-450 (pdftotext empty); no deterministic codes |
| eligibility | `oem_identity_field_proven=false` → **excluded from BACKFILL_EXACT** |

## SKU join rule

SKU may join a Karzar product to an evidence row; SKU is not authority. Variant compatibility uses `source_item_description` vs local `name` when description exists.
