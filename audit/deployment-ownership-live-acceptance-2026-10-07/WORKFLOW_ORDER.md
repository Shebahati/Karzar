# Workflow order proof — run 37601628972

```text
PREFLIGHT_FINISHED_BEFORE_REAL_RSYNC = YES
```

| Step | UTC (log) | Evidence |
|------|-----------|----------|
| Incoming package (self-hosted) | ~09:35:21–09:37 | job success before Sync |
| Ownership preflight (fail-closed before rsync) | 09:37:24.928 start | step name explicit |
| Preflight PASS | **09:37:25.4036902Z** | `status=PASS unexpected_ownership=0` |
| Sync backend → /opt/karzar/Karzar | **09:37:25.4306691Z** | `rsync -a --delete` after preflight |
| Rebuild/restart | 09:37:28+ | compose rebuild |
| Cleanup incoming | after deploy job | success |

Critical invariant: preflight `status=PASS` timestamp precedes Sync backend `##[group]` timestamp.
