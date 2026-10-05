## 0. Delivery start

- [x] 0.1 Run `agent-process start_change check-red-consumer-python --planner Claude --implementer Claude` for tracking issue 342. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/check-red-consumer-python`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_check_red.py`, add a helper that puts a directory holding an empty `python` (`python.exe` on Windows, mode 0o755 elsewhere) alone on `PATH` and returns its `shutil.which("python")`. In `test_behavioural_change`, use it and assert `cmd[:3] == [<that path>, "-m", "pytest"]` instead of `sys.executable`; update its docstring to "the `python` on `PATH`"
- [x] 1.2 Add `test_no_python_on_path`: `PATH` set to an empty directory, a valid declaration, the fake runner; assert exit 2, `python` in stderr, and no command recorded
- [x] 1.3 Run `AGENT_PROCESS_PYTHON=python agent-process check_red "tests/publisher/test_check_red.py::test_behavioural_change" "tests/publisher/test_check_red.py::test_no_python_on_path"` — the prefix because the unfixed `check_red` under the plugin environment is the bug itself; 2.3 checks the plain session run. Verify that it prints `RED: 2 failed` and exits 0, both failing in their body (the command starts with `sys.executable`; no exit 2). Commit as `test(implementation): check_red runs the python on PATH`

## 2. Runner

- [x] 2.1 In `skills/agent-process/scripts/check_red.py`, resolve `shutil.which("python")` after the declaration check and exit 2 with `check_red: \`python\` is not on PATH; …` when it is `None` (design D2); use it as `cmd[0]` (D1). Update the module docstring's runner sentence and the comment above `cmd`. Verify that `python -m pytest tests/publisher/test_check_red.py -q` passes
- [x] 2.2 In `skills/agent-process/SKILL.md` Group 1, replace "of its own interpreter" with "of the `python` on `PATH`". Verify that `python -m pytest tests/publisher -q` passes
- [x] 2.3 Run `agent-process check_red tests/publisher/test_check_red.py::test_runner_owns_the_selection` from the worktree, with `AGENT_PROCESS_PYTHON` set by the session. Verify that it now prints `not RED: 1 green test(s)` and exits 1 instead of `No module named pytest`. Commit as `fix(implementation): check_red runs the consumer's python`

## 3. Verify

- [x] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [x] 4.1 With a clean worktree, run `agent-process archive_change check-red-consumer-python`. Verify that it archives the delta into `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: check-red-consumer-python" --body-file <report>`. The report references the tracking issue plainly (#342), never with `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation` / Behavioural change → n/a: a process rule on the implementer, carried by Group 1 of this file
- `implementation` / Runner given → `tests/publisher/test_check_red.py::test_behavioural_change`
- `implementation` / No python on PATH → `tests/publisher/test_check_red.py::test_no_python_on_path`
- `implementation` / Configuration that cuts the run → `tests/publisher/test_check_red.py::test_behavioural_change`, `tests/publisher/test_check_red.py::test_interrupted_run_is_no_verdict`
- `implementation` / No quality command declared → `tests/publisher/test_check_red.py::test_refuses_without_quality_declaration`
- `implementation` / Run leaves the tree clean → `tests/publisher/test_check_red.py::test_run_leaves_the_tree_clean`
