## 0. Delivery start

- [x] 0.1 Run `agent-process start_change edit-lint-surfaces-git-failure --planner Claude --implementer Claude` for tracking issue 369. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/edit-lint-surfaces-git-failure`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_edit_lint.py` add `test_git_failure_inside_a_repository_is_visible`, parametrized over three states of an adopted `lint_repo` with a `FINDING` hook (design decision 6): `dubious` — the hook's environment carries `GIT_TEST_ASSUME_DIFFERENT_OWNER=1`; `extension` — `core.repositoryformatversion 1` and `extensions.zzz true` in the repository's config; `gitfile` — the edited file lies in a directory whose `.git` file reads `gitdir: <tmp_path>/missing`. Assert exit 2, `edit-time lint is not active:` in stderr, and git's message in stderr (`dubious ownership`, `zzz`, `missing`). Add a `git-dir` case to `test_file_outside_adopted_repository_is_silent`: the edited file is `<adopted repo>/.git/info/exclude` (decision 2); it already passes and guards the silence of decisions 1 and 2
- [x] 1.2 Run `agent-process check_red tests/publisher/test_edit_lint.py::test_git_failure_inside_a_repository_is_visible`. Verify that it prints `RED: 3 failed` and exits 0. Commit as `test(edit_lint): a git failure inside a repository skips edit-time lint silently`

## 2. Visible git failure

- [ ] 2.1 In `skills/agent-process/scripts/edit_lint.py` `adopted_root`: run git with `LC_ALL=C` set and `LANGUAGE` removed from the inherited environment (decision 3); check `stdout`/`stderr is None` before the exit code (decision 5); on a non-zero exit return None only when stderr starts with `fatal: not a git repository (or any ` (decision 1) or `fatal: this operation must be run in a work tree` (decision 2), else print `edit-time lint is not active: <stderr>` to stderr and exit 2 (decision 4). Update the module docstring's last sentence. Verify that `python -m pytest tests/publisher/test_edit_lint.py tests/publisher/test_plugin.py -q` passes. Commit as `fix(edit_lint): a git failure inside a repository is a marker, not a silent skip`

## 3. Verify

- [ ] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change edit-lint-surfaces-git-failure`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: edit-lint-surfaces-git-failure" --body-file <report>`. The report references tracking issue #369 plainly, never with `Closes`. It carries the scenario → test map and the residuals of design Risks (a reworded discovery message, invalid `HEAD`, `core.bare=true` silent in a misconfigured checkout, locale pinning untested because `ubuntu-latest` has no translated catalogue)
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving them. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Commit-stage finding → `tests/publisher/test_edit_lint.py::test_commit_stage_finding_reaches_the_agent`, `tests/publisher/test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository`
- `distribution` / Only pre-push hooks declared → `tests/publisher/test_edit_lint.py::test_only_pre_push_hooks_run_nothing`
- `distribution` / Worktree file → `tests/publisher/test_edit_lint.py::test_worktree_file_uses_the_worktree_root`
- `distribution` / Worktree branch config → `tests/publisher/test_edit_lint.py::test_worktree_branch_config_runs`
- `distribution` / File outside an adopted repository → `tests/publisher/test_edit_lint.py::test_file_outside_adopted_repository_is_silent`
- `distribution` / Git fails inside a repository → `tests/publisher/test_edit_lint.py::test_git_failure_inside_a_repository_is_visible`
- `distribution` / pre-commit missing → `tests/publisher/test_edit_lint.py::test_pre_commit_that_cannot_run_is_visible`
- `distribution` / This repository's edit-time lint → `tests/publisher/test_plugin.py::test_publisher_lints_at_edit_time`
