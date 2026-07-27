# Security Progress

**Rollup:** 100%

- [x] **SEC-001** Security hygiene pass for go-live bar — `done` 100% | P1 | 12h | Sprint 03
  - Owner: unassigned | Week 5 Day 1 | Risk: med
  - [x] Description: Admin noindex, step-up coverage, dependency scan, secrets audit.
  - [x] Dependencies: —
  - [x] Files: app/**, frontend/admin-panel/**
  - [x] Modules: security
  - [x] Tags: security
  - Acceptance Criteria:
    - [x] Admin X-Robots-Tag
    - [x] No secrets in FE
  - Definition of Done:
    - [x] SECURITY_PROGRESS
  - Notes: Admin `X-Robots-Tag: noindex, nofollow, noarchive` via shared `security-headers` + layout `robots: { index: false }`; `scripts/security_hygiene_check.sh` green; FE secret pattern scan 0 hits; step-up PIN on products/orders/CMS/customers/brands/categories; Pillow→12.3.0; residual ecdsa + Next/postcss/sharp tracked in RISKS R8.

## Evidence log
- [x] SEC-001 implementation: admin security headers module + vitest + hygiene script + Pillow bump (this PR)
- [x] Secrets audit: `bash scripts/security_hygiene_check.sh` passed; FE tracked-source key-material scan = 0 hits
- [x] Dependency scan: `pip-audit -r requirements.txt` → remaining `ecdsa` PYSEC-2026-1325 (transitive via python-jose); npm audit high on next/postcss/sharp deferred (force Next 16.2.12 out of range)
