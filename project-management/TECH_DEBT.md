# Tech Debt

- [x] TD-001 Admin FE depth-2|3 selectable aligned (isLayer3Leaf removed; docs fixed)
- [ ] Legacy docs drift (GO_LIVE_EXECUTION_PLAN vs live site)
- [ ] Multiple long-lived enrichment worktrees to prune
- [ ] Hero/CMS image precedence edge cases — monitor after #84
- [x] Coverage threshold prose aligned to enforced **68%** (AODS `CR-003` Option A, 2026-07-30) — SoT: `pyproject.toml` + `backend-ci.yml`
- [x] Branch naming Canon `feature/*` (AODS `CR-002` Option A, 2026-07-30) — `feat/*` grandfathered; no mass-rename
- [ ] Coverage gate noise when tests fail early
- [x] PMO progress ledgers duplicated — **CLOSED** 2026-07-30 (AODS `CR-007` Option A: `progress/`+`sprints/` canonical)
- [x] `openapi/v1.json` snapshot drift vs app — regenerated 2026-07-30; CI job `aods` verifies via `--gate openapi` (AODS `CR-012` CLOSED / Phase 4)
- [ ] PR checklist is Accepted but `pull_request_template.md` does not exist (AODS `CR-018`)
- [ ] Pytest markers/options declared twice (`pytest.ini` + `pyproject.toml`) (AODS `CR-016`)
- [ ] 58 unmerged remote branches, 45 local worktrees (AODS `CR-017`)
- [ ] 0 validator findings in `aods/registry/validation-baseline.json` (emptied 2026-07-30 with `CR-023`); file may only shrink without HC-14
- [x] **OI-GOV-02** Add `aods` to Protect main required checks — closed 2026-07-30 (admin applied; verify OK)
