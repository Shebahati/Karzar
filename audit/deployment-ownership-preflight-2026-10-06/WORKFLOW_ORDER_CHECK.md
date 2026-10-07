# Workflow order check

Source: `.github/workflows/deploy-staging.yml`

## Job graph

```text
deploy-freeze   (ubuntu-latest)
    │  enforces refs/heads/main + KARZAR_DEPLOY_FREEZE != true
    ▼
package         (self-hosted karzar-vps)
    │  mirror → incoming/<sha>/tree + FE images
    ▼
deploy          (self-hosted karzar-vps, environment: staging)
    │
    ├─ Diagnose incoming permissions
    ├─ Verify incoming source
    ├─ Verify incoming frontend images handoff
    ├─ Ownership preflight (fail-closed before rsync)   ← NEW
    ├─ Sync backend → /opt/karzar/Karzar                ← real rsync
    ├─ Sync frontend → /opt/karzar/frontend
    └─ Rebuild backend + frontend + smoke
```

## Freeze safety

| Concern | Behavior |
|---------|----------|
| Freeze gate position | Before any VPS package/deploy work |
| Preflight vs freeze clear | Workflow never writes `KARZAR_DEPLOY_FREEZE`; Owner clears/restores the Actions variable |
| Preflight FAIL | Job exits nonzero before Sync backend; no partial live rsync; no compose rebuild |
| Freeze after FAIL | Remains whatever Owner set for the attempt; Owner should restore `true` |

Preferential note: VPS path preflight cannot run on the ubuntu freeze job (paths are
on the self-hosted runner). Ordering freeze → package → verify → **preflight** →
rsync is the compatible architecture.

## Auto-chown

```text
chown -R … in deploy-staging.yml = ABSENT
sudo chown in deploy-staging.yml = ABSENT
```

Structural tests: `test_workflow_orders_preflight_before_rsync`,
`test_deploy_staging_ownership_preflight_before_rsync_no_autochown`.
