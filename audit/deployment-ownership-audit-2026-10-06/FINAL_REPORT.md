# FINAL REPORT — Deployment ownership audit

## A. Status

COMPLETE — classification `ROOT_CAUSE_PARTIALLY_PROVEN` (multiple causes).

## B. Safety

No VPS ownership mutation, no deploy, no DB mutation during this audit.

## C. Identity

| Item | Value |
| --- | --- |
| origin/main | `59716cd779d3bf981be2ad8096c70d0bd9f080b1` (PR #438) |
| deployed SHA | `4e750eafb00f8b6e72c4dba9c539d409c0fd8a02` (PR #439) |
| main vs deployed | main ahead by 8 commits; **not deployed** in this task |
| runner service user | `github-runner` |
| SSH interactive login observed | `root` |

## D. Failed rsync

Run `37468470923`: github-runner `rsync -a --delete` from incoming tree → `/opt/karzar/Karzar` exit 23.

Failures: cannot unlink root-owned orphan `audit/insize-price-20-*`; cannot mkstemp into root-owned `deploy/staging` and `services/gsc_mcp`; cannot chgrp those dirs.

## E. Ownership findings

**Expected root:** `/opt/karzar`, `.env`, `.deploy-secrets`.

**Unexpected at failure:** `deploy/`, `deploy/staging/`, `services/`, `services/gsc_mcp/**`, orphan `audit/insize-price-20-*`.

**Current (post-success):** deploy-managed tree github-runner-owned; orphans gone; only expected secret root ownership remains under checkout (`.env`).

## F. Orphans

Four untracked `audit/insize-price-20-*` directories existed on VPS only (not on `main`). Exact creating command unproven (`CREATOR_UNPROVEN`); ownership root:root and same-day mtime align with root operational INSIZE price work. Successful redeploy deleted them via `--delete`.

## G. Root cause

```text
classification: ROOT_CAUSE_PARTIALLY_PROVEN
classes: multiple causes
  1) root-executed operational tooling inside live checkout (PROVEN: /root/.bash_history docker compose gsc_mcp; SSH as root)
  2) untracked root-owned orphan audit dirs blocking rsync --delete (PROVEN existence/effect; creator unproven)
  3) deployment workflow defect/gap: no ownership preflight before rsync (PROVEN absence)
```

## H. Risk

Next deploy recurrence risk: **HIGH** if operators continue writing as root into `/opt/karzar/Karzar`. Other workflows using the same live tree inherit the same failure mode.

## I. Proposed fix

See `REMEDIATION_PLAN.md` + `PREFLIGHT_DESIGN.md`. Mutation authorized: **NO** in this task.

## J. Canonical model

See `CANONICAL_OWNERSHIP_MODEL.md`.
