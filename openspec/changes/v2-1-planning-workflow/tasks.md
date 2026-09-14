## 1. OpenSpec configuration

- [ ] 1.1 `openspec schema fork spec-driven agent-process`; insert `architect-review` between `design` and `tasks`; `openspec schema validate agent-process`
- [ ] 1.2 `config.yaml` rules: `proposal` (bug: reproduction + root cause first), `tasks` (RED first, scenario → named test or `n/a`), `architect-review` (principles §I–VII, unmapped scenario is a finding)
- [ ] 1.3 Test: `test_roles_and_carriers` — schema artifact list and rules keys match this change's spec

## 2. Skills and scripts

- [ ] 2.1 `agents/architect-reviewer.md` writes `architect-review.md` from `openspec instructions architect-review --json`
- [ ] 2.2 `skills/implement-change/SKILL.md`: tracking issue (ask priority) → `gh issue develop -c` → `set_status In progress` → follow `openspec-apply-change` → `ci_check` → PR → `wait_for_pr`; re-run on an open PR reads unresolved threads
- [ ] 2.3 `scripts/check_red.py`, `scripts/set_status.py`, `scripts/wait_for_pr.py`; tests named after the scenarios `Behavioural change`, `Tracking issue created`, `Pending review`
- [ ] 2.4 Remove `/plan`, `discovery` subagent, `validate_issue_status.py`, `.agents/skills/plan-issue`, `.agents/skills/implement-issue`, planner/implementer runbooks

## 3. Verify

- [ ] 3.1 Plan and implement one real change with Claude and one with Codex on this repository; both end in `wait_for_pr`
- [ ] 3.2 `openspec validate --strict --all` green; `openspec archive v2-1-planning-workflow` after merge
