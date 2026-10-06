# Canonical ownership model (deployment)

## Who should own the repo checkout?

`/opt/karzar/Karzar` and `/opt/karzar/frontend` must be owned by **`github-runner:github-runner`**.

Rationale: Deploy Staging rsync runs as `github-runner` with `-a --delete` into these trees.

## Who should own deploy/services?

- `/opt/karzar/Karzar/deploy/**` → `github-runner:github-runner`
- `/opt/karzar/Karzar/services/**` → `github-runner:github-runner`

These are Git-tracked application/deploy assets synced by rsync. They are **not** root runtime state.

## Who should own generated audit artifacts?

- **Preferred:** write audit packs into the developer/agent workspace / PR branch, then land via Git + deploy rsync (owner = github-runner after sync).
- **If generating on the VPS:** write under a runner-writable ops area **outside** the live checkout (e.g. `/opt/karzar/logs/` or `/opt/karzar/ops-artifacts/`), never as root into `/opt/karzar/Karzar/audit/`.
- Untracked VPS-only audit directories under the live checkout are **forbidden** for root.

## Paths that genuinely require root ownership

| Path | Why |
| --- | --- |
| `/opt/karzar` top-level | host layout |
| `/opt/karzar/Karzar/.env` | secrets; mode 640 root:github-runner; **rsync-excluded** |
| `/opt/karzar/.deploy-secrets` | secrets outside checkout |
| system nginx/certs under `/etc` | OS services (not the Git checkout) |

## Paths that must be writable by github-runner

- `/opt/karzar/incoming` (setgid 2775)
- `/opt/karzar/workspace`, `/opt/karzar/mirror`, `/opt/karzar/logs`
- Entire `/opt/karzar/Karzar` tree except rsync-excluded secrets/uploads/backups/logs
- `/opt/karzar/frontend`

## Explicitly reject

- `chmod -R 777`
- Broad recursive chown of `/opt/karzar` including secrets/volumes
- Running operational tooling as root inside the live Git checkout
