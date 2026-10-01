## 0. Delivery start

- [x] 0.1 Run `agent-process start_change start-change-worktree-exclude --planner Claude --implementer Claude` for tracking issue 292. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/start-change-worktree-exclude`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_start_change.py`, add `test_main_checkout_stays_clean` (spec *Main checkout stays clean*), parametrized with ids `absent` and `present` over an `info/exclude` of the `_clone` fixture without and with a pre-existing `/.claude/worktrees/` line: after `start_change.main(_START, gh=Gh(root=root, git_runner=_run), root=root)`, `git -C root status --porcelain --untracked-files=all` is empty and `.git/info/exclude` holds the line exactly once
- [x] 1.2 In `test_parallel_changes`, replace the assertion that the start's new status lines start with `?? .claude/` by `assert not new` (the start adds no status line to its checkout)
- [x] 1.3 Add `test_exclude_fails` beside `test_worktree_listing_fails` (spec *Worktree listing fails*), parametrized over `git rev-parse` failing through `Gh(fail_on=…)` and the resolved `info/exclude` being a directory: exit 1, stderr names the failure (`rev-parse`, resp. the exclude path), and `_develops(gh) == []`. Extend `Gh` in `tests/publisher/delivery_fakes.py` to answer `git -C <root> rev-parse --path-format=absolute --git-path info/exclude` with `<root>/.git/info/exclude` (document the answer in its docstring)
- [x] 1.4 Run `agent-process check_red "tests/publisher/test_start_change.py::test_main_checkout_stays_clean[absent]" tests/publisher/test_start_change.py::test_parallel_changes tests/publisher/test_start_change.py::test_exclude_fails` and verify each fails in its body (status line `?? .claude/`; no `rev-parse` call, so no exit 1). `[present]` passes before the fix by construction (the line already hides the worktree) and guards the no-duplicate append, so it is not in the RED set. Commit as `test(implementation): start_change keeps its worktrees out of the main checkout's status`

## 2. Fix

- [x] 2.1 `skills/agent-process/scripts/start_change.py`: add `exclude_worktrees(main, gh)` beside `WORKTREES` (design D2, D3) — resolve the file with `git -C <main> rev-parse --path-format=absolute --git-path info/exclude`, create its parent when absent, append `/.claude/worktrees/` (preceded by a newline when the file does not end with one) only when no line equals it; re-raise an `OSError` as `RuntimeError` naming the path (D4). Call it in `start_change` right after `main` is resolved, before `prune_merged_worktrees`; add one sentence to the module docstring. Verify `python -m pytest tests/publisher/test_start_change.py -q` passes. Commit as `fix(implementation): start_change excludes .claude/worktrees/ from the main checkout's status`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [x] 4.1 With a clean worktree, run `agent-process archive_change start-change-worktree-exclude`. Verify that it archives the delta into `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: start-change-worktree-exclude" --body-file <report>`. The report references the tracking issue plainly, never with `Closes`, and carries the scenario → test map and the root cause from proposal — Why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation` / Main checkout stays clean → `tests/publisher/test_start_change.py::test_main_checkout_stays_clean`
- `implementation` / Merged change's worktree → `tests/publisher/test_start_change.py::test_merged_changes_worktree` (existing)
- `implementation` / Started from inside the previous change's worktree → `tests/publisher/test_start_change.py::test_started_from_inside_the_previous_changes_worktree` (existing; real git, so it also runs the exclude step from a linked worktree's cwd)
- `implementation` / Cleanup fails → `tests/publisher/test_start_change.py::test_cleanup_fails` (existing)
- `implementation` / Parallel changes → `tests/publisher/test_start_change.py::test_parallel_changes` (assertion changed in 1.2)
- `implementation` / Plan committed → `tests/publisher/test_start_change.py::test_plan_committed` (existing)
- `implementation` / Worktree step fails after the branch exists → `tests/publisher/test_start_change.py::test_worktree_step_fails_after_branch_exists` (existing)
- `implementation` / Worktree listing fails → `tests/publisher/test_start_change.py::test_worktree_listing_fails` (existing), `tests/publisher/test_start_change.py::test_exclude_fails`
