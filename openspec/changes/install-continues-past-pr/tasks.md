## 0. Delivery start

- [x] 0.1 Run `agent-process start_change install-continues-past-pr --planner Claude --implementer Claude` (tracking issue 483), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_planning_workflow.py` add `test_install_continues_past_the_installation_pr`: in the Install section's step 4 (between ` 4. ` and ` 5. `, as `test_install_names_the_skill_marker` cuts it) assert `agent-process wait_for_pr <PR>`, `exit 3`, `rerun once`, `show the person`, `ekolvah/agent-process-distribution`, `gh pr view <PR> --json state`, `MERGED` and `same session`
- [x] 1.2 Run `agent-process check_red tests/publisher/test_planning_workflow.py::test_install_continues_past_the_installation_pr` and commit RED with these ticks

## 2. Install continues past the PR

- [x] 2.1 `skills/agent-process/SKILL.md` Install step 4 per design D2, D2b, D3: it ends with `agent-process wait_for_pr <PR>`, the handling of its exits (a first exit 3 rerun once, a second shown, quality fixed by a commit, threads and other failures shown to the person, a P0/P1 thread on an installer-managed file proposed as an issue in `ekolvah/agent-process-distribution`), the merge request, `gh pr view <PR> --json state`, on another state the state shown and install stopped, on `MERGED` the switch and pull, and steps 5–6 in the same session; step 5 is unchanged (D2a), and no sentence of step 4 ends in `5.`, which would cut the test's slice; the prose uses the asserted phrases verbatim (`show the person`, not `shows the person`). Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` is green, then commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change install-continues-past-pr`, then `gh pr create --title "feat: install-continues-past-pr" --body-file <report>`. The report names tracking issue 483 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, goal 3, §I, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Installation PR merged | `tests/publisher/test_planning_workflow.py::test_install_continues_past_the_installation_pr` |
