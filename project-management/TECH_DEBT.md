# Tech Debt

- [x] TD-001 Admin FE depth-2|3 selectable aligned (isLayer3Leaf removed; docs fixed)
- [ ] Legacy docs drift (GO_LIVE_EXECUTION_PLAN vs live site)
- [ ] Multiple long-lived enrichment worktrees to prune
- [ ] Hero/CMS image precedence edge cases — monitor after #84
- [ ] Coverage gate noise when tests fail early
- [ ] Coverage threshold stated as 62/67/67/68% across four documents; enforced value is 68 (AODS `CR-003`)
- [x] PMO progress ledgers duplicated — **CLOSED** 2026-07-30 (AODS `CR-007` Option A: `progress/`+`sprints/` canonical)
- [x] `openapi/v1.json` snapshot drift vs app — regenerated 2026-07-30; CI job `aods` verifies via `--gate openapi` (AODS `CR-012` CLOSED / Phase 4)
- [ ] PR checklist is Accepted but `pull_request_template.md` does not exist (AODS `CR-018`)
- [ ] Pytest markers/options declared twice (`pytest.ini` + `pyproject.toml`) (AODS `CR-016`)
- [ ] 58 unmerged remote branches, 45 local worktrees (AODS `CR-017`)
- [ ] 31 validator findings recorded as visible debt in `aods/registry/validation-baseline.json`; the file may only shrink
- [ ] **OI-GOV-02** Add `aods` to Protect main required checks — script ready: `bash scripts/ops_require_aods_status_check.sh` (repo admin); UI: https://github.com/Shebahati/Karzar/rules/19696648
