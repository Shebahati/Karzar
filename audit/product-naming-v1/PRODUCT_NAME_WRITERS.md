# Product Name Writers — Inventory (Phase 0/1)

**Status:** Proposed audit artifact (read-only)  
**Scope:** Every path that can create or mutate `products.name`  
**Non-claim:** Does not authorize APPLY, production writes, or Board Acceptance.

Classification legend:

| Class | Meaning |
|-------|---------|
| **A — Interactive admin** | Human enters free-text name via UI/API |
| **B — Catalog importer** | Bulk create/update from external catalogs |
| **C — Remediation / rebuild** | Corrective renames against live or planned catalog |
| **D — Seed / legacy bootstrap** | Dev or one-shot seed paths |
| **E — Name builder helper** | Builds candidate name strings for later import (may not write DB itself) |

---

## 1. Interactive admin (Class A)

| Writer | Path | How name is set | Notes |
|--------|------|-----------------|-------|
| Admin product form | `frontend/admin-panel/src/features/catalog/product-schema.ts:175` (zod `name`), `:342` (`toProductCreatePayload`) | Free string, trim, max 255 | No naming engine; no manufacturer_code field |
| Admin create API | `app/api/endpoints/products_admin.py` → `ProductCreate` | Pass-through | Schema: `app/schemas/product.py` (`ProductCreate.name`) |
| CRUD create | `app/crud/product.py:41-58` | Persists `name`; **slug generated from name/sku at create only** (`:47-55`) | |
| CRUD update | `app/crud/product.py:303-318` | `setattr` for any unset fields including `name` | **Does not regenerate `slug`** on rename (`NAME_CHANGE_CAUSES_SLUG_CHANGE = NO`) |

---

## 2. Catalog importers (Class B)

| Writer | Path | How name is set | Brand / source |
|--------|------|-----------------|----------------|
| ShopMill INSIZE sync | `scripts/shopmill_insize_sync.py:361` (PUT update), `:383` (POST create) | Reseller crawl `row["name"][:255]` | INSIZE via ShopMill |
| Mitutoyo import | `scripts/mitutoyo_import.py:221` | CSV/source `row["name"][:255]` | Mitutoyo |
| Azarsanat import | `scripts/azarsanat_import.py:654` | Source name with HTML entity cleanup | Multi-brand reseller |
| ZCC.IR import planner | `scripts/zcc_ir_import.py:90` | `name_fa` into CREATE payload | ZCC.CT / related |
| ZCC Category-B draft | `scripts/zcc_ir_category_b_draft_import.py:103-106` | `record["name"]` into draft payload | Category B; inactive drafts |
| CSV seed import | `scripts/seed_products_from_csv.py:345-348` | ORM `Product(name=row["name"][:255])` | Generic CSV |

All of the above treat **source title as canonical name**, not structured Type+Brand+OEM → engine.

---

## 3. Remediation / rebuild (Class C)

| Writer | Path | How name is set | Notes |
|--------|------|-----------------|-------|
| Catalog remediation | `scripts/catalog_remediation.py:551`, `:556` | PUT cleaned / garbage-fixed names | Heuristic cleanup, not v1 grammar |
| Official INSIZE rebuild | `scripts/catalog_target/official_insize_rebuild.py:484` (payload), `:565` (`UPDATE … SET name = %s`) | `proposed_name` from official rebuild plan | Category B / gated; identity-aware but pre-dates naming engine |
| Rebuild plan builder | `scripts/build_insize_official_rebuild_plan.py` (companion) | Writes plan CSV including `proposed_name` | Plan artifact only until apply |

---

## 4. Name builders / price-list parse (Class E → feeds B)

| Writer | Path | Role |
|--------|------|------|
| Price-list PDF parser | `scripts/parse_price_list_pdfs.py:267-277` (`build_name`), rows carry `name` | Assembles description + size into a title string for downstream CSV/import — **not** Karzar naming grammar |

---

## 5. Startup / seed legacy (Class D)

| Writer | Path | How name is set |
|--------|------|-----------------|
| Local catalog bootstrap | `app/core/startup.py:94-97` | Hard-coded DEV sample `اینسرت نمونه توسعه (DEV)` when DB empty |

Not a production naming authority.

---

## 6. Implications for Naming Standard v1

1. **Many writers, one free string.** No shared grammar today → bilingual brand dumps, `مدل` vs `کد`, marketing/reseller wording drift.
2. **Slug stability is already correct for renames** (`app/crud/product.py` update path) — naming APPLY must keep that invariant (ADR-010).
3. **Phase 2+ target:** importers emit structured fields → `build_product_name_v1` → `products.name`; interactive admin shows preview (SPEC §15 Mode B).
4. **Phase 0/1:** this inventory + `scripts/audit_product_naming_v1.py` are **read-only**. Do not wire writers to the engine yet.

---

## 7. Explicit non-writers (out of scope for name mutation)

- Enrichment scripts that touch descriptions/images/specs without renaming (still ADR-012 bounded).
- Hesabfa item push (`app/services/hesabfa/item_push.py`) — **reads** `product.name` for accounting sync; does not author storefront titles.
- Storefront display components — consume API `name`; do not write.

---

*Generated for Phase 0/1 Product Naming Standard audit. Cite paths when proposing writer cut-over.*
