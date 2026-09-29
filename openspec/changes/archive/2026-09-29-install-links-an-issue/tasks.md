## 0. Delivery start

- [x] 0.1 Run `agent-process start_change install-links-an-issue --planner Claude --implementer Claude` for tracking issue 247. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/install-links-an-issue`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Harness (design — Risks, third item): `tests/publisher/conftest.py` `sandbox` makes `root` a clone of a bare `origin` (`git init --bare -b main`) with one initial commit on `main` pushed; `init_harness.py` `snapshot` skips `.git`; `FakeGitHub` answers `repo view` with `defaultBranchRef {name: "main"}` and holds `issues` (number, title, state) and `pulls` (number, head, base, body, url) with `issue list --state open --json number,title`, `issue create --title --body`, `pr list --head --state open|all --json number,state,url` and `pr create --base --head --title --body` in the observed shapes of design D4, each requiring `--repo ekolvah/consumer`, with `pulls[i].state` settable to `MERGED` / `CLOSED`, all in `state()`; `LABELS` gains `onboarding-branch`, `onboarding-commit`, `onboarding-issue`, `onboarding-push`, `onboarding-pr` in D4 order; `LINE` accepts the new labels. The retry test's `_final` adds the remote branches of `origin` and the tree of the installation commit
- [x] 1.2 Tests in `tests/publisher/test_init_remote.py` (D1–D4): replace `test_only_project_writes_remote` with `test_remote_writes_are_project_and_pr` (every `gh` write is `project copy`, `project link`, `issue create` or `pr create`; the only `git push` targets `agent-process/install-<CURRENT>`; `main` has one commit locally and on `origin`); `test_installed_footprint_is_closed` compares `git diff --name-only main..HEAD` with `OPENSPEC_OUTPUT | CONSUMER_FILES` and expects a clean worktree; `test_dry_run_writes_nothing_remote` also allows `issue list` and `pr list` as reads and asserts no new branch and the same `HEAD`. Add `test_install_opens_the_pr` (*Fresh install opens the PR*: one open PR, head B, base `main`, body starts `Closes #<N>` for the one open issue `Install agent-process <CURRENT>`, output line `written onboarding-pr:` holds its URL), `test_open_issue_is_reused` (issue pre-seeded → no `issue create`, body names it), `test_nothing_to_install` (after the first run, `git switch main` and merge B locally, rerun: no onboarding line, no new `gh` write, no new branch), `test_rerun_after_merge` (after the first run mark the PR `MERGED`, rerun on B: all five onboarding lines `unchanged` naming the PR URL, no new `gh` write, no push), and `test_unsafe_starting_point` parametrized `dirty` / `other-branch` / `branch-not-checked-out` / `pr-closed` (exit 2, a `conflict onboarding-branch:` line naming the cause, `snapshot` and `github.state()` unchanged)
- [ ] 1.3 Run `agent-process check_red tests/publisher/test_init_remote.py::test_remote_writes_are_project_and_pr tests/publisher/test_init_remote.py::test_installed_footprint_is_closed tests/publisher/test_init_remote.py::test_dry_run_writes_nothing_remote tests/publisher/test_init_remote.py::test_install_opens_the_pr tests/publisher/test_init_remote.py::test_open_issue_is_reused tests/publisher/test_init_remote.py::test_nothing_to_install tests/publisher/test_init_remote.py::test_rerun_after_merge "tests/publisher/test_init_remote.py::test_unsafe_starting_point[dirty]" "tests/publisher/test_init_remote.py::test_unsafe_starting_point[other-branch]" "tests/publisher/test_init_remote.py::test_unsafe_starting_point[branch-not-checked-out]" "tests/publisher/test_init_remote.py::test_unsafe_starting_point[pr-closed]" tests/publisher/test_init.py::test_retry_after_each_write` and verify each fails in its body. Commit as `test(distribution): init opens the installation PR`

## 2. Installer

- [x] 2.1 `skills/agent-process/scripts/init.py` (D2–D4): `_repository` also reads `defaultBranchRef`; add the five onboarding steps per the D4 table, classified from reads and re-read in `apply`, present only when a file step is planned or the current branch is B; `_run` puts `onboarding-branch` before the file steps and the other four after the Project steps; the `onboarding-pr` written line names the PR URL re-read with `gh pr list`; every `gh issue` / `gh pr` command pins `--repo`. Update the module docstring's step list and its "Nothing is committed or pushed" sentence. Verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_init_remote.py tests/publisher/test_init_config.py tests/publisher/test_init_conflicts.py -q` passes

## 3. Install procedure

- [x] 3.1 `skills/agent-process/SKILL.md` Install: step 3 has the person do the `review-secret` row (set `CLAUDE_CODE_OAUTH_TOKEN`) before the yes, so the first head's `agent-review` runs with it; step 4 says the confirmed run opens the installation PR, linked to its issue, and prints it (name neither branch nor title: `init` prints them), leaving the checkout on that branch; the person then does the other printed `manual` rows (keep `plugin-channel`), reviews and merges the PR, then switches to the default branch and pulls; drop "The installer never commits or pushes…". Step 5 names that PR's number in `activate_protection --pr <N>`. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` passes. Commit as `feat(distribution): init opens the installation PR` with footer `BREAKING CHANGE: init --confirm commits on agent-process/install-<version>, pushes it and opens the installation PR`

## 4. Verify

- [x] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 5. Deliver

- [x] 5.1 With a clean worktree, run `agent-process archive_change install-links-an-issue`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "feat: install-links-an-issue" --body-file <report>`. The report references the tracking issue plainly, never with `Closes` (#247), carries the scenario → test map and the observation of proposal — Why, and notes that the first-run green `link` is observed on the next installation run (#117)
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Confirmed run → `tests/publisher/test_init_remote.py::test_remote_writes_are_project_and_pr`
- `distribution` / Dry-run → `tests/publisher/test_init_remote.py::test_dry_run_writes_nothing_remote`
- `distribution` / Fresh install opens the PR → `tests/publisher/test_init_remote.py::test_install_opens_the_pr`
- `distribution` / Open issue is reused → `tests/publisher/test_init_remote.py::test_open_issue_is_reused`
- `distribution` / Nothing to install → `tests/publisher/test_init_remote.py::test_nothing_to_install`
- `distribution` / Rerun after the merge → `tests/publisher/test_init_remote.py::test_rerun_after_merge`
- `distribution` / Unsafe starting point → `tests/publisher/test_init_remote.py::test_unsafe_starting_point`
- `distribution` / Fresh repository → `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed` (now the installation commit's diff)
- `distribution` / Retry after an interrupted write → `tests/publisher/test_init.py::test_retry_after_each_write` (now also interrupts after each onboarding write)
