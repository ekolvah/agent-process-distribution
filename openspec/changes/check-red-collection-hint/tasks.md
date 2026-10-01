## 0. Delivery start

- [x] 0.1 Run `agent-process start_change check-red-collection-hint --planner Claude --implementer Claude` for tracking issue 251. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/check-red-collection-hint`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [ ] 1.1 Add `test_test_of_code_that_does_not_exist_yet` to `tests/publisher/test_check_red.py`, a live run as `test_run_leaves_the_tree_clean` is (design, Risks): in `tmp_path` write `tests/test_greet.py` starting with `from newpkg.greet import greet` and one test calling it, and `.github/agent-process-quality.json`; `chdir` there; parametrize the selection over the node id (pytest rc 4) and the file path (rc 2); run `check_red.main(...)` and assert `SystemExit` code 2 and that stderr names `test_greet` and `NotImplementedError`
- [ ] 1.2 Run `agent-process check_red tests/publisher/test_check_red.py::test_test_of_code_that_does_not_exist_yet` and verify both parametrizations fail on the stderr assertion. Commit as `test(implementation): check_red names the way to RED on a collection failure`

## 2. Gate

- [ ] 2.1 `skills/agent-process/scripts/check_red.py` (D1): in the incomplete-run branch, after the `did not complete the run` line, print to stderr the conditioned sentence — a test module that fails at collection runs no test; if its import target does not exist yet, add it as a stub whose body raises `NotImplementedError` and re-run on the same node ids. No report read; the exit stays 2. Extend the module docstring's boundary paragraph with one sentence naming issue 251. Verify `python -m pytest tests/publisher/test_check_red.py -q` passes. Commit as `fix(implementation): check_red names the way to RED on a collection failure`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change check-red-collection-hint`. Verify that it archives the delta into `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: check-red-collection-hint" --body-file <report>`. The report references the tracking issue plainly, never with `Closes` (#251), carries the scenario → test map and the reproduction of proposal — Why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation` / Test of code that does not exist yet → `tests/publisher/test_check_red.py::test_test_of_code_that_does_not_exist_yet`
- `implementation` / Configuration that cuts the run → unchanged: `tests/publisher/test_check_red.py::test_interrupted_run_is_no_verdict`
