# Karzar API — Frontend Handover

## Live docs
- Swagger UI: `/api/docs`
- OpenAPI JSON: `/api/openapi.json` (use with `openapi-typescript`)

## Error envelope (all HTTP errors)
```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "Request validation failed",
  "details": [{ "field": "sku", "message": "already exists" }]
}
```

## Product list (PLP) — `GET /api/v1/products/`
Query: `skip`, `limit`, `category_id`, `brand_id`, `is_active`, `search`, `min_price`, `max_price`

Spec filters (choose one or combine):
- JSON: `?filters={"technical_specs.range":"0-150mm"}`
- Prefixed: `?spec_technical_specs__range=0-150mm` (`__` = dot in path)
- Substring: `?filters={"technical_specs.range__icontains":"150"}`

Response:
```json
{
  "data": [{ "id": 1, "sku": "...", "name": "...", "thumbnail": null, "base_price": "99.99", "stock_status": "in_stock", "category": { "id": 1, "name": "..." }, "brand": { "id": 1, "name": "..." } }],
  "meta": { "total_count": 0, "skip": 0, "limit": 100, "has_next": false, "has_prev": false }
}
```

## Product detail (PDP) — `GET /api/v1/products/{id}` or `/sku/{sku}`
Full product with `images[]`, `thumbnail`, `stock_status`, `low_stock`, `availability`, typed `specifications`, nested `category`/`brand`.

## Category tree — `GET /api/v1/categories/tree`
Unlimited product-assignable depth is **not** supported: only depth-3 leaf categories are selectable (`is_selectable=true`). The tree endpoint may render up to 3 layers; creating a 4th layer is rejected.

**Response shape:** raw JSON array (not `{ "data": [...] }`).

```json
[{ "id": 1, "name": "...", "slug": "...", "parent_id": null, "subcategories": [{ "...": "..." }] }]
```
Children are sorted alphabetically by `name`.

## Auth
- Login: `POST /api/v1/auth/login` — `application/x-www-form-urlencoded` (`username` = phone, `password`)
- Register: `POST /api/v1/auth/register` — JSON body
- Step-up (delete/restore): `POST /api/v1/auth/verify-pin` with `{ "pin": "..." }` → returns `secure_token`
- Destructive requests need: `Authorization: Bearer <jwt>` + `X-Step-Up-Token: <secure_token>`

## Recommended frontend stack
Next.js + TypeScript + TanStack Query — SSR for SEO, type generation from OpenAPI, cached server state for PLP/PDP.
