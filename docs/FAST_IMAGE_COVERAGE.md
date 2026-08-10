# Fast Image Coverage

**Program:** IMG-FAST-01 — Catalog-wide one-image coverage sprint  
**Current node:** IMG-FAST-01A — Live storefront catalog baseline

## Objective

Ensure **one usable primary image per storefront product**.

“Usable” means the image the public storefront currently exposes as the summary `thumbnail` (or a deterministically promotable existing gallery image) resolves over HTTP and decodes as an image. This is **not** a product-identity or photography-quality review.

## Fast Coverage vs Quality Enrichment

| Track | Goal | This node |
|-------|------|-----------|
| **Fast Coverage** | Every storefront product has at least one technically usable primary image | Baseline only (IMG-FAST-01A) |
| **Quality Enrichment** | Rights-cleared, brand-correct, high-quality replacements | Later nodes — **out of scope here** |

## IMG-FAST-01A scope

- Enumerate the **public storefront catalog** via `GET /api/v1/products/` (trailing slash; `limit` 1..1000).
- Classify each product into exactly one of:
  - `usable_primary`
  - `promotable_existing_image` (reuse existing gallery asset — **not** internet discovery)
  - `missing_all_images`
  - `broken_only`
  - `known_placeholder_only` (deterministic signatures only)
  - `ambiguous_current_state`
- Emit an external Artifact under `/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01A`.

### Non-goals (this node)

- Image discovery / third-party search
- ProductImage writes / DB writes / storage writes
- Replacement execution
- Human-review bundle generation
- Merge / Ready-for-review

## Authority

Primary current-state authority for the accepted IMG-FAST-01A baseline was the **public storefront catalog** reached via an **explicit** `--api-base` (the accepted run targeted the public storefront API host). Environment naming (e.g. `/health` self-label “Staging”) is operational debt and does not change read-only baseline semantics.

Historical IMG-02A-01 inventory (`docs/EXISTING_IMAGE_AUDIT.md`, 2026-08-03) is **reference only** — never copied into current counts.

This program plan **does not supersede ADR-012** and **does not authorize production writes**. IMG-FAST-01A is read-only GET validation only.

## Environment selection (fail-closed)

**No production/live API endpoint is a code default.**

Operational runs **require** an explicit `--api-base`. The script will not choose localhost, staging, or any live host silently.

```bash
python scripts/build_fast_image_coverage_baseline.py \
  --api-base "$KARZAR_FAST_COVERAGE_API_BASE" \
  --package-dir /home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01A \
  --zip-path /home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01A.zip
```

Missing `--api-base` exits before any network activity.

## Runtime contracts (origin/main)

- Storefront list forces `is_active=True` for non-super-admin (`app/api/endpoints/products_catalog.py`).
- Thumbnail / primary selection: `is_primary` else `images[0]`; order `(not is_primary, display_order, id)` (`app/utils/product_presenter.py`).

## Tooling

CI tests (`tests/test_fast_image_coverage_baseline.py`) are **fixture-only** and perform zero live network calls.
