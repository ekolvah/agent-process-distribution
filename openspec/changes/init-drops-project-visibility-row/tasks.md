## 0. Delivery start

- [x] 0.1 Run `agent-process start_change init-drops-project-visibility-row --planner Claude --implementer Claude` (tracking issue 492), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_init_remote.py`: `PROJECT_ROWS` becomes `("project-workflows", "project-areas")` and `test_manual_actions_are_printed` unpacks two rows without the `"visibility" in visibility` check; `test_observed_manual_rows_are_omitted` stops setting `project.public` (the fake's default is private), so its `manual == []` proves the row gone
- [x] 1.2 Run `agent-process check_red tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted` and commit RED with these ticks

## 2. Drop the row

- [x] 2.1 Design D1, D2: in `skills/agent-process/scripts/manual.py` remove `public` from `QUERY`, from `_project_state` (docstring, return type and value) and its callers, and the `project-visibility` branch of `rows`; in `tests/publisher/init_harness.py` drop `Project.public`, `public=True` on the template, the `"public"` key of the linked answer and "visibility" from the `_project_read` docstring; in the `skills/agent-process/scripts/init.py` module docstring the `manual` rows no longer name the visibility. Verify `python -m pytest tests/publisher/test_init_remote.py -q -k manual` is green, then commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change init-drops-project-visibility-row`, then `gh pr create --title "feat: init-drops-project-visibility-row" --body-file <report>`. The report names tracking issue 492 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, goal 3, §I, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Manual actions | `tests/publisher/test_init_remote.py::test_manual_actions_are_printed` |
| distribution / Observed done | `tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted` |
| distribution / Unreadable state | `tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed` (unchanged; its `project-read` case follows `PROJECT_ROWS`) |
