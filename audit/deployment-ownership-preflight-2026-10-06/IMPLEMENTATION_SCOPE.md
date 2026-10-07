# Implementation scope

## Allowed (this PR)

| Area | Paths |
|------|--------|
| Preflight script | `deploy/staging/scripts/deploy_ownership_preflight.py` |
| Workflow integration | `.github/workflows/deploy-staging.yml` |
| Tests | `tests/test_deploy_ownership_preflight.py`, `tests/test_ops_phase0_guards.py` |
| Ops docs | `docs/OPERATIONS.md`, `docs/integrations/google-search-console-mcp.md` |
| Evidence | `audit/deployment-ownership-preflight-2026-10-06/**` |
| AODS | `aods/registry/document-registry.yaml`, `aods/tools/aods_validate.py` naming allow |

## Forbidden (verified)

```text
VPS chown/chmod          NO
live rsync / deploy      NO
database mutation        NO
catalog / sellability    NO
product naming APPLY     NO
GSC feature redesign     NO
auto-chown in workflow   NO
```

## OUT_OF_SCOPE

```text
OUT_OF_SCOPE = 0
```

No catalog, commerce, naming, or GSC feature changes beyond documenting the
ownership invariant for root compose operations.
