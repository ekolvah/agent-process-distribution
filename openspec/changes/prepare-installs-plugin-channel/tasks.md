## 0. Delivery start

- [x] 0.1 Run `agent-process start_change prepare-installs-plugin-channel --planner Claude --implementer Claude` (tracking issue 509), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_planning_workflow.py::test_install_names_the_skill_marker`, replace `assert "plugin-channel" in manual_step` with assertions that the Prepare part of the Install section (before ` 1. `) holds `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"`, `claude plugin install agent-process@agent-process-marketplace` and `"autoUpdate": true`, and that `manual_step` holds no `plugin-channel`; verify `agent-process check_red tests/publisher/test_planning_workflow.py::test_install_names_the_skill_marker` reports it failing, then commit RED with the group 1 ticks

## 2. Install text

- [x] 2.1 Per design D1, in `skills/agent-process/SKILL.md` Install add the Prepare bullet, drop the `plugin-channel` item from step 4, make the plugin paragraph say "by Prepare" without its `claude plugin install` copy and "a machine that followed Prepare" for "a machine that did the `plugin-channel` row", and shorten the release-tag migration sentence to Prepare's plugin step; verify `grep -n "plugin-channel" skills/agent-process/SKILL.md` is empty and `python -m pytest tests/publisher/test_planning_workflow.py -q` is green, then commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change prepare-installs-plugin-channel`, then `gh pr create --title "docs: prepare-installs-plugin-channel" --body-file <report>`. The report names tracking issue 509 as a plain reference, carries the scenario-to-test map, states that `init`'s row and the README block stay (design D1, D2), and names the principles it interacts with (goal 1, §I, §IV, §VII); then run `gh pr merge <PR> --auto --squash`
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| none | n/a: docs-only, `skip_specs: true`; the Install wording is pinned by `test_install_names_the_skill_marker` (1.1) |
