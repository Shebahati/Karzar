# Frontend collaborator gates + Owner GitHub access pack

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Owner order** | Invite FE to merge+deploy without contradicting code/docs |
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
2. Branch protection on `main` per Owner checklist (required reviews + Code Owners + status checks including `Collaborator Scope Gate`)
3. Environment `staging` deploy access for collaborator; keep `production` Owner-only
4. Send handoff paste after this PR merges

## Evidence parents

- `docs/COLLABORATOR_DEPLOY.md` (CR-011 B)
- `docs/development/git-development-workflow.md` (Binding)
- `docs/development/standards/pr-checklist.md` (Accepted)
- `docs/architecture/CANON-LOCK.md`
- Board Knowledge gates (no dual-write / RAG)
