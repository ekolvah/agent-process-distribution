## 0. Delivery start

- [x] 0.1 Run `agent-process start_change archive-validates-main-specs --planner Claude --implementer Claude` (tracking issue 525), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_pr_delivery.py` lift the git setup of `test_ticks_left_for_the_archive` (real `_runner`, `git()` wrapper, `run` that stubs only `git push`, init and user config) into a module helper, and add `test_archive_leaves_a_placeholder_purpose` on it: committed main specs `alpha` (valid) and `gamma` (placeholder Purpose, untouched by the change), and a committed change shaped like the fixture of `test_planning_workflow.py::test_review_archives_with_the_change` whose deltas add a requirement to `alpha` and create `beta` without `## Purpose`; run `archive_change` with that `run`, so the pinned OpenSpec runs for real; assert exit 2, `'beta'` and `placeholder` in stderr, no `git push` called and `HEAD` unchanged. Then write a file outside `openspec/`, re-run, and assert exit 2 naming it in stderr and `HEAD` unchanged; remove it. Then replace beta's placeholder in `openspec/specs/beta/spec.md` with a 50+ character Purpose, re-run, and assert exit 0, one `git push`, a clean worktree and an archive commit carrying `openspec/specs/alpha/spec.md` with the added requirement and `openspec/specs/beta/spec.md` with that Purpose (the untouched `gamma` did not block)
- [x] 1.2 Run `agent-process check_red tests/publisher/test_pr_delivery.py::test_archive_leaves_a_placeholder_purpose`, verify it fails on the exit code (today the archive runs and commits the placeholder), and commit RED with the group 1 ticks

## 2. Implementation

- [x] 2.1 In `skills/agent-process/scripts/archive_change.py` implement design decisions 1–2: one `OPENSPEC_CMD` prefix for every `npx` call; the resume check of decision 2 before the clean-worktree check; after the lock removal, `validate <capability> --type spec --strict` for each `spec.md` under the archived change's `specs/` whose main spec exists, the capability named by its parent path relative to `specs/` with `as_posix()`, and on a `RuntimeError` of a `validate` call only print it with the decision 1 line and return 2; update the docstring's exit codes and recovery; verify 1.1 passes and `python -m pytest tests/publisher/test_pr_delivery.py tests/publisher/test_session_binding.py -q` is green (their fixtures have no spec deltas, so no `validate` call reaches their stubs)
- [x] 2.2 In `skills/agent-process/SKILL.md` Delivery, after "never a direct edit of `openspec/specs/`", add the exception of design decision 3: ", except a placeholder `## Purpose`, which only a direct edit replaces", and add "except a placeholder `## Purpose`" to the asserted phrases of `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change`; verify `python -m pytest tests/publisher/test_planning_workflow.py -q` is green. Commit 2.1–2.2 with their ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change archive-validates-main-specs`, then `gh pr create --title "fix: archive-validates-main-specs" --body-file <report>`. The report names the tracking issue as a plain reference, carries the scenario-to-test map, states design **Risks** and names the principles it interacts with (§IV, §V, §VII)
- [ ] 4.2 Run `gh pr merge <PR> --auto --squash`, then `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| implementation / Archive commit | `tests/publisher/test_pr_delivery.py::test_archive_commit` |
| implementation / Ticks left for the archive | `tests/publisher/test_pr_delivery.py::test_ticks_left_for_the_archive` |
| implementation / Stale archive lock | `tests/publisher/test_pr_delivery.py::test_archive_commit` |
| implementation / Archive leaves a placeholder Purpose | `tests/publisher/test_pr_delivery.py::test_archive_leaves_a_placeholder_purpose` (first run) |
| implementation / Re-run after the Purpose is written | `tests/publisher/test_pr_delivery.py::test_archive_leaves_a_placeholder_purpose` (re-run) |
