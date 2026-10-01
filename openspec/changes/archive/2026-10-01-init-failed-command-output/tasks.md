## 0. Delivery start

- [x] 0.1 Run `agent-process start_change init-failed-command-output --planner Claude --implementer Claude` for tracking issue 279. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/init-failed-command-output`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_init.py`, add `test_failure_names_both_streams` (spec *Output on both streams*) beside `test_failure_keeps_absent_streams_visible`, reusing its `Context` construction through a shared helper: the runner returns exit 1, stdout `cause` and stderr `failed to push`. The `InstallError` message contains `exited 1`, `failed to push` and `cause`, with `failed to push` before `cause`. Run `agent-process check_red tests/publisher/test_init.py::test_failure_names_both_streams` and verify it fails in its body on the missing `cause`. Commit as `test(distribution): init names both streams of a failed command`

## 2. Fix

- [x] 2.1 `skills/agent-process/scripts/init.py` `Context.call`: when both streams are `None`, keep `output not captured`; otherwise join the stripped non-empty streams (stderr, stdout) with a newline. Verify `python -m pytest tests/publisher/test_init.py -q -k failure` passes, including every case of `test_failure_keeps_absent_streams_visible`. Commit as `fix(distribution): init names a failed command's stdout beside stderr`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [x] 4.1 With a clean worktree, run `agent-process archive_change init-failed-command-output`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: init-failed-command-output" --body-file <report>`. The report references the tracking issue plainly (#279), never with `Closes`, and carries the scenario → test map and the root cause from proposal — Why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Output on both streams → `tests/publisher/test_init.py::test_failure_names_both_streams`
- `distribution` / Output not captured → `tests/publisher/test_init.py::test_failure_keeps_absent_streams_visible` (existing; its `None`/`None` case)
