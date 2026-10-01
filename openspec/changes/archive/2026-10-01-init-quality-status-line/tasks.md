## 0. Delivery start

- [x] 0.1 Run `agent-process start_change init-quality-status-line --planner Claude --implementer Claude` for tracking issue 290. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/init-quality-status-line`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 `tests/publisher/test_init.py::test_quality_command_marker`: select the lines starting `quality: ` instead of `manual quality-command: `; for `absent` and `malformed` assert one such line naming `QUALITY` and containing `CI runs no tests`, placed before the first line starting `manual `, and in every case assert no line starts `manual quality-command`; for `declared` assert no `quality: ` line. Update the docstring to the status line
- [x] 1.2 `tests/publisher/test_init_remote.py`: in `_manual_rows`, keep the guard that the `manual` rows end the output but let it hold for none (`lines[len(lines) - len(manual):] == manual`, no `assert manual`), and in `test_observed_manual_rows_are_omitted` assert `manual == []`; verify the other callers of `_manual_rows` still pass with `python -m pytest tests/publisher/test_init_remote.py -q -k "not test_observed_manual_rows_are_omitted"`
- [x] 1.3 `tests/publisher/test_planning_workflow.py::test_install_asks_no_quality_command`: assert `"quality-command" not in install` (design D2) and update the docstring to say Install step 4 does not list the status line (#290)
- [x] 1.4 Run `agent-process check_red "tests/publisher/test_init.py::test_quality_command_marker[absent]" "tests/publisher/test_init.py::test_quality_command_marker[malformed]" tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted tests/publisher/test_planning_workflow.py::test_install_asks_no_quality_command` and verify RED. Commit as `test(distribution): init reports the missing quality command as status`

## 2. Status line

- [x] 2.1 `skills/agent-process/scripts/init.py` (D1): `_manual` returns only `manual.rows(...)` and its docstring drops the quality clause; `run` prints, inline and right before the `manual` rows, the line `quality: {quality.DECLARATION} declares no test -- CI runs no tests until the change that adds the first tests declares {"test": "<command>"}` while `_test_declared(ctx.root)` is false. In the module docstring, replace "a `quality-command` row says so" with the `quality:` line printed before the `manual` rows. Verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_init_remote.py tests/publisher/test_init_conflicts.py -q` passes
- [x] 2.2 `skills/agent-process/SKILL.md` Install step 4 (D2): delete the sentence "The `quality-command` row stays while no `test` is declared: CI runs no tests until then." Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` passes. Commit 2.1–2.2 as `fix(distribution): init reports the missing quality command as status, not a manual row`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [x] 4.1 With a clean worktree, run `agent-process archive_change init-quality-status-line`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: init-quality-status-line" --body-file <report>`. The report references the tracking issue plainly, never with `Closes` (#290), carries the scenario → test map and the reproduction of proposal — Why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Install without tests → `tests/publisher/test_init.py::test_quality_command_marker[absent]`, `[malformed]`
- `distribution` / Declared quality command → `tests/publisher/test_init.py::test_quality_command_marker[declared]`
- `distribution` / Upgrade over a passed test command → unchanged: `tests/publisher/test_init_conflicts.py::test_upgrade_over_passed_test_conflicts`
- `distribution` / Observed done → `tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted`
- `distribution` / Unreadable state → unchanged: `tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed`
