# Contributing to Karzar

## Branch & PR hygiene

- Branch names (Canon / SoT — [`development/git-development-workflow.md`](./development/git-development-workflow.md)):
  `feature/…`, `fix/…`, `hotfix/…`, `chore/…`, `docs/…`
- **New work** must use those prefixes. Historical remote branches named `feat/…` are grandfathered until
  deleted; do **not** mass-rename them (`CR-002` Option A / `HC-04`).
- Cloud Agent may create `cursor/…` branches (platform-imposed); do not treat that as a human convention.
- One concern per PR; squash-merge; delete the branch after merge
- PR body: Summary + Test plan + audit IDs when remediating (`BE-20`, `OPS-02`, …)
- Never force-push `main`; rebase onto `origin/main` before opening a PR

## Local checks

```bash
# Backend
ruff check app tests
pytest -q

# Frontends
cd frontend/Storefront && npm ci && npm run typecheck && npm run lint && npm test
cd frontend/admin-panel && npm ci && npm run typecheck && npm run lint && npm test
```

## Transaction ownership

Endpoints own `commit`/`rollback`. Services and CRUD flush only. See [ARCHITECTURE.md](./ARCHITECTURE.md#transaction-ownership-be-01).

## Docs authority

Engineering quality bar and remediation targets: `docs/audits/v2/`.  
When site docs contradict v2, **edit the site docs** to match v2.
