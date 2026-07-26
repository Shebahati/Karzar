# Product SEO descriptions — locked plan

**Status:** P0 merged (#66, 2026-07-25); P1 tooling follow-up  
**Companions:** `seo-architecture-constitution.md`, `information-architecture-constitution.md`, PIM Naming & Descriptions, `product-quality-framework.md`, `ai-content-pipeline.md`

## Locked decisions (2026-07-25)

1. **Separate `short_description` field** — do **not** reuse `description` as the short body. Long body stays `description`. Keep `meta_title` / `meta_description`.
2. **P2 brand order:** INSIZE → Mitutoyo → Dasqua (rewrite name-echo stubs) → ASIMETO.
3. **AI allowed for long-form (P4)** at highest quality with strict constitution / PIM / AI-pipeline alignment. AI output = **Draft → human QA** only; **no hallucinated specs**.
4. **Apply on staging first** (`api.karzartools.com` / staging DB), dry-run before write; promote after review. Do not write production unless the environment is clearly the same and already confirmed staging=live on this VPS.

## Field roles

| Field | Role |
|-------|------|
| `short_description` | Visible PDP blurb + default meta/JSON-LD source |
| `description` | Long editorial body |
| `meta_title` | Optional SEO title override (else product name) |
| `meta_description` | Optional SEO description override |
| `slug` | Exposed on API for future `/product/[slug]`; **no URL migrate in P0** |

### Metadata priority (storefront)

- Title: `meta_title` → `name`
- Description: `meta_description` → `short_description` → `description` excerpt → minimal non-spammy fallback
- JSON-LD `Product.description`: visible short (or subset); no extra claims

## Phases

| Phase | Scope |
|-------|--------|
| **P0** | DB + API + admin form + PDP metadata/visible short+long + tests (**merged** #66) |
| **P1** | Deterministic template (SoT-only, bilingual brand cleanup) + dry-run with `brand_id` + detail hydrate |
| **P2** | Bulk fill by brand order on staging after dry-run review |
| **P3** | QA sampling / stub residual checks |
| **P4** | AI long-form drafts only (Pending); human publish gate |

## Out of scope (until later)

- Full bulk apply without dry-run review
- Migrating URLs to `/product/[slug]`
- Committing secrets / production writes by default

## Staging deploy + migration

Migration: `b3c4d5e6f7a8_product_short_description` (`products.short_description` Text nullable).

Applied on staging (2026-07-25): alembic head `b3c4d5e6f7a8`, column present.

```bash
# From laptop (clean origin/main tree — avoid local WIP revision collisions)
TMP=$(mktemp -d) && git archive origin/main | tar -x -C "$TMP"
rsync -az --delete --exclude '.git/' --exclude '.env' --exclude 'backups/' \
  --exclude 'data/uploads/' --exclude 'logs/' --exclude 'frontend/' \
  "$TMP/" root@195.177.255.198:/opt/karzar/Karzar/
ssh root@195.177.255.198 'cd /opt/karzar/Karzar && bash deploy/staging/scripts/deploy-backend.sh'
# entrypoint runs: alembic upgrade head
```

## Staging dry-run (P2 prep)

```bash
export KARZAR_API_BASE=https://api.karzartools.com/api/v1
python scripts/dry_run_product_seo_descriptions.py --brand INSIZE --limit 500 --hydrate-detail 25 --json /tmp/seo-insize.json
python scripts/dry_run_product_seo_descriptions.py --brand Mitutoyo --limit 500 --hydrate-detail 25 --json /tmp/seo-mitutoyo.json
python scripts/dry_run_product_seo_descriptions.py --brand Dasqua --limit 500 --hydrate-detail 25 --json /tmp/seo-dasqua.json
python scripts/dry_run_product_seo_descriptions.py --brand ASIMETO --limit 500 --hydrate-detail 25 --json /tmp/seo-asimeto.json
```

Do **not** pass `--apply` until samples look excellent and migration is live (already is on staging).

### Apply gate (P2)

Bulk write only when `apply_ready` is true: template must include at least one safe measurement SoT field (`range` / `resolution` / بازه / دقت / …). Category+SKU-only blurbs are dry-run review fodder, not bulk-write candidates (taxonomy leaves often mislabel kits/sets).

Templates prefer a **name-derived product lead** over a short category leaf when the name is more specific.
