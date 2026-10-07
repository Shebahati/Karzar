# Deployment ownership / rsync permission audit — 2026-10-06

Read-only audit after Deploy Staging run `37468470923` failed on rsync permissions,
then recovered via ownership fix + run `37469215878`.

## Safety

```text
VPS_FILE_MUTATION = NO
CHOWN / CHMOD / DELETE / DEPLOY = NO
```

## Verdict

`ROOT_CAUSE_PARTIALLY_PROVEN` — multiple causes; strongest evidence is root SSH /
root operational tooling (GSC MCP compose) writing into the live checkout, plus
untracked root-owned orphan audit dirs blocking `rsync --delete`.

See `FINAL_REPORT.md`.
