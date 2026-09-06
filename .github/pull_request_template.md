## Summary
<!-- One concern. What changed and why. -->

## Authority
- Canon Lock: `docs/architecture/CANON-LOCK.md`
- Refs: <!-- Accepted ADR/RFC/spec paths that bind this change; must exist on origin/main -->
- Task: <!-- GitHub issue number, or NONE -->

## Checklist
- [ ] Branch from current `main` (`feature/*` | `fix/*` | `hotfix/*` | `chore/*` | `docs/*`; cloud `cursor/*` allowed)
- [ ] One concern per PR
- [ ] No secrets committed
- [ ] No production API default for Category A ingestion
- [ ] Schema changes include Alembic
- [ ] API shape changes regenerate `openapi/v1.json` + `docs/API_CHANGELOG.md`
- [ ] DoD for the PR type (`docs/development/standards/definition-of-done.md`)
- [ ] Relevant Accepted/Binding Canon rows cited

## Test plan
- [ ] <!-- Commands a reviewer can run -->

## Rollback
<!-- Revert commit, image, or compensating action. Never set production `PAYMENT_PROVIDER=mock`. -->
