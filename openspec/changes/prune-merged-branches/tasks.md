## 0. Delivery start

- [x] 0.1 Run `agent-process start_change prune-merged-branches --planner Claude --implementer Claude` (tracking issue 436), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/delivery_fakes.py`, give `Gh` a `pr_heads` map answered as `headRefOid` beside `state` by `gh pr view <branch> --json state,headRefOid`, and, without a `git_runner`, answer `git for-each-ref` and `git remote prune origin` with `""`
- [x] 1.2 In `tests/publisher/test_start_change.py::test_merged_changes_worktree`, give `done` and `dirty` their tips as PR heads, assert `done`'s branch is deleted (replacing the assertion that it survives) and the `kept: <dirty>` line names the uncommitted changes
- [x] 1.3 Add `test_merged_changes_branch` on `_clone` with real git: `gone` (no worktree, at its PR head, pushed to the bare `origin`, fetched, then deleted there), `later` (merged, one commit after its head), `none` (no PR); assert `gone` and `origin/gone` are deleted and the deletion printed, `kept: later` is on stderr, `none` and `origin/main` exist, and no `gh pr view main` call was made
- [x] 1.4 Parametrize `test_cleanup_fails` on `_clone` with real git and `fail_on` over `git worktree remove`, `git branch -D` and `git remote prune`: each yields a `kept:` line naming the worktree, branch or remote and the error, and `start_change` exits 0; in `test_started_from_inside_the_previous_changes_worktree` assert the branch `prev` survives and no `gh pr view prev` call was made in any field form
- [x] 1.5 Run `agent-process check_red` with the node ids of `test_merged_changes_worktree`, `test_merged_changes_branch` and the `git branch -D` and `git remote prune` cases of `test_cleanup_fails`, and commit RED with these ticks; the `git worktree remove` case and `test_started_from_inside_the_previous_changes_worktree` already pass and stay as regression guards run in 2.1

## 2. Cleanup

- [x] 2.1 In `skills/agent-process/scripts/start_change.py`, replace `prune_merged_worktrees` with `prune_merged_changes` (D3): `git remote prune origin` (D4); one `git for-each-ref refs/heads` with name, tip and worktree path; skip the main worktree's and the cwd's branches; one `gh pr view <branch> --json state,headRefOid`; when `MERGED` and tip equals `headRefOid`, remove a clean worktree under `.claude/worktrees/`, then `git branch -D`, printing each (D1); a dirty worktree, a differing tip and every failure a `kept:` line, `no pull requests found` silent (D5); rewrite the cleanup rule of the module docstring to match. Verify `python -m pytest tests/publisher/test_start_change.py`
- [x] 2.2 In `skills/agent-process/SKILL.md` Group 0, "removes the clean worktrees of merged changes" becomes "removes the clean worktrees and the local branches of merged changes"; in `CLAUDE.md` add the exception of D2 to the force-delete line. Verify with `grep -n "local branches of merged" skills/agent-process/SKILL.md` and `grep -n "PR head" CLAUDE.md`
- [x] 2.3 Commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change prune-merged-branches`, then `gh pr create --title "feat: prune-merged-branches" --body-file <report>`. The report names the tracking issue as a plain reference, the principles the change interacts with, and the scenario-to-test map
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| implementation / Main checkout stays clean | `tests/publisher/test_start_change.py::test_main_checkout_stays_clean` (unchanged) |
| implementation / Started from inside the previous change's worktree | `tests/publisher/test_start_change.py::test_started_from_inside_the_previous_changes_worktree` |
| implementation / Parallel changes | `tests/publisher/test_start_change.py::test_parallel_changes` (unchanged) |
| implementation / Plan committed | `tests/publisher/test_start_change.py::test_plan_committed` (unchanged) |
| implementation / Worktree step fails after the branch exists | `tests/publisher/test_start_change.py::test_worktree_step_fails_after_branch_exists` (unchanged) |
| implementation / Worktree listing fails | `tests/publisher/test_start_change.py::test_worktree_listing_fails` (unchanged) |
| implementation / Merged change's worktree | `tests/publisher/test_start_change.py::test_merged_changes_worktree` |
| implementation / Merged change's branch | `tests/publisher/test_start_change.py::test_merged_changes_branch` |
| implementation / Cleanup fails | `tests/publisher/test_start_change.py::test_cleanup_fails` |
