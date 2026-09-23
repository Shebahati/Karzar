# PROMPT 85 RESULT

STATUS: COMPLETE (code/workflow cutover only; no deploy executed)

## Summary

Deploy Staging cut over from GitHub-hosted SSH handoff to self-hosted
`package-incoming-local` + local FE image build/save. Freeze gate remains
on `ubuntu-latest`. Live sync / compose / alembic remain in the existing
deploy job and were **not** executed by this prompt.

## Workflow change

- `deploy-freeze`: unchanged (main + `KARZAR_DEPLOY_FREEZE`)
- `package`: `[self-hosted, karzar-vps]` — mirror → package → FE images → incoming
- `deploy`: unchanged safety (verify, live rsync, rebuild, smoke, `environment: staging`)
- `cleanup`: `[self-hosted, karzar-vps]` local delete (`SSH_HOST` unset)

Removed from Deploy Staging invocation: `push-incoming-source.sh`,
`push-incoming-frontend-images.sh`, GitHub SSH secrets usage.

## Frontend handling

- **Was:** GitHub-hosted `build-staging-frontend-images.sh` + SSH rsync of tar bundle
- **Now:** same build script on VPS during package (`KARZAR_PACKAGE_DRY_RUN=0`),
  `docker save` into `incoming/<sha>/frontend-images`, marker `transport=local-package`
- **Deploy job:** still loads prebuilt only (`KARZAR_REQUIRE_PREBUILT_FRONTEND_IMAGES=1`);
  no npm/docker build in Sync+rebuild job
- **Blocker to watch:** VPS needs docker buildx + registry.npmjs.org reachability;
  GHA build cache disabled on self-hosted (`KARZAR_USE_GHA_CACHE=0`)

## Tests

- `test-package-incoming-local.sh` PASS
- `test-delta-rsync-handoff.sh` PASS (incl. `WORKFLOW_SELF_HOSTED_PACKAGE`)
- `cleanup-incoming-source.sh --selftest` PASS
- `test-prebuilt-frontend-handoff.sh` PASS

## Non-goals confirmed

No deploy, alembic, container restart, VPS runtime mutation, or Wave ops.
