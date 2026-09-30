# SEO Wave 1B — crawl + pagination contract

## PAGE_SIZE

- Shared `CATALOG_PAGE_SIZE = 20` (`src/config/catalog-page-size.ts`)
- Server PLP + client `CatalogView` + HTTP contract tests use the same constant.

## URL contract

| Surface | Page 1 | Page N |
|---------|--------|--------|
| Catalog | `/catalog` | `/catalog?page=N` |
| Category hub | `/categories/{slug}` | `/categories/{slug}?page=N` |
| Brand hub | `/brands/{slug}` | `/brands/{slug}?page=N` |
| Blog | `/blog` | `/blog?page=N` |

- Invalid `page` → redirect strips `page` (normalize to page 1 URL).
- `?page=1` → 308/redirect to clean page-1 URL (facets preserved).
- `page > totalPages` (valid integer) → HTTP 404 on catalog/hubs/blog.

## Canonical matrix (non-faceted)

- `/catalog` → `/catalog`
- `/catalog?page=2` → `/catalog?page=2`
- Hubs/blog: same pattern with hub path prefix.
- Faceted URLs: `noindex,follow`, canonical remains clean parent (e.g. `/catalog`).

## Facet + page

- Filter/sort/search/spec changes clear `page` via `applyCatalogParamPatch`.
- Pagination preserves non-page query params (`buildPaginatedHref`).

## Tests

- Unit: `src/lib/__tests__/pagination-url.test.ts`
- Production HTTP: `e2e/crawl-discovery.spec.ts` + Wave 1A `entity-http-status.spec.ts` via `npm run test:http-contract`

## SSR fetch (representative)

- **Catalog**: one `listProducts` for requested page + ancillary category/brand/tree prefetches.
- **Category hub**: one `listProducts` (paged) + flat/tree for chrome/JSON-LD.
- **Brand hub**: one `listProducts` (paged) for grid + JSON-LD.
- **Categories index**: one `listCategoriesTree` on server.
- **Blog**: one `listArticles` on server; client pagination is link-based.
