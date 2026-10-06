## 0. Delivery start

- [x] 0.1 Run `agent-process start_change edit-lint-file-repo-root --planner Claude --implementer Claude` for tracking issue 360. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/edit-lint-file-repo-root`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/lint_harness.py`, move `ADOPTION_MARKER` there from `tests/publisher/test_plugin.py` (which imports it), and make `lint_repo` take `adopted: bool = True`: when set it writes an empty marker; it then commits everything with the `git` helper (`commit -q -m init`), so a `git worktree` can be added. In `test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository` drop the two lines that write the marker. Verify that `python -m pytest tests/publisher/test_edit_lint.py tests/publisher/test_plugin.py -q` still passes
- [x] 1.2 In `tests/publisher/test_edit_lint.py` add `test_worktree_file_uses_the_worktree_root`, parametrized with ids `allowed` and `other` over `allowed/x.md` → exit 0 and empty stdout/stderr, and `other/x.md` → exit 2 with `finding:` in stderr: a `lint_repo` whose hook is `{**FINDING, "exclude": "^allowed/"}`, `git worktree add -q <tmp>/wt`, the file written in the worktree, run with the main checkout as `cwd` (design D1)
- [x] 1.3 Add `test_worktree_branch_config_runs`: `lint_repo` with `PRE_PUSH` only; in a worktree on a new branch commit a config whose `pre-commit`-stage hook prints `branch:` and fails; edit `<wt>/a.py` from the main checkout → exit 2 with `branch:` in stderr (design D1)
- [x] 1.4 Add `test_file_outside_adopted_repository_is_silent`, parametrized with ids `no-repo` and `not-adopted` over a file in `tmp_path` outside any repository and `a.py` of a `lint_repo(..., FINDING, adopted=False)` sibling, run from an adopted `lint_repo(..., FINDING)` → exit 0, empty stdout and stderr (design D2, D3)
- [x] 1.5 Run `agent-process check_red "tests/publisher/test_edit_lint.py::test_worktree_file_uses_the_worktree_root[allowed]" tests/publisher/test_edit_lint.py::test_worktree_branch_config_runs tests/publisher/test_edit_lint.py::test_file_outside_adopted_repository_is_silent`. The `[other]` case already passes today (it guards against over-silencing) and so stays out. Verify that it prints `RED: 4 failed, 0 green` and exits 0, each failing in its body. Commit with the Group 1 ticks as `test(distribution): edit_lint lints in the edited file's repository root`

## 2. Root and adoption

- [x] 2.1 In `skills/agent-process/scripts/edit_lint.py`, turn the `pre-commit` lookup into one check over `pre-commit` and `git`, printing `edit-time lint is not active: <name> is not on PATH` for the first missing one (design D4). Verify that `python -m pytest tests/publisher/test_edit_lint.py -k cannot_run -q` passes
- [x] 2.2 Resolve the root with `git -C <dirname of the absolute path> rev-parse --show-toplevel` (`encoding="utf-8"`); a non-zero exit, or a root without `.github/workflows/agent-process.yml`, exits 0 silently; run `pre-commit` with `cwd=<root>` and that same absolute path in `--files`, since pre-commit makes a relative entry absolute against its own working directory. Update the module docstring: the working directory is the edited file's repository root (design D1–D3). Verify that `python -m pytest tests/publisher/test_edit_lint.py tests/publisher/test_plugin.py -q` passes
- [x] 2.3 In `.agent-process/docs/adr/0034-edit-time-lint-runs-the-projects-pre-commit-config.md`, amend the first Decision bullet: the run happens in the root of the repository holding the edited file, and a file outside an adopted repository is skipped. Verify that `python -m pre_commit run --hook-stage pre-commit --files .agent-process/docs/adr/0034-edit-time-lint-runs-the-projects-pre-commit-config.md` passes. Commit 2.1–2.3 as `fix(distribution): edit_lint lints in the edited file's repository root`

## 3. Verify

- [ ] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change edit-lint-file-repo-root`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: edit-lint-file-repo-root" --body-file <report>`. The report references the tracking issue plainly (#360), never with `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Commit-stage finding → `tests/publisher/test_edit_lint.py::test_commit_stage_finding_reaches_the_agent`, `tests/publisher/test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository`
- `distribution` / Only pre-push hooks declared → `tests/publisher/test_edit_lint.py::test_only_pre_push_hooks_run_nothing`
- `distribution` / Worktree file → `tests/publisher/test_edit_lint.py::test_worktree_file_uses_the_worktree_root`
- `distribution` / Worktree branch config → `tests/publisher/test_edit_lint.py::test_worktree_branch_config_runs`
- `distribution` / File outside an adopted repository → `tests/publisher/test_edit_lint.py::test_file_outside_adopted_repository_is_silent`
- `distribution` / pre-commit missing → `tests/publisher/test_edit_lint.py::test_pre_commit_that_cannot_run_is_visible`
- `distribution` / This repository's edit-time lint → `tests/publisher/test_plugin.py::test_publisher_lints_at_edit_time`
