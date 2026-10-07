# AUTHORIZATION — Phase C/D Cleanup

Owner authorized ONE narrowly scoped VPS cleanup:

- DELETE exactly the 8 frozen paths in `PHASE_C_DELETE_ROOTS.txt` / `FROZEN_DELETE_ALLOWLIST.txt`
- `PHASE_D_CHOWN_PATHS = 0` → chown forbidden, chmod forbidden
- No deploy, no PR merge, no preserve mutation, no database mutation

Historical preservation manifests retain `safe_to_remove_source = NO` (pre-cleanup truth).
This closeout records that Owner authorization later permitted live-source deletion.
