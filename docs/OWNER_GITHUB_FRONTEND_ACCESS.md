# Owner checklist — GitHub access for frontend collaborator

**Who:** `@Shebahati` only (agent tokens cannot change collaborators / branch protection).  
**Collaborator GitHub user:** [`mhrbzandi-Designer`](https://github.com/mhrbzandi-Designer) (Mehrab Zandi)  
**Goal:** Write + ability to squash-merge after gates + ability to run **Deploy Staging**; Production remains Owner-gated. Staging = live VPS.

Agent verified (2026-08-01): invite API returned **403** for the cloud token; collaborators list currently shows only `Shebahati`. You must click the steps below in the GitHub UI.

---

## A. Invite collaborator (Write)

1. Open https://github.com/Shebahati/Karzar/settings/access  
2. **Add people** → `mhrbzandi-Designer`  
3. Permission: **Write** (not Admin)  
4. Send invitation → confirm they Accept  

Optional later: if they only need Actions without merge, Write is still required to run `workflow_dispatch` on private repos in typical setups.

---

## B. Branch protection on `main`

Open https://github.com/Shebahati/Karzar/settings/branches → rule for `main` (create if missing):

| Setting | Value |
|---------|--------|
| Require a pull request before merging | **On** |
| Require approvals | **1** |
| Dismiss stale pull request approvals when new commits are pushed | **On** |
| Require review from Code Owners | **On** |
| Require status checks to pass | **On** |
| Status checks (exact job names) | `storefront`, `admin-panel`, `Collaborator Scope Gate` — add `storefront-e2e` when stable enough to block |
| Require branches to be up to date before merging | **On** (recommended) |
| Do not allow bypassing the above settings | **On** for everyone except you if you need break-glass; prefer no bypass |
| Restrict who can push to matching branches | **On** — only via PR |
| Allow force pushes | **Off** |
| Allow deletions | **Off** |

Effect with [`.github/CODEOWNERS`](../.github/CODEOWNERS):

- Frontend paths: code owners `@Shebahati` + `@mhrbzandi-Designer` — **author cannot satisfy their own review**; your Approve is still required for their PRs.  
- After your Approve + green checks, **they** may press Squash and merge (Write).  
- Non-frontend / Canon / backend paths: Owner-only in CODEOWNERS; scope-gate fails their PR if they touch those paths.

---

## C. Actions / Environments

1. https://github.com/Shebahati/Karzar/settings/actions — allow Actions; Workflow permissions: **Read and write** only if required by existing deploy workflows (do not loosen beyond current working deploy).  
2. Environment **`staging`**: allow `mhrbzandi-Designer` to deploy (Required reviewers: leave empty or only yourself if you want a second click; empty = they can Run workflow after merge).  
3. Environment **`production`**: keep required reviewer **`Shebahati`** + wait timer + typed `deploy-production` confirm. Do **not** add the FE collaborator as production reviewer unless you explicitly decide later.

Deploy docs: [`COLLABORATOR_DEPLOY.md`](./COLLABORATOR_DEPLOY.md) (`CR-011` Option B — merge does **not** auto-deploy).

---

## D. After invite — smoke the human path

1. Collaborator accepts invite.  
2. They open a tiny no-op or docs-only frontend PR (or wait for real work).  
3. You Approve once → they squash-merge → they Run **Deploy Staging** → smoke www/admin/api `/ready`.

---

## E. Charter they must follow

Send the paste-ready message:

[`FRONTEND_COLLABORATOR_HANDOFF_FA.md`](./FRONTEND_COLLABORATOR_HANDOFF_FA.md)

Canonical rules:

[`FRONTEND_COLLABORATOR_CHARTER.md`](./FRONTEND_COLLABORATOR_CHARTER.md)

---

## F. What the agent already landed in Git

- Charter + this Owner checklist  
- Hardened `CODEOWNERS`  
- CI job **Collaborator Scope Gate** (fails non-Owner PRs that touch forbidden paths)  
- Links from `COLLABORATOR_DEPLOY.md` / `frontend/README.md` / PR template  

Merge that PR to `main` before relying on the scope gate in protection rules.
