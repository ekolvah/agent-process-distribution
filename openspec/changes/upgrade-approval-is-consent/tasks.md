## 0. Delivery start

- [x] 0.1 Run `agent-process start_change upgrade-approval-is-consent --planner Claude --implementer Claude` (tracking issue 485), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_planning_workflow.py` add `test_upgrade_approval_is_its_consent`, slicing `_section("Install")` with the `split(" N. ", 1)` idiom of `test_install_continues_past_the_installation_pr`: step 3 names `Ask once`, `manual agent-identity`, `project-copy`, `project-link`, `pre-push`, `project-areas`, `task-readings-url`, `task-readings-token` and `task-readings-dashboard`; step 4 names `gh pr merge <PR> --auto --squash`, `approve` and `manual protection`
- [x] 1.2 Run `agent-process check_red tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` and commit RED with these ticks

## 2. Unasked upgrade

- [ ] 2.1 `skills/agent-process/SKILL.md` Install steps 3 and 4 per design D1–D4. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` is green, then commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change upgrade-approval-is-consent`, then `gh pr create --title "feat: upgrade-approval-is-consent" --body-file <report>`. The report names tracking issue 485 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 2, goal 3, §I, §VII)
- [ ] 4.2 Run `gh pr merge <PR> --auto --squash`, then `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Upgrade with the agent's identity | `tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` |
| distribution / Write outside the PR or no agent identity | `tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` |
| distribution / Installation PR merged | `tests/publisher/test_planning_workflow.py::test_install_continues_past_the_installation_pr` (unchanged) |
| distribution / Unasked upgrade PR merged | `tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` |
