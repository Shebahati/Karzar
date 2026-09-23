# PROMPT 81 RESULT

STATUS: COMPLETE (prep + dry-run only; no deploy cutover)

## Filesystem

BEFORE:
- `/opt/karzar/incoming` → `root:root 755`
- `/opt/karzar/workspace` → MISSING
- `/opt/karzar/mirror` → MISSING
- `/opt/karzar/logs` → MISSING
- `/opt/karzar/logs/deploy` → MISSING

AFTER (`prepare-self-hosted-dirs.sh` as root, once):
- `/opt/karzar/incoming` → `github-runner:github-runner 2775`
- `/opt/karzar/workspace` → `github-runner:github-runner 755`
- `/opt/karzar/mirror` → `github-runner:github-runner 755`
- `/opt/karzar/logs` → `github-runner:github-runner 755`
- `/opt/karzar/logs/deploy` → `github-runner:github-runner 755`
- `WORLD_WRITABLE_COUNT=0`

## Mirror

- bare mirror: `/opt/karzar/mirror/Karzar.git` (public HTTPS; no deploy key)
- no live-tree checkout under `/opt/karzar/Karzar`
- `MIRROR_HAS_SHA=5524453824d49ed40b154bc10ab8bd0e018efb4c`
- detached worktree checkout verified (`MIRROR_CHECKOUT_OK`), then removed

## Package

- path: SHA → workspace checkout → tracked tree → manifest → `incoming/<sha>`
- VPS proof: `MANIFEST_OK sha256=96daddd5… files=1717 bytes=84030287`
- `transport=local-package` in `HANDOFF_COMPLETE`
- `INCOMING_OWNER=github-runner:github-runner`
- dry-run skips frontend docker image build (`FRONTEND_IMAGES=SKIPPED`)

## Dry run

PASS (local `test-package-incoming-local.sh` + VPS `dry-run-self-hosted-package.sh`):
- checkout ✓
- package ✓
- manifest ✓
- incoming write ✓
- checksum / consume verify ✓ (`MANIFEST_SHA_MATCH=YES`, `HANDOFF_OK … transport=local-package`)
- cleanup simulation ✓ (`CLEANUP_SIM_OK`; incoming removed)

Unchanged during VPS dry-run:
- live `/opt/karzar/Karzar` mtime
- live `/opt/karzar/frontend` mtime
- alembic `n7o8p9q0r1s2`

MUST NOT / DID NOT:
- docker compose up
- container rebuild
- alembic upgrade
- live rsync
- DB writes

## Security

- no GitHub SSH deploy key in package/mirror/dry-run scripts (`NO_SSH_DEPLOY_KEY_IN_PACKAGE_PATH`)
- no sudo in normal runner package path (prepare dirs is one-time root)
- no secrets in markers (sha, transport, files, bytes, manifest only)

## Files changed

- `deploy/staging/scripts/deploy-tree-lib.sh` — accept `local-package` transport
- `deploy/staging/scripts/prepare-self-hosted-dirs.sh` (new)
- `deploy/staging/scripts/ensure-git-mirror.sh` (new)
- `deploy/staging/scripts/package-incoming-local.sh` (new)
- `deploy/staging/scripts/dry-run-self-hosted-package.sh` (new)
- `deploy/staging/scripts/test-package-incoming-local.sh` (new)
- `.github/workflows/deploy-staging-self-hosted-package-dry-run.yml` (new)
- `docs/OPERATIONS.md` — Phase 1 local-package note
- `audit/insize-phase3/PROMPT_81_RESULT.md` (this file)

## Runtime impact

- Deploy Staging workflow unchanged (still GitHub-hosted SSH handoff)
- freeze not modified
- live compose / containers untouched

## Database

- none (alembic remained `n7o8p9q0r1s2`)

## Deploy

- none (no Deploy Staging; no compose; no live sync)

## Wave

- none

## Blockers

- none for Phase 1 prep/dry-run
- Phase 2+ still required to cut over Deploy Staging package job to self-hosted path and to implement FE image build when `KARZAR_PACKAGE_DRY_RUN=0`

STOP.
