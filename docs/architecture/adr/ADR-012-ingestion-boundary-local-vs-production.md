# ADR-012 — Ingestion Boundary (Local vs Production)

## Status
Accepted

### Board Acceptance (Wave 1)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۷ (2026-07-29) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | موج ۱ قفل EPIC 1 — تصمیم **الف** |
| **Scope** | Binding ingestion boundary: Category A routine writes local-only; production enrichment not routine; aligns `data-ingestion-policy.md`. |

## Date
2026-07-29

## Deciders
Architecture Board (**Accepted** ۱۴۰۵/۰۵/۰۷ · Mohammad Shebahati) · Backend lead · Platform Architect · Security consult

## Context
`data-ingestion-policy.md` is binding: Category A routine catalog writes via local API only; ban default live-API imports against `https://api.karzartools.com`. Historical script defaults often pointed at production (documented non-compliance for routine use). Repository governance lock PASS does not weaken this.

**Problem:** Enrichment convenience regresses to production writes, destroying Plane A pipeline SoT.

## Decision Drivers
- Production safety
- Reproducibility
- Auditability
- Alignment with ADR-001 Plane A
- Non-bypassable failure mode

## Considered Options
### Option A — Allow production enrichment when “careful”

Engineers may write prod if they pinky-promise.

**Pros:** Fast fixes.

**Cons:** Undermines policy; unreviewable.

**Risks:** Catastrophic bulk edits.
### Option B — Local-only forever including controlled prod deploys

Never any prod catalog pipeline.

**Pros:** Max isolation.

**Cons:** Blocks legitimate Category B controlled execution.

**Risks:** Manual prod drift.
### Option C — Category A local default; controlled B only (Chosen)

Affirm ingestion policy categories; harden expectations.

**Pros:** Matches binding policy.

**Cons:** Requires CI/discipline.

**Risks:** Mis-tagged Category B.

## Decision
1. **Category A (default enrichment/import/bulk update) catalog writes MUST use local API only**, with expected base `KARZAR_API_BASE=http://127.0.0.1:8000/api/v1` (or equivalent documented local base).
2. **Production write prohibition for routine enrichment remains normative.** Scripts MUST NOT default to `https://api.karzartools.com` for Category A work.
3. **Failure mode:** If a Category A job is configured to target production, it MUST NOT proceed (fail closed: abort with error). “Continue with warning” is non-compliant.
4. Every ingestion job MUST declare Source, Destination, Owner, Validation, Audit trail, Rollback per ingestion policy §5.
5. **Category B** controlled production execution remains possible only under ingestion policy ticket/backup controls — not as a developer habit.
6. **This ADR MUST NOT be weakened by any other ADR** (Prompt 2 rule R4). AI agents (ADR-009) MUST NOT write production catalog data.
7. Audit/logging: enrichment runs SHOULD emit machine-readable run logs retained with the Git-versioned job definition.

## Rejected Alternatives
Rejected “careful production enrichment” (A) as Category A practice. Rejected absolute forever ban on all controlled Category B (B) that would contradict ingestion policy’s controlled path.

## Consequences
### Positive
- Protects 5901 baseline integrity
- Makes PR review objective (ADR citation)
- Aligns scripts with Plane A SoT

### Negative / Trade-offs
- Local environment must stay healthy
- Legacy scripts need default fixes over time (via PRs, not this ADR alone)

### Follow-up work required
- Prompt 11 developer standards / PR checklist
- Ingestion policy remains KEEP binding doc
- All enrichment Epics
- No RFC required to *obey* this ADR; RFC required to *change* it

## Compliance & Gates
Non-compliant: Category A job targeting production; missing fail-closed guard; agent prod writes. **No other ADR may override this boundary.**

## References
- `docs/architecture/karzar-knowledge-platform-master-architecture.md`
- `docs/architecture/data-ingestion-policy.md`
- `docs/architecture/specification-data-flow.md`
- `docs/audits/repository-governance-final-lock.md`
- `docs/audits/EPIC0-executive-summary.md`
- `docs/audits/catalog-baseline-completeness-report.md`

## Acceptance Self-Check
- [x] Decision is implementable without guessing
- [x] Alternatives recorded
- [x] No schema migration ordered by this ADR alone
- [x] No contradiction with ingestion policy
- [x] EPIC 0 facts not falsified
