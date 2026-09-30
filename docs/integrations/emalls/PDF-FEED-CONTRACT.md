# Emalls direct PDF product feed

**Status:** Implementation evidence (not Board-Accepted).  
**Source of truth:** Emalls PDF supplied directly to Karzar — «راهنمای ایجاد صفحه معرفی محصولات به ایمالز».  
**Concern:** Read-only marketplace feed. No catalog/price/availability mutation.

## Two separate Emalls contracts

| | Contract A (WordPress plugin) | Contract B (this document) |
|--|------------------------------|----------------------------|
| Route | `POST /api/v1/integrations/emalls/products` | `GET\|POST /api/v1/integrations/emalls/feed` |
| Authority | Observed official WP extraction plugin | Direct Emalls PDF |
| Auth | Emalls token + remote validator | **Not specified by PDF** — none invented |
| Params | body/form `token`, `page`, `limit` | query `page`, `item_per_page` |
| Prices | string TOMAN; WC `old_price` fallback | integer TOMAN; `old_price` null when no discount |
| Docs | [`API-CONTRACT.md`](API-CONTRACT.md) | this file |

Do not conflate the two adapters.

## Route

| Item | Value |
|------|-------|
| Methods | `GET`, `POST` (identical semantics) |
| Path | `/api/v1/integrations/emalls/feed` |
| Content-Type | `application/json; charset=utf-8` |
| Body | **Not required** (PDF is query-string based) |

Example:

```
GET /api/v1/integrations/emalls/feed?page=1&item_per_page=50
POST /api/v1/integrations/emalls/feed?page=1&item_per_page=50
```

## Request

| Param | Default | Rules |
|-------|---------|-------|
| `page` | `1` | integer ≥ 1 |
| `item_per_page` | `50` | integer ≥ 1; **Karzar operational safety cap = 100** (not specified by the Emalls PDF) |

Invalid values → Karzar **422** validation envelope.

## Root response

PDF **required:** `products`, `pages_count`.  
PDF optional (returned by Karzar for operational clarity): `success`, `total_items`, `item_per_page`, `page_num`.

```json
{
  "success": true,
  "products": [],
  "total_items": 0,
  "pages_count": 0,
  "item_per_page": 50,
  "page_num": 1
}
```

Not returned: `count`, `max_pages`, `Version`, `NeedSession`, `TokenSendByEmalls`.

## Product fields

| Field | PDF | Karzar mapping |
|-------|-----|----------------|
| `title` | string, required | `product.name` |
| `id` | string, optional | `str(product.id)` |
| `price` | integer TOMAN, required | `base_price` exact integer |
| `old_price` | integer TOMAN, optional | `original_price` if present and exact integer, else `null` (no WC fallback; fractional never truncated) |
| `category` | string, required | assigned category `name` |
| `image` | string URL, required | primary valid public HTTPS image |
| `color` | string, optional | `""` — Karzar has no canonical color source |
| `guarantee` | string, optional | `warranty_text` or `""` |
| `is_available` | boolean, required | `product_is_available(product)` |
| `url` | string URL, required | `{EMALLS_PUBLIC_SITE_ORIGIN}/product/{slug}` |

## Price

- Unit: **TOMAN** (explicit in the Emalls PDF).
- Serialization: JSON **integer** (not string).
- No ×10 / ÷10 / Rial conversion.
- Unpriced (`base_price` null) or non-positive / fractional Toman → **excluded** from this feed (PDF requires `price`).
- Fractional Decimals are never truncated; they fail integrity / eligibility.

## Eligibility

PDF-feed eligible set (not the broader WordPress `/products` set):

1. `deleted_at IS NULL`
2. `is_active = true`
3. valid non-placeholder public HTTPS image (absolute; no localhost/private/staging)
4. exact positive integer `base_price` (PDF-required price)
5. non-empty `name`, `slug`
6. category present with non-empty trimmed `name` (not merely `category_id`)

**Availability is not an inclusion gate.** Public + unavailable products export with `"is_available": false`.

`stock_quantity` is never used.

Ordering: `Product.id DESC`.

### Pagination invariant

`total_items`, `pages_count`, and page slicing derive from the **same final**
PDF-feed eligible set (after coarse SQL candidates + authoritative Python
`product_satisfies_pdf_feed`).

**No post-pagination eligibility dropping is permitted.** A row counted in
`total_items` must be serializable on some page; a row rejected by final
eligibility must not inflate counts or consume page slots.

Image selection for eligibility and presentation is identical: primary-first /
`display_order` / `id`, first URL that is non-placeholder and resolves to
public HTTPS. An invalid earlier non-placeholder does not hide a later valid
image.

Fractional `original_price` is omitted as `old_price: null` (optional PDF
field; never truncated). That omission is a data-quality anomaly visible only
via DB-level audit — API-only preflight must not claim zero fractional
anomalies.

## Authentication

The PDF does **not** specify token, API key, or Authorization. This endpoint invents none. Throttle (`PUBLIC_THROTTLE_EMALLS_*`) is a Karzar operational control.

## Preflight

`scripts/emalls_pdf_feed_preflight.py` — read-only; no token.

- `--pages 0` = full feed: requires `fetched == total_items`, page fullness,
  premature-empty detection, constant root pagination fields.
- `--pages N` = partial scan: does **not** require `fetched == total_items`;
  report `scan_complete: false` / `full_feed: false`.
- Only claim FULL FEED when `scan_complete` is true.

## Open questions (PDF silent)

1. Whether Emalls will later require authentication for custom feeds.
2. Maximum `item_per_page` (Karzar uses safety cap 100).
3. Whether `old_price: null` vs omitting the key is preferred by Emalls UI (Karzar returns `null` for stable shape).
