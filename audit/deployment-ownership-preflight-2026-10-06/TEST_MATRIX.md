# Test matrix

| Case | Coverage | Result |
|------|----------|--------|
| All managed paths runner-owned → PASS | `test_pass_all_runner_owned` | PASS |
| Root-owned replace target → FAIL | `test_root_owned_replace_target_fails` | PASS |
| Root/foreign dest-only `--delete` hazard → FAIL | `test_destination_only_undeletable_detected` | PASS |
| Non-writable parent → FAIL | `test_unreplaceable_when_parent_not_writable` | PASS |
| Runner-owned nested dirs → PASS | `test_pass_all_runner_owned` | PASS |
| Expected root-only `.env` excluded → PASS | `test_expected_env_excluded_from_root_scan` | PASS |
| Root-owned outside managed scope ignored | `test_root_owned_outside_managed_ignored` | PASS |
| Spaces/unicode paths safe | `test_unicode_and_spaces_paths_in_report` | PASS |
| Missing required directory | `test_missing_optional_frontend_reports_required_missing` | PASS |
| Unexpected root execution → FAIL | `test_runner_identity_rejects_root` | PASS |
| Wrong user → FAIL | `test_runner_identity_rejects_wrong_user` | PASS |
| Historical class modelled; dry-run only | `test_historical_failure_model_preflight_before_rsync` | PASS |
| Workflow orders preflight before rsync; no auto-chown | `test_workflow_orders_preflight_before_rsync`, `test_deploy_staging_ownership_preflight_before_rsync_no_autochown` | PASS |

Command:

```bash
pytest tests/test_deploy_ownership_preflight.py tests/test_ops_phase0_guards.py -q
```
