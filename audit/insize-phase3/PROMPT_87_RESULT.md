# PROMPT 87 RESULT

STATUS: COMPLETE

## Change

Removed the `on_main` synchronization lifecycle from AODS while preserving
registry / links / naming / openapi / ingestion-boundary gates.

## Behavior

- Registered paths must exist in the worktree
- Unclassified active markdown still fails
- Branch membership is git (`origin/main`), not a registry boolean
- Links gate uses git for CR-001-style messages when a registered target is
  missing from the tree and absent from origin/main

## Non-goals

AODS not removed. App/DB/deploy workflows untouched.
