# IMAGE Discovery Pipeline

**Implementation status:** merged to `main` (PR #198)
**Production status:** not approved
**Offline 100-SKU asset/state regression:** passed (copy of preserved external pilot; no live network)
**Live current TOSAG parser regression:** pending
**Database / ProductImage integration:** not implemented

**Scope:** Generic multi-brand engine + INSIZE/TOSAG adapter (`insize_tosag`)
**Non-goals:** DB writes, `ProductImage` insert, Alembic, staging/prod apply, cropping, commercial-rights clearance

### Merge record

```text
Merged PR: #198
Merge commit: f10cfff3ace2a00ef3a7403d5408e79e0b9b395b
Final implementation head: fe227b4f03c110d81f468f8a760d4ccf6fb23092
Final local test suite before merge: 110 passed
```

This tool is **not** production-ready. Live TOSAG parser validation remains pending. No ProductImage or database apply is in scope for the merged tooling.

## Architecture

| Layer | Owns |
|-------|------|
| `scripts/discover_product_images.py` | CLI (`run`, `consolidate`) + numeric flag validation |
| `scripts/image_discovery/contracts.py` | Manifest fields, global `candidate_id` / `product_key` identity, source-manifest contract |
| `scripts/image_discovery/paths.py` | Safe path segments; **no-follow** asset scans; governed/batch root symlink rejection |
| `scripts/image_discovery/atomic.py` | Atomic writes + corrupt JSON refuse-overwrite |
| `scripts/image_discovery/core.py` | Orchestration, single-flight URL cache, resume, **run output policy** |
| `scripts/image_discovery/transport.py` | HTTP allowlist, redirects, bounded reads, scheme/port |
| `scripts/image_discovery/quality.py` | Signature + structural verify, dimensions, presentation flags |
| `scripts/image_discovery/output.py` | Manifests, semantic hash, contact sheet, referenced-asset run-state |
| `scripts/image_discovery/consolidation.py` | Cross-batch integrity, conflicts, coherent `--allow-replace` recognition |
| `scripts/image_discovery/sources/html_subject.py` | Structural `HTMLParser` subject/unrelated boundary + region-tagged meta/JSON-LD |
| `scripts/image_discovery/sources/insize_tosag.py` | INSIZE identity, TOSAG hosts, atomic structured acceptance |

The generic engine must not hard-code INSIZE/TOSAG business rules. New brands get new adapters under `sources/`.

## Identity contract (IMG-01B / IMG-01D)

- `product_id` may be empty for legacy external discovery.
- Else `product_key = product_id:<id>` / `identity_basis = product_id`.
- Otherwise `product_key = brand_sku:<normalized_brand>:<normalized_sku>` (never bare SKU globally).
- Adapter supplies `source_candidate_key` (CSV fallback = SHA-256 of detail|image|index — not Python `hash()`).
- `candidate_id = cid:` + SHA-256(`source_adapter`, `product_key`, `source_candidate_key`, `image_role`).
- Consolidation **fail-closes** on missing/malformed/mismatched `candidate_id` or empty/invalid Manifest SHA (never invents SHA from disk alone).

## Discovery versus validation

```text
candidate discovery → candidate validation → asset materialization → human review
```

**Currently implemented for INSIZE:** governed CSV **candidate validation** against public TOSAG detail pages (not open-web crawl / catalogue scrape). Page-subject boundaries use a stack-based `html.parser.HTMLParser` (not regex nesting). Meta and JSON-LD evidence carry DOM-region origin; unrelated regions never auto-confirm. Product JSON-LD acceptance is **atomic** (one Product object with compatible Brand + requested SKU/MPN/productID). Future adapters may implement discovery from official sites while reusing the same engine.

## Command

```bash
.venv/bin/python scripts/discover_product_images.py run \
  --source insize_tosag \
  --products-csv data/imports/insize_products.csv \
  --candidates-csv data/imports/insize_images_imported.csv \
  --output-dir /absolute/path/outside/repo \
  --limit 100 \
  --max-images-per-product 1 \
  --concurrency 2 \
  --delay 0.5 \
  --resume
```

```bash
.venv/bin/python scripts/discover_product_images.py consolidate \
  --input-dir /external/batches \
  --output-dir /external/consolidated \
  --allow-replace
```

**Run output policy (IMG-01E):**

- New run (no `--resume` / `--force-refetch`): `--output-dir` must be **absent or completely empty**.
- Arbitrary non-empty shells (`notes.txt`, unrelated `summary.json`, assets-only, partial pipeline, unknown files) fail closed.
- `--resume` requires a coherent governed prior output, same `source_adapter`, valid referenced assets, **source-manifest identity contract** (`validate_source_manifest_row` on every row — same as Consolidation), no unknown files, no symlink roots.
- `--force-refetch` still requires a coherent prior when the directory is non-empty (does not overwrite unrelated shells).

**`--allow-replace` policy (IMG-01D):**

- Every **non-empty** Output requires explicit handling (`--allow-replace` or a new empty directory).
- `--allow-replace` accepts **only** a coherent governed prior output: `manifests/manifest.json` (JSON list) + `summary.json` (JSON object identifying the pipeline) + `assets/`.
- Unknown top-level or nested files fail closed.
- Stale governed assets are inventoried in `manifests/preexisting-stale-files.csv` and **not** deleted; replacement is refused until the operator archives or chooses a new empty Output.
- Missing Manifest identity or SHA evidence fails closed (`status=integrity_failure`).
- **No symlink is followed** during any asset or root operation (`lstat` / no-follow iterators). Symlinked output/batch roots are rejected.

Legacy shim: `scripts/discover_insize_product_images.py` → forwards to `run --source insize_tosag`.

**Flags:** `--max-images-per-product` / `--concurrency` must be `> 0`; `--delay` / `--limit` / `--offset` must be `>= 0`. Without `--resume`, previous Manifest is not reused. With `--resume`, governed previous state may be reused when disk SHA matches. `--force-refetch` refetches network assets.

## Multi-image contract

Fields: `image_role`, `source_rank`, `display_order_candidate`, `source_image_index`, `candidate_id`, plus identity/provenance fields.
Roles include `primary`, `alternate`, `detail`, …
IMG-01 pilots use `--max-images-per-product 1` (primary coverage only).

## Safety

- Absolute `--output-dir` outside the Git repository (must not itself be a symlink)
- Host allowlist per adapter (INSIZE: `www.tosag.ch` only); HTTPS default; unexpected ports rejected
- Bounded HTTP body reads (`response_too_large`)
- Cross-host redirects rejected
- No SQLAlchemy / `app.db` / Product models
- Does not inspect credential environment variables
- Rights always `review_required` / `pending_human_review`
- Asset filenames use safe segments + short SHA suffix; full SHA-256 remains the integrity key
- Symlinks / non-regular files under `assets/` fail closed (`unexpected_asset_symlink` / `unexpected_non_regular_asset`)
- Symlinked governed roots (`assets/`, `manifests/`, `review/`, `logs/`, metadata files, batch roots) fail closed (`unexpected_governed_symlink`)
- Duplicate physical files with the same SHA are reported in `manifests/duplicate-physical-assets.csv` (not auto-deleted)

## Classification

| Specificity | Meaning |
|-------------|---------|
| `family` | Same content SHA shared by ≥2 SKUs of one brand |
| `singleton_unverified` | Unique in current set without exclusivity proof |
| `cross_brand_duplicate` | Same SHA across different brands → `pending_human_review` + `cross-brand-duplicates.csv` |
| `sku` | Only with explicit source exclusivity proof (not auto-inferred) |

Consolidation verifies source bytes vs declared Manifest SHA, writes `candidate-conflicts.*` / `candidate-provenance.*` on duplicates, and **fail-closes** on integrity errors (`status=integrity_failure`).

Same-brand SHAs shared by more than `HIGH_REUSE_SKU_THRESHOLD` (default **8**) SKUs are listed in `manifests/high-reuse-assets.csv` for human review (not auto-rejected).

## Run stability

`manifests/run-state.json` compares **manifest-referenced** asset SHA sets. Summary reports `new_referenced_assets`, `removed_referenced_assets`, `stale_unreferenced_files`, `missing_referenced_files`, `duplicate_physical_asset_*`, `unexpected_symlinks`. Corrupt JSON is not treated as a first-run empty state.

## Provenance

`provenance_batch`, `provenance_manifest`, `provenance_source_adapter` on accepted and rejected rows. Consolidation records every Batch occurrence in `candidate-provenance.*`.

## Validation scope honesty

| Kind | Status |
|------|--------|
| Asset/state offline 100-SKU resume regression | Proven (copy of external pilot; no live network) |
| Structural page-subject Parser fixture tests | Local HTML fixtures only — **not** live-site proof |
| Region-isolated meta/JSON-LD + atomic Product tests | Local HTML fixtures only — **not** live-site proof |
| Symlink-root / run-output policy tests | Local tmp fixtures |
| Live current TOSAG page-parser regression | **Pending** network availability — offline resume does **not** prove hardened parser behavior against the live site |
| Production / ProductImage apply | **Not implemented / not approved** |
