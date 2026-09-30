## 0. Delivery start

- [x] 0.1 Run `agent-process start_change init-empty-repository --planner Claude --implementer Claude` for tracking issue 271. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/init-empty-repository`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Harness per design D5, in `tests/publisher/init_harness.py`: `FakeGitHub.default_branch = "main"` and `FakeGitHub.empty = False`; `repo view` returns `defaultBranchRef.name` `""` when `empty`, else `default_branch`; `api repos/ekolvah/consumer` answers `{"default_branch": <default_branch>}`; `pr create` exits 1 when `--base` is not a branch on `origin` (`_pushed`); a helper `empty_origin(sb)` deleting `refs/heads/main` on `origin` and setting `empty = True`, `default_branch = "trunk"`, and a helper `empty_repository(sb)` = `empty_origin` plus deleting `refs/heads/main` and `refs/remotes/origin/main` in the clone (its unborn branch stays `main`). In `tests/publisher/test_init_remote.py`: `_gh_kind` counts `api repos/<repo>` without `--method`/`-X` as `read`; `_git_state` reads `HEAD` so that an unborn one is a state, not a `CalledProcessError`
- [x] 1.2 Add `test_repository_with_no_commits` (Scenario: Repository with no commits): on `empty_repository`, a dry-run exits 0, prints `planned onboarding-root`, and leaves `github.state()` and `_git_state` unchanged; a confirmed run then exits 0, `origin` has no `main`, `trunk` on `origin` has no parent and the tree of `git write-tree` of an empty index, `rev-list --count trunk..<BRANCH>` on `origin` is 1 and its diff names exactly the installer's files, the pushes are exactly `<root>:refs/heads/trunk` and `<BRANCH>`, and one open PR has base `trunk` and head `<BRANCH>`
- [x] 1.3 Add three `UNSAFE` rows (D4): `unpushed-history` (`empty_origin`) naming `git push -u origin HEAD:trunk`; `unborn-checkout` (the clone's `refs/heads/main` deleted) naming `git pull origin main`; `empty-dirty` (`empty_repository`, then an untracked file) naming `move them out of the worktree`. In `test_unsafe_starting_point` assert `"``" not in line`
- [x] 1.4 Run `agent-process check_red tests/publisher/test_init_remote.py::test_repository_with_no_commits "tests/publisher/test_init_remote.py::test_unsafe_starting_point[unpushed-history]" "tests/publisher/test_init_remote.py::test_unsafe_starting_point[unborn-checkout]" "tests/publisher/test_init_remote.py::test_unsafe_starting_point[empty-dirty]"` and verify each fails in its test body: the dry-run exits 2 with `` not `` `` for the empty repository, and the rows on their cause assertion. Verify the rest of `tests/publisher/test_init_remote.py` still passes with the harness change. Commit as `test(distribution): init installs into a repository with no commits`

## 2. The default branch's name (D2)

- [x] 2.1 `skills/agent-process/scripts/init.py`: when `_repository()` reads an empty `defaultBranchRef.name`, read `gh api repos/<owner>/<name>` through `_gh_json` and take `default_branch`; a missing or empty value raises `InstallError` naming the read. Pass `empty=True` to `onboarding.Target` (new field, default `False`). Verify `python -m pytest tests/publisher/test_init_remote.py -q` fails only the four tests of 1.4

## 3. The initial commit (D1, D3)

- [x] 3.1 `skills/agent-process/scripts/onboarding.py`: when `to.empty` and a file step is planned, `plan` returns `onboarding-root` (detail `an empty initial commit -> origin/<default>`) before `onboarding-branch`; its apply runs `write-tree`, `commit-tree -m "Initial commit"`, `push origin <sha>:refs/heads/<default>` (no force), `fetch origin <default>`; `onboarding-branch` then applies `git switch --no-track -c <branch> origin/<default>`, with detail `<branch> from the initial commit`. A comment names the tracking issue (#271). Verify `python -m pytest tests/publisher/test_init_remote.py::test_repository_with_no_commits -q` passes. Commit as `fix(distribution): init creates the base of a repository with no commits`

## 4. Conflicts (D4)

- [x] 4.1 `skills/agent-process/scripts/onboarding.py`: in the empty case, `plan` skips the `current != to.default` check (D4); a checkout whose `rev-parse --verify --quiet HEAD` succeeds and a worktree with changes return the D4 conflicts; in `_unsafe_start`, an unborn `HEAD` returns the `git pull origin <default>` conflict before the existing checks. Verify `python -m pytest tests/publisher/test_init_remote.py -q` passes. Commit as `fix(distribution): init names the starting points of an empty repository`

## 5. Docstrings

- [x] 5.1 `skills/agent-process/scripts/init.py` module docstring: `onboarding-root` in the step list (renumbering the rest and the `Steps 10-11` reference), the three conflicts in the conflict sentence, and the exception in "The default branch is never written". `onboarding.py`: the module and `plan` docstrings name `onboarding-root`. Verify `python -m pytest tests/publisher -q` passes. Commit as `docs(distribution): init's docstrings name the initial commit`

## 6. Verify

- [x] 6.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 6.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 7. Deliver

- [ ] 7.1 With a clean worktree, run `agent-process archive_change init-empty-repository`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 7.2 Run `gh pr create --title "fix: init-empty-repository" --body-file <report>`. The report references the tracking issue plainly, never with `Closes` (#271), carries the scenario → test map, the observations of proposal — Why, the dropped guard of design D1 with its catchers, and the probe repositories left for the person to delete
- [ ] 7.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 7.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Repository with no commits → `tests/publisher/test_init_remote.py::test_repository_with_no_commits`
- `distribution` / Unsafe starting point → `tests/publisher/test_init_remote.py::test_unsafe_starting_point` (new rows `unpushed-history`, `unborn-checkout`, `empty-dirty`; the no-empty-name assertion covers every row)
- `distribution` / Confirmed run (WHEN narrowed to a repository with commits) → unchanged: `tests/publisher/test_init_remote.py::test_remote_writes_are_project_and_pr`
- `distribution` / Dry-run, Fresh install opens the PR, Open issue is reused, Nothing to install, Rerun after the merge → unchanged: `tests/publisher/test_init_remote.py::test_dry_run_writes_nothing_remote`, `::test_install_opens_the_pr`, `::test_open_issue_is_reused`, `::test_nothing_to_install`, `::test_rerun_after_merge`
