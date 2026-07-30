# Risk Register

- [ ] **R1** Head-term SEO expectation vs mid-tail strategy — Owner: Product/SEO — *mitigate:* KPI freeze in `EXECUTIVE_SUMMARY.md` + checkpoint narrative in `RELEASE_PLAN.md`.
- [ ] **R2** AI content hallucinations on specs — Owner: Content lead — *mitigate:* specs SoT in PIM; editorial ban on invented numeric claims.
- [ ] **R3** CWV regression from imagery or template drift — Owner: Frontend lead — *mitigate:* PERF-001 budgets landed; monitor field p75 during launch window; keep image priority/CDN constraints.
- [ ] **R4** Enrichment scripts writing commerce fields — Owner: Backend/data owner — *mitigate:* content-only assertions and no price/stock mutation policy.
- [ ] **R5** Single VPS staging=live blast radius — Owner: Ops — *mitigate:* pre-release backup verification + rollback operator assignment + off-peak deployment.
- [ ] **R6** Scope creep before checkpoint (knowledge platform and broad P2 work) — Owner: PMO — *mitigate:* KB-001 deferred; enforce freeze list from REL-001.
- [x] ~~**R7** Security gate incomplete at release decision point (`SEC-001`)~~ — mitigated 2026-07-27: SEC-001 ACs closed (X-Robots-Tag, FE secrets audit, step-up inventory, dep scan evidence).
- [x] **R9** OpenAPI contract drift undetected — Owner: Backend Architect — *closed 2026-07-30:* snapshot regenerated + Backend CI job `aods` runs `--gate openapi` (AODS `CR-012` CLOSED). Residual: add `aods` to branch-protection required checks (`OI-GOV-02`).
- [ ] **R10** AI agents operating without enforced scope or context control — Owner: Owner — *mitigate:* AODS prompt library + allow-list gate + forbidden-context list; residual until the pack is Accepted and its gates are required CI checks.
- [ ] **R11** Quality claims are self-certified — Owner: Independent auditor — *mitigate:* scorecard raises 5.7→9.0 with no independent re-audit; AODS requires the remediator not to score the remediation (AODS `CR-006`).
- [ ] **R8** Residual dependency advisories after SEC-001 — Owner: Security/Ops — *mitigate:* schedule controlled upgrades for (a) `ecdsa` PYSEC-2026-1325 via `python-jose`, (b) Next/postcss/sharp high advisories requiring Next 16.2.12 force bump outside current range; do not force-bump on release critical path without regression plan.
