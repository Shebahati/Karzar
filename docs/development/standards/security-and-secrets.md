# Security & Secrets

**Status:** Proposed

---

## Secrets

- Never commit `.env`, API keys, DB passwords, tokens, private leaflets dumps with credentials.  
- Use env vars / secret stores; document required names without values.  
- Rotate if accidental commit; treat as incident.

## Production boundary

- No routine production enrichment from laptops.  
- No force-push to `main`; respect branch protection.  
- Break-glass IAM ≠ Fact Approver (Data Governance).

## Dependency / supply

- Prefer pinned known packages; review new network-calling scripts.

## Logging

- No secrets in logs.  
- Audit enrichment jobs with env + git ref.

## AI

- AI System cannot Approve/Publish material Facts or change prices autonomously.
