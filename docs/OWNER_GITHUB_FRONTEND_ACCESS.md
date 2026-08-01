# Owner checklist — GitHub access for frontend collaborator (no Owner review)

**Who:** `@Shebahati` only (agent tokens cannot change collaborators / branch protection).  
**Collaborator:** [`mhrbzandi-Designer`](https://github.com/mhrbzandi-Designer)  
**Policy (Owner decision 2026-08-01):** FE merges and Deploy Staging **without** waiting for your review. Safety = path allowlist CI + Frontend CI + branch protection status checks. Production stays Owner-only. Staging = live VPS.

Agent invite API = **403**. You must click below.

---

## A. Invite collaborator (Write)

1. https://github.com/Shebahati/Karzar/settings/access  
2. **Add people** → `mhrbzandi-Designer` → permission **Write** (not Admin)  
3. They must **Accept**

---

## B. Branch protection on `main` (self-merge + CI-only)

https://github.com/Shebahati/Karzar/settings/branches → rule for `main`:

| Setting | Value |
|---------|--------|
| Require a pull request before merging | **On** |
| Require approvals | **0** (Owner review not required) |
| Require review from Code Owners | **Off** (otherwise FE cannot self-merge) |
| Require status checks to pass | **On** |
| Required status checks | `storefront` · `admin-panel` · `Collaborator Scope Gate` · prefer also `storefront-e2e` |
| Require branches to be up to date before merging | **On** |
| Restrict who can push to matching branches | **On** — no direct `main` pushes |
| Allow force pushes | **Off** |
| Allow deletions | **Off** |
| Allow specified actors to bypass required pull requests | **Off** (or only you for break-glass) |

CODEOWNERS remains for **notifications / ownership clarity**; it must **not** be a required review gate while this policy is active.

Non-Owner PRs that touch backend/Canon/OpenAPI still fail **Collaborator Scope Gate**. Package.json / lockfile changes by FE also fail that gate.

---

## C. Actions / Environments

1. Staging environment: **no** required reviewers (so they can Run **Deploy Staging** alone).  
2. Production environment: required reviewer **`Shebahati`** + wait timer + typed `deploy-production` — do **not** add FE.  
3. Remind them: merge does **not** auto-deploy (`CR-011` B); they must Run workflow manually.

---

## D. After setup

1. Merge the gates PR to `main` (so Scope Gate exists).  
2. Confirm protection lists the three (or four) check names exactly.  
3. Send paste from [`FRONTEND_COLLABORATOR_HANDOFF_FA.md`](./FRONTEND_COLLABORATOR_HANDOFF_FA.md).  
4. Optional: watch their first Deploy Staging smoke once; no Approve needed on PRs.

---

## E. Risk acceptance

Without human review, a green CI can still ship a bad UX. Residual controls:

- path allowlist + lockfile freeze for FE  
- tsc / lint / unit / (e2e if required)  
- staging = production host → they must smoke after every deploy  
- you retain Production + backend/Canon paths  

If this becomes too risky later: set Require approvals back to **1**.
