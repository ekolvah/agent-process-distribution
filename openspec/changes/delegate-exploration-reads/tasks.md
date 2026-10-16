## 0. Delivery start

- [x] 0.1 After issue 414 (`goal-function-every-session`) has merged, run `agent-process start_change delegate-exploration-reads --planner Claude --implementer Claude` (tracking issue 424), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists
- [ ] 0.2 Compare *The skill carries the principles core and harness tactics* in `openspec/specs/roles/spec.md` with this change's roles delta, apart from the delegation sentence and the scenario's `Explore` clause; if they differ, rewrite the delta on the merged text and commit it; verify `openspec validate delegate-exploration-reads --strict`

## 1. RED

- [ ] 1.1 Extend `test_skill_carries_principles_core_and_harness_tactics` in `tests/publisher/test_plugin.py` as design D2 says
- [ ] 1.2 Run `agent-process check_red tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics` and commit RED with these ticks

## 2. Tactic

- [ ] 2.1 Replace the subagent bullet of `## Claude harness` in `skills/agent-process/always-on.md` with the text of design D1 (spec roles: The skill carries the principles core and harness tactics); verify the node of 1.2 passes
- [ ] 2.2 Commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Open the measurement issue of design D3 with `gh issue create`, its body carrying D3's comparison and the revert condition of Risks, and set its area with `agent-process set_status <N> --area "Token efficiency"`; verify `gh issue view <N>` shows the body
- [ ] 4.2 Run `agent-process archive_change delegate-exploration-reads`, then `gh pr create --title "feat: delegate-exploration-reads" --body-file <report>`; the report names tracking issue 424 as a plain reference and carries the scenario-to-test map and names the measurement issue of 4.1
- [ ] 4.3 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| roles / A consumer reads principles and tactics from the skill | `tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics` |
