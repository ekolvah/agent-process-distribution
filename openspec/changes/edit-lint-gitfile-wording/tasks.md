## 0. Delivery start

- [x] 0.1 Run `agent-process start_change edit-lint-gitfile-wording --planner Claude --implementer Claude` (tracking issue 477), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 no RED: test-only fix; the RED is CI run 42374569845 on git 2.56.0, local git is older

## 2. Test expectation

- [x] 2.1 In the gitfile case of `test_git_failure_inside_a_repository_is_visible`, expect `edit-time lint is not active: fatal: ` and update its comment; verify `python -m pytest tests/publisher/test_edit_lint.py` passes
- [x] 2.2 Update the comment above `_NOT_REPOSITORY_CODE` in `skills/agent-process/scripts/edit_lint.py` to name both git wordings of a missing gitdir
- [x] 2.3 Commit the group with its ticks as `test: expect git's fatal prefix, not its wording, for a missing gitdir`

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change edit-lint-gitfile-wording`, then `gh pr create --title "test: edit-lint-gitfile-wording" --body-file <report>`; the report names the tracking issue as a plain reference, carries the scenario-to-test map and states the principles it interacts with (§I, §V)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

- n/a: `skip_specs` — no delta scenario; the existing *Git fails inside a repository* stays mapped to `test_git_failure_inside_a_repository_is_visible`.
