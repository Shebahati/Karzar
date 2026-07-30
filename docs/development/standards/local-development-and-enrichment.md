# Local Development & Enrichment

**Status:** Proposed · Binding companion: `docs/architecture/data-ingestion-policy.md`

---

## Environments

| Env | Role | Catalog writes |
|-----|------|----------------|
| **Local** (`karzar_db`, API `127.0.0.1:8000` typical) | Default develop/test after baseline | Category **A** |
| **Production** | Runtime store — not sandbox | Category **B** only with ticket + backup; never routine enrich |
| Baseline tag | `KARZAR-BASELINE-20260728` | Marker; do not rewrite history |

Primary checkout: `Website/backend`. Branch rules: `git-development-workflow.md`. Until unlock, Phase-9 stand-in may track main content — still branch for work.

---

## Catalog mutation classes

| Class | Allowed? | Notes |
|-------|----------|-------|
| Read-only analytics / SELECT audits | Yes | EPIC 0 style |
| Local API enrichment (Category A) | Yes | Versioned script; declare §5 attrs |
| Forbidden: laptop → production API/DB as routine | **No** | ADR-012 / ingestion policy |
| Category B production transform | Exception only | Ticket, backup, audit, Board-visible |
| Category C prod→local dump | Baseline/sync only | Not enrichment substitute |

---

## `KARZAR_API_BASE` rule

- Category A scripts/docs/examples MUST default or document **local** base.  
- Production URL as unnoticed default is **non-compliant**.  
- PR checklist fails if production base is the routine path.
- Targeting a production host requires **both** `KARZAR_ALLOW_PRODUCTION_WRITE=1` and
  `KARZAR_INGESTION_CATEGORY=B` (fail-closed via `scripts/ingestion_boundary.py`).

---

## Enrichment proof for PRs

1. Run against local baseline.  
2. Record counts / sample SKUs / validation.  
3. Fail-closed on unexpected delta when tool supports dry-run.  
4. New JSON keys → log CandidateProperty (ADR-004); do not treat as Approved Properties.  
5. Never dual-write Facts without RFC-003 gates.

---

## Observability minimum

Log: actor/job id, git ref, env, source, destination, row counts, validation result, errors.
