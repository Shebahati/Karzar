# Frontend collaborator gates + Owner GitHub access pack

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Owner order** | FE self-merge + Deploy Staging without Owner review; must not break code/docs |
| **Collaborator** | `mhrbzandi-Designer` |
| **Agent limit** | GitHub collaborator invite + branch protection API → **403** (Owner UI required) |

## Delivered in Git

- `docs/FRONTEND_COLLABORATOR_CHARTER.md`
- `docs/FRONTEND_COLLABORATOR_HANDOFF_FA.md` (paste-ready)
- `docs/OWNER_GITHUB_FRONTEND_ACCESS.md`
- `.github/CODEOWNERS` hardened
- `.github/workflows/collaborator-scope-gate.yml`
- PR template FE block; links from README / COLLABORATOR_DEPLOY / frontend README

## Owner residual (cannot be done by agent token)

1. Invite `mhrbzandi-Designer` with **Write**
2. Branch protection: **0 approvals**, Code Owners review **Off**, required checks `storefront` + `admin-panel` + `Collaborator Scope Gate` (+ e2e preferred)
3. Staging env: no required reviewer; production Owner-only
4. Send updated handoff paste (`FRONTEND_COLLABORATOR_HANDOFF_FA.md`) after merge

## Evidence parents

- `docs/COLLABORATOR_DEPLOY.md` (CR-011 B)
- `docs/development/git-development-workflow.md` (Binding)
- `docs/development/standards/pr-checklist.md` (Accepted)
- `docs/architecture/CANON-LOCK.md`
- Board Knowledge gates (no dual-write / RAG)
