## 0. Delivery

- [ ] 0.1 Tracking issue for this change (ask the person for the priority, set the Project field); `gh issue develop -c <N>`; status by hand (`set_status` is created below)

## 1. OpenSpec configuration

- [ ] 1.1 `openspec schema fork spec-driven agent-process`; insert `architect-review` between `design` and `tasks`; `openspec schema validate agent-process`
- [ ] 1.2 `config.yaml` rules: `proposal` (bug: reproduction + root cause first), `tasks` (RED first, scenario → named test or `n/a`), `architect-review` (principles §I–VII, unmapped scenario is a finding)
- [ ] 1.3 The delivery tasks of `v2-2` … `v2-6` `tasks.md` are the template's output (written by hand in #105); the rule reproduces them
- [ ] 1.4 Test: `test_roles_and_carriers` — schema artifact list and rules keys match this change's spec

## 2. Skills and scripts

- [ ] 2.1 `agents/architect-reviewer.md` writes `architect-review.md` from `openspec instructions architect-review --json`
- [ ] 2.2 `config.yaml` `tasks` rule: delivery-tasks template — tracking issue (ask priority) → `gh issue develop -c` → `set_status In progress` → … → `ci_check` → PR → `wait_for_pr`, apply unresolved threads, repeat → `finish_change <change>`; a re-run of `openspec-apply-change` on an open PR continues at the first unchecked task
- [ ] 2.3 `scripts/check_red.py`, `scripts/set_status.py`, `scripts/wait_for_pr.py`, `scripts/finish_change.py` (marks its task, `archive -y`, commit, push, `wait_for_pr`); tests named after the scenarios `Behavioural change`, `Tracking issue created`, `Archive commit`, `Pending review`
- [ ] 2.4 Remove `/plan`, `discovery` subagent, `validate_issue_status.py`, `.agents/skills/plan-issue`, `.agents/skills/implement-issue`, planner/implementer runbooks

## 3. Verify

- [ ] 3.1 Plan and implement one real change with Claude and one with Codex on this repository; both end in `wait_for_pr`
- [ ] 3.2 `openspec validate --strict --all` green

## 4. Deliver

- [ ] 4.1 `ci_check` green; open the PR (body: change name, tracked deferrals as issue links)
- [ ] 4.2 `wait_for_pr`; apply every unresolved thread or reply on the one left to the person; repeat until nothing is unresolved
- [ ] 4.3 `finish_change v2-1-planning-workflow` — marks this task, `openspec archive v2-1-planning-workflow -y`, commit, push, `wait_for_pr` on that head
