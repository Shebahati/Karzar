# Contributing to Karzar

## Branch & PR hygiene

- Branch names: `fix/…`, `feat/…`, `chore/…`, `docs/…`
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
