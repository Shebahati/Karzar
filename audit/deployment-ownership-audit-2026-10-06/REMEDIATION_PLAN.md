# Remediation plan (NOT EXECUTED)

## Root cause summary

Multiple causes, primarily **root SSH / root operational tooling writing into the live checkout**, plus **workflow gap** (no ownership preflight before rsync).

## One-time remediation (narrow; requires Owner authorization)

Only if drift returns before next deploy:

```text
chown -R github-runner:github-runner \
  /opt/karzar/Karzar/deploy \
  /opt/karzar/Karzar/services

# Remove or re-own untracked root-owned orphans under audit/ that are not on main:
# identify with: find ... -user root; then either delete (if untracked junk) or chown.
```

Do **not** chown `.env`, `.deploy-secrets`, Docker volumes, or `/opt/karzar` top-level wholesale.

Current post-success state (2026-10-06 audit): live tree already github-runner-owned except expected `.env`; orphans already deleted by successful rsync. One-time chown may be **NO-OP** unless new drift appears.

## Workflow hardening

1. Add a **read-only preflight** step before `Sync backend` (see `PREFLIGHT_DESIGN.md`).
2. Document: never `ssh` as root into `/opt/karzar/Karzar` for file creation; use `sudo -u github-runner` or write outside checkout.
3. GSC MCP / nginx ops: apply host configs from `/etc` as root, but update Git-tracked `deploy/` / `services/` only via deploy pipeline or as github-runner.
4. Optionally extend `prepare-self-hosted-dirs.sh` notes: it intentionally does **not** chown the live tree — do not misuse it as a live-tree fixer.

## Practice change

- Operator SSH key currently lands as **root** (`PermitRootLogin yes`). Prefer a non-root deploy/ops user for day-to-day SSH, with explicit sudo for nginx/docker only.
