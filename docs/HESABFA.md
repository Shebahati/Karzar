# Hesabfa (حسابفا) Level-4 integration

## Scope (locked product decisions)

| Concern | Direction |
|---------|-----------|
| Catalog & prices | **Site is source of truth** — do not push catalog/prices site→Hesabfa as primary |
| Stock / warehouse counts | **Hesabfa only** — site never stores or displays numeric stock; only **موجود / ناموجود** (`is_available`) |
| Item shells | **Site → Hesabfa** create/upsert on product save + backfill (`ProductCode` = site `sku`, quantity fields omitted) |
| Item `active` | **Always true** for non-deleted catalog shells. Independent of site `is_active` and `is_available` |
| Contacts | One Hesabfa contact **per customer** (create/link on demand by phone) |
| Inquiry / proforma | **Not synced** |
| Sale invoice | Created in Hesabfa **after payment verify** (hook wired; skipped while `HESABFA_TEST_MODE=true`) |
| Admin metrics | **No Hesabfa numbers in admin** — website paid sales / availability only; never sales-summary or stock from Hesabfa |
| Categories | **Not synced** by default — shop IA ≠ accounting `nodeFamily`; match products by SKU only |

## Environment variables (VPS / `.env`)

Set these on the API host only (Compose env file or `/opt/karzar/.deploy-secrets`). **Never commit real keys.**

```bash
HESABFA_ENABLED=true
HESABFA_API_KEY=...
HESABFA_LOGIN_TOKEN=...
HESABFA_BASE_URL=https://api.hesabfa.com/v1
HESABFA_TIMEOUT_SECONDS=15
# true = invoice writes skipped; item push still allowed
HESABFA_TEST_MODE=true
# Admin must never consume Hesabfa reads (sales totals, stock, etc.)
HESABFA_ADMIN_READS_ENABLED=false
HESABFA_CURRENCY_UNIT=rial
HESABFA_CURRENCY_CODE=IRR
```

### Staging checklist

1. Add vars to API container on VPS `195.177.255.198`.
2. `alembic upgrade head` (hesabfa tables + `products.is_available`).
3. Keep `HESABFA_TEST_MODE=true` until verified.
4. Keep `HESABFA_ADMIN_READS_ENABLED=false` (default).
5. `POST /api/v1/hesabfa/items/push` creates a Hesabfa shell only when ProductCode lookup proves the item is missing. An already mapped item is left untouched. New shells are created active, independent of site publication state. Quantity fields are omitted. This endpoint is not an activation campaign (see below).
6. Zero any leftover `products.stock_quantity` from older Hesabfa pulls (`scripts/clear_hesabfa_pulled_stock.py`).
7. When gateway live: `HESABFA_TEST_MODE=false`.

## Admin API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/hesabfa/status` | Enabled / configured / test mode / `admin_reads_enabled` |
| POST | `/api/v1/hesabfa/mappings/sync` | Match site `sku` ↔ Hesabfa `ProductCode` |
| POST | `/api/v1/hesabfa/items/push` | Create missing Hesabfa shells for non-deleted site products. Already mapped items are not saved. New shells are active. Quantity fields omitted. Not an activation campaign. |
| POST | `/api/v1/hesabfa/stock/sync` | **Deprecated no-op** — Hesabfa→site quantity pull disabled |
| GET | `/api/v1/hesabfa/sales-summary` | **Website paid sales only** — Hesabfa fields always null |

## What admin must NOT show

- Hesabfa total sales / invoice counts
- Warehouse quantities or inventory value pulled from Hesabfa
- Any other Hesabfa-sourced metric widgets

Dashboard keeps **فروش وبسایت (پرداخت‌شده)** from local orders only.

## Item activation

Hesabfa item activation is independent of Karzar storefront activation.

This section is **policy**. It does not claim that every live Hesabfa item is currently active.

- Karzar `is_active` does not control Hesabfa `active`.
- Karzar availability (`is_available`) does not control Hesabfa `active`.
- Karzar soft delete does not delete or deactivate the Hesabfa item.
- A new Hesabfa item created by Karzar is created active.
- An already mapped Hesabfa item is not saved merely to reconcile activation, and its prices are not overwritten.

The canonical desired flag is `HESABFA_ITEM_ACTIVE = True` via `hesabfa_item_should_be_active()` in `app/services/hesabfa/item_lifecycle.py`. Desired state is not write authorization. The website publication lifecycle and Hesabfa accounting item lifecycle are intentionally independent.

| State | Meaning |
|-------|---------|
| Site `is_active` | Storefront / catalog publication |
| Site `is_available` | Website sale availability (موجود / ناموجود) |
| Hesabfa `active` | Accounting item lifecycle. New shells this integration creates are active. Existing items are not rewritten to chase this flag |

Soft-deleting a site product does **not** deactivate the Hesabfa item. `ensure_product_in_hesabfa()` skips `deleted_at IS NOT NULL`, which means do not touch Hesabfa, not deactivate it. `ProductService.delete_product()` does not call Hesabfa.

Hard-deleting a site product is not redesigned here. The local mapping row can disappear with the product (FK `ON DELETE CASCADE`). This integration does not delete or deactivate the Hesabfa item, so accounting history is not destroyed as a side effect. Orphaned Hesabfa items can remain; that is intentional.

`reconcile_product_item_shell()` still **refuses** the operation for site-active, site-available, priced, or non-zero `stock_quantity` rows. That is an operation gate for the draft-shell reconciler (which rows it may touch). It is not the Hesabfa `active` flag. A save on that path is create-only, after lookup proves no ProductCode, and the new item is active.

## Existing-item price safety

`item/save` is assumed to be a full replacement. Karzar must not perform an activation-only `item/save` on an already mapped Hesabfa item while price-preserving update semantics are unproven. Safety comes from not issuing that save.

`ensure_product_in_hesabfa()` calls `item/save` only when lookup proves no ProductCode exists, and that create payload omits `code`. An already mapped item, or a ProductCode that already exists, is left untouched (`existing_item_preserved`). Shell `buyPrice` / `sellPrice` of 0 are create-only. They are not sent onto an existing item. Zero shell prices must never overwrite an existing item.

Create-missing shell prices are not invoice line prices. Invoice lines stay gross `unitPrice` with `tax` 0 until VAT metadata is proven (see Invoice money / tax).

A mapped item whose remote `Active` is false is classified `RECONCILIATION_REQUIRED`. This PR reports it for a later controlled correction. It does not correct it. `--apply` stays refused. No environment flag enables mass activation.

POLICY IMPLEMENTED: storefront lifecycle does not write Hesabfa activation. A read-only reconciliation on 2026-09-29 classified the live catalog and did not correct mapped inactive items (`audit/hesabfa-activation-reconcile-2026-09-29/README.md`). That snapshot is evidence. It is not a claim that every Hesabfa item is active, and it does not authorize APPLY.

## Activation reconciliation (dry-run only)

```bash
python scripts/hesabfa_product_activation_reconcile.py --dry-run --batch-size 250
python scripts/hesabfa_product_activation_reconcile.py --dry-run --resume --after-id 1000
```

Target population: `Product.deleted_at IS NULL`. The scan is not restricted by `is_active`, `is_available`, price, image, or sellability.

Dry-run is the default. It reads the local database and Hesabfa items (`item/getItems`) or JSON snapshots. It does **not** call `item/save`, and it does not commit database writes. Reports land in `artifacts/hesabfa_product_activation/` (`summary.json`, `reconciliation.csv`, `errors.csv`, `ambiguous.csv`, `sha256sums.txt`) with `DRY_RUN=true`, `REMOTE_WRITES=0`, `DATABASE_WRITES=0`.

Identity is site `sku` ↔ Hesabfa `ProductCode`. Duplicate or conflicting matches are `AMBIGUOUS` and are not repaired.

The live dry-run opens one database read-only transaction before the catalog read (`SET TRANSACTION READ ONLY`, then `SHOW transaction_read_only` must be `on`, on PostgreSQL; `PRAGMA query_only=ON` on SQLite), loads non-deleted products and mappings once, classifies in memory, and rolls the transaction back. It does not fall back to a writable session.

ProductCode lookup pages `item/getItems` until the fetched row count equals reported `TotalCount`. A short page, a repeated page, or a duplicate remote `Code` fails closed. A short first page is not treated as proof that an item is missing. The published list-filter example uses operator `*` (contains) and is not used as an exact ProductCode query. Duplicate ProductCodes raise.

`--apply` is **refused** with `BLOCKED_PENDING_API_CONFIRMATION`. Official `item/save` documentation (https://www.hesabfa.com/help/api/item) says an existing `code` edits the item, `name` and `itemType` are required, and `buyPrice` / `sellPrice` are optional. Stock is not an `item/save` field; opening quantity is a separate method limited to the first fiscal year. That page does not state whether an update replaces omitted fields, and it does not show an existing item saved with explicit zero prices. `ITEM_SAVE_CONTRACT` remains `UNKNOWN`. The apply refusal remains even with `--confirm-production-write`, `KARZAR_ALLOW_PRODUCTION_WRITE=1`, and `KARZAR_INGESTION_CATEGORY=B`. Do not use `POST /hesabfa/items/push` as an activation campaign. It does not save an already mapped item. It creates a missing shell only.

`item/save` update semantics remain unproven. Do not run a production save experiment. A contract test belongs on a dedicated non-production Hesabfa business.

Classifications include `UNMAPPED`, `MAPPED_ACTIVE`, `RECONCILIATION_REQUIRED` (mapped or discovered inactive), `MISSING_REMOTE_ITEM`, `AMBIGUOUS`, and `PRICE_RISK` (a read item has a non-zero buy or sell price). `WOULD_ACTIVATE` stays 0 because activation is not an authorized write.

The push backfill's population is every non-deleted site product. Only a proven-missing ProductCode is created, and that new shell is active regardless of site publication state.

## Inventory policy

- Warehouse counts: **Hesabfa only**.
- Site: `is_available` boolean. Storefront shows **موجود** / **ناموجود**.
- Do **not** import `GetQuantity` into the site (worker removed; `/stock/sync` is a no-op).
- Product create may create a new Hesabfa shell when integration is enabled and no ProductCode exists. The create payload omits quantity fields and sets `active` true. Product update, availability changes, price removal, and soft delete do not save an already mapped item.
- Legacy `stock_quantity` column is kept at `0` (cleared after older pulls).

## Categories

Hesabfa `item/save` supports `nodeFamily`, but site categories are **not synced** (shop IA ≠ accounting folders). Match by SKU only.

## Payment hook

`verify_order_payment` → `maybe_create_invoice_after_payment`. Failures never roll back payment. `HESABFA_TEST_MODE=true` → skip with status `skipped`.

## Invoice money / tax

Karzar `OrderItem.unit_price` is the **final customer-facing gross** (same meaning as
`Product.base_price` for payment). Hesabfa sale invoice lines are tax-exclusive in
the public plugin contract:

```text
line_total = unitPrice × quantity − discount + tax
invoice_total ≈ Σ(line_total) + freight
```

Evidence (official WooCommerce Hesabfa plugin `ssbhesabfa`):

| Field | Plugin meaning |
|-------|----------------|
| `UnitPrice` | WooCommerce line `subtotal / quantity` (net of line tax) |
| `Discount` | `subtotal − total` |
| `Tax` | absolute `subtotal_tax` |
| `Freight` | `shipping_total + shipping_tax` |

### Current Karzar fail-safe (accounting tax unproven)

`product.tax_percent` / snapped `OrderItem.tax_percent` is **not** proven to be
authoritative embedded-VAT metadata (create/admin default `9` vs ORM/DB `0`;
imports often omit an intentional accounting choice). Inventing a net/tax split
from that field would misclassify VAT while the customer already paid the gross.

Until Owner/accounting confirms the metadata:

| Field | Karzar behavior |
|-------|-----------------|
| `unitPrice` | Full gross (paid) unit amount in Hesabfa money |
| `tax` | `0` |
| `freight` | `shipping_customer_cost` (0 for `receiver_due`) |
| `discount` | `0` |

This keeps:

```text
Σ(unitPrice × quantity) + freight == order.estimated_total
```

(within currency conversion), without claiming a VAT breakdown.

### Future Owner-gated inclusive extraction

Helper `_inclusive_net_unit_and_tax` implements:

1. Convert gross unit toman → Hesabfa money (`rial` = ×10 integer; `toman` = 0.01).
2. `gross_line = gross_unit × quantity`.
3. `net_line = round(gross_line / (1 + tax_percent/100))` (`ROUND_HALF_UP`).
4. `net_unit = floor(net_line / quantity)` to the currency quantum (keeps `tax >= 0`).
5. `tax = gross_line − net_unit × quantity`.

Enable only after Owner confirms `tax_percent` means VAT already included in
`base_price`. Never send `unitPrice = gross` together with `tax = gross × rate`
(that double-counts tax).
