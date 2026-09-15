## 0. Delivery start

- [x] 0.1 `grep -q "^approve" openspec/changes/v2-1d-archive-before-pr/architect-review.md`;
  tracking issue #125 exists (priority High, asked at creation);
  `gh issue develop -c 125 --name v2-1d-archive-before-pr` from fresh origin/main;
  `python .agent-process/scripts/set_status.py 125 "In Progress" --priority High`;
  `gh issue comment 125 --body "planner: Claude; implementer: Claude"`.

## 1. RED

- [x] 1.1 `tests/publisher/test_delivery_scripts.py::test_archive_commit` rewritten for
  `archive_change`: call order `archive → commit → push`, no review request, no wait, the own task
  ticked when its command is on a continuation line, plus the stale-lock and
  dirty-worktree exits; `test_none_capture_is_an_error` parametrized on
  `archive_change`. `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change`:
  in the `tasks` rule, "priority" precedes `gh issue create` and `archive_change.py` precedes
  `gh pr create`; `test_pinned_openspec` reads `archive_change.py`. Run
  `python -m pytest tests/publisher --junitxml .pytest-report.xml`; verify
  `python .agent-process/scripts/check_red.py --report .pytest-report.xml
  tests/publisher/test_delivery_scripts.py::test_archive_commit
  tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` exits 0; commit.

## 2. Archive before the PR

- [ ] 2.1 `git mv .agent-process/scripts/finish_change.py .agent-process/scripts/archive_change.py`;
  drop the review request and the `wait_for_pr` call, keep the clean-worktree and lock
  checks; `_mark_own_task` matches the whole task item; docstring says what it does; verify `test_archive_commit`,
  `test_none_capture_is_an_error` green; commit.
- [ ] 2.2 `openspec/config.yaml` `tasks` rule: Group 0 asks the priority before
  `gh issue create`; Deliver group in the new order with the archived `tasks.md` as the
  place of the later ticks and of a re-run; verify `test_tasks_of_a_new_change`,
  `test_pinned_openspec` green; commit.
- [ ] 2.3 `agent-process.md` step 3 names the new order (one sentence); ADR 0027 gains the
  observation (a post-archive push cost a review round on every PR of #111); verify
  `test_doc_links`, `test_doc_narrative`, `test_adr_records` green; commit.

## 3. Verify

- [ ] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` green.
- [ ] 3.2 `python .agent-process/scripts/ci_check.py` green.

## 4. Deliver

- [ ] 4.1 `git status --short` empty;
  `python .agent-process/scripts/archive_change.py v2-1d-archive-before-pr` (marks this
  task, archives, commits, pushes); verify `openspec/specs/implementation/spec.md` carries
  the `archive_change` requirement and no `.openspec-archive.lock` is tracked.
- [ ] 4.2 `gh pr create --title v2-1d-archive-before-pr --body-file <report>` (change name,
  #125 as a plain reference, the scenario → test map, deferrals);
  `python .agent-process/scripts/request_codex_review.py --request <PR>`; verify
  `gh pr view` shows the PR whose first commit is the archive.
- [ ] 4.3 `python .agent-process/scripts/wait_for_pr.py <PR>`; apply every unresolved thread,
  push, re-request, at most three rounds; the fourth leaves the rest to the person with a
  reply; ticks and round notes go to `openspec/changes/archive/<date>-v2-1d-archive-before-pr/tasks.md`;
  verify exit 0. The person merges.

## Scenario → test map

- implementation / Archive commit → `test_archive_commit`
- implementation / Stale archive lock → `test_archive_commit`
- implementation / Tasks of a new change → `test_tasks_of_a_new_change`
- planning / Behaviour change → `n/a: process behaviour; observed on this PR (its first commit is the archive)`
