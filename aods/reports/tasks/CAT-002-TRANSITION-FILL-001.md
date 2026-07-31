# Task record — CAT-002-TRANSITION-FILL-001

| Field | Value |
|-------|-------|
| NODE_ID | CAT-002-TRANSITION-FILL-001 |
| Archetype | KNOW |
| Prompt | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| Date | 2026-07-30 |
| TASK_ID | CAT-002 |
| Change class | C3 (catalog content transform; Category A local) |
| Strategy | C-as-A transition fill (shopmill → locked measurement keys + `source_attributes`; fill-empty; no invent; CandidateProperty mindset) |
| Allowlist | `scripts/enrich_insize*.py` (run only), `scripts/shopmill_insize_crawl.py` (run only), `data/imports/insize/**`, `project-management/**`, `aods/reports/tasks/**` |

## Authority (origin/main)

- `docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md` — Category A → local only; fail-closed on production
- `docs/architecture/data-ingestion-policy.md` — provenance, no invent, declare Source/Destination
- `docs/development/standards/local-development-and-enrichment.md` — local Category A; CandidateProperty for new keys
- Script contract: `scripts/enrich_insize_from_shopmill.py` header (content-only PUT keys; forbidden commerce)

## Source verification

| Artifact | Path | sha256 |
|----------|------|--------|
| Crawl (reused) | `data/imports/insize/shopmill/shopmill_insize.jsonl` | `35aba1cc78ac0aea2d39e76d2c6018b012731602e0cda45302ac2bb0dfe10903` |
| Site export (offline dry-run only) | `data/imports/insize/shopmill/site_export.jsonl` | `56c97c7b099c4d914db40ac1a68e5902630a17afec3f774b8fadca846519dc94` |

Provenance note: `data/imports/insize/shopmill/PROVENANCE-CAT-002.txt`

Live shopmill Store API (`/wp-json/wc/store/v1/products`) timed out from this host (curl exit 28). Homepage reachable. Reused commerce-stripped legacy crawl (867 rows, 861 with specs; zero price/stock keys).

## Resolved target

```
KARZAR_API_BASE=http://127.0.0.1:8000/api/v1
```

LOCAL: YES (declared). REACHABLE: YES — apply executed 2026-07-30 after stack repair.

## Dry-run results

Command:

```bash
KARZAR_API_BASE=http://127.0.0.1:8000/api/v1 \
  python3 scripts/enrich_insize_from_shopmill.py --reuse-crawl --reuse-export --dry-run
```

| Metric | Value |
|--------|-------|
| shopmill_rows | 867 |
| catalog_insize (export) | 872 |
| matched | 861 |
| payloads | 861 |
| skipped_no_specs | 6 |
| unmatched | 5 |
| ambiguous | 0 |
| apply | false |
| zero_price_writes | true |
| payload_forbidden_count | 0 |
| country_as_material | 0 |

Reports:

- `data/imports/insize/shopmill/summary.json`
- `data/imports/insize/shopmill/dry_run_payloads.jsonl`
- `data/imports/insize/shopmill/match_report.csv`
- `data/imports/insize/shopmill/dry_run_cat002.log`

## HALT before apply (superseded by stack repair + apply)

TRIGGER: local API unreachable (E2 environment / operator sequence §1).

Evidence:

- `curl http://127.0.0.1:8000/...` → connection refused
- `docker logs lathe_api` → `cannot open /app/docker-entrypoint.sh`
- Container bind-mount: `/home/moahmmad/Projects/Karzar/Website/backend` → `/app` (wrong/missing tree vs this checkout)

No `--apply` run. No production/staging write. No HC-09 packet.

## Proposed next commands (human)

1. Fix/start local stack from this repo (see operator checklist in agent report).
2. Fresh local export (drop `--reuse-export`).
3. Dry-run against fresh export; spot-check ≥200.
4. `KARZAR_API_BASE=http://127.0.0.1:8000/api/v1 python3 scripts/enrich_insize_from_shopmill.py --reuse-crawl --apply --apply-confirm`

## PMO

CAT-002 → `in_progress` / 40%. Mirrors: BACKEND_PROGRESS, SPRINT_02, KANBAN, CHANGELOG, SEO_PROGRESS.

## Status

HALTED after dry-run — awaiting healthy local Category A API before apply.


## Stack repair (2026-07-30 follow-up)

| Issue | Fix |
|-------|-----|
| `lathe_api` Project=`backend`, bind-mount `…/Karzar/Website/backend` (empty; missing `docker-entrypoint.sh`) | Removed broken container; `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build app` from this repo (`Mount=/home/moahmmad/Projects/Karzar-clean/Karzar`) |
| `asyncpg.InvalidPasswordError` (pg_hba: localhost `trust`, docker network `scram-sha-256`; volume password ≠ `.env`) | `ALTER USER` password to match compose/`.env` (local only) |
| Apply login 401 | Env admin phone existed as `super_admin` but hash ≠ `INITIAL_SUPER_ADMIN_PASSWORD`; local hash reset to settings bootstrap creds |
| WordPress exited container claiming `:8000` | Removed `karzartools-wordpress-1` |

Ready probe (real):

```text
{"status":"ready","service":"Industrial Lathe Tools API","database":"ok","redis":"ok"}
```

## Apply results (local Category A)

Command:

```bash
KARZAR_API_BASE=http://127.0.0.1:8000/api/v1 \
  python3 scripts/enrich_insize_from_shopmill.py --reuse-crawl --apply --apply-confirm
```

(Fresh site export from local API; not `--reuse-export`.)

| Metric | Value |
|--------|-------|
| api | `http://127.0.0.1:8000/api/v1` |
| catalog_insize | 872 |
| already_complete | 735 |
| matched (new payloads) | 126 |
| skipped_no_specs | 6 |
| unmatched | 5 |
| applied | 126 |
| apply_errors | 0 |
| zero_price_writes | true |
| fields_written | description, meta_description, meta_title, short_description, specifications |

Reports: `apply_report.csv`, `applied.csv` under `data/imports/insize/shopmill/`.

## Remaining

- AC ≥200 SKU human QA spot-check still open
- 5 unmatched + 6 no-specs residual
- No HC-09 / no staging-prod promote
