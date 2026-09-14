## 0. Delivery

- [x] 0.1 Tracking issue exists, priority set (#111); branch `v2-1a-delivery-scripts` from fresh
  `origin/main`; `python .agent-process/scripts/set_issue_status.py 111 in-progress`.

## 1. Carried over from PR 121

- [x] 1.1 `set_status.py`, `wait_for_pr.py`, `finish_change.py`, `check_red.py --report`,
  `AGENTS.md` runner bullet, `.gitignore`, `tests/publisher/test_delivery_scripts.py` (RED and
  green history in PR 121); remove `openspec/changes/v2-1-planning-workflow/`; verify
  `python -m pytest tests/publisher/test_delivery_scripts.py -q` green; commit.

## 2. Review findings left open on PR 121

- [x] 2.1 RED: `test_class_scoped_node_id`, `test_issue_in_unlinked_project`; verify
  `check_red.py --report .pytest-report.xml <both ids>` exits 0; commit.
- [x] 2.2 `check_red._selects`: a node id ending in a class selects the class and its nested
  classes; `set_status._project_for`: an item in an unlinked Project → `ValueError` naming the
  issue's Projects and the linked ones; verify the two tests and
  `tests/agent_process/test_ci_check.py` green; commit.

## 2a. Review round 1 (PR 122)

- [x] 2a.1 RED: new head between the two settling polls restarts the settling; `finish_change`
  refuses a dirty worktree (exit 2, nothing archived); commit.
- [x] 2a.2 `wait_for_pr`: `headRefOid` is part of the settled identity; `finish_change`:
  `git status --porcelain` preflight; the `implementation` delta describes the script, the
  `tasks` rule requirement moves to `v2-1b-planning-schema`; the `state` delta describes
  `set_status --priority`, the "ask the person" clause moves with the rule; verify
  `test_delivery_scripts.py` green.

## 2b. Review round 2 (PR 122)

- [x] 2b.1 RED: a push between the settled poll and the thread query restarts the settling;
  `::` inside a `[params]` suffix is part of the test id; commit.
- [x] 2b.2 `wait_for_pr`: the thread query returns `headRefOid` and a differing head restarts
  the settling; `check_red._selects` splits `::` only before `[`; `finish_change` pins
  `@fission-ai/openspec@1.13.0` (the version `test_openspec_valid.py` validates against;
  PR 123 round 1); verify `test_pending_review`, `test_parametrized_node_id`; commit.

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` green.
- [x] 3.2 `python .agent-process/scripts/ci_check.py` green.

## 4. Deliver

- [x] 4.1 `git status --short` empty; push (output to a file); `gh pr create --title
  v2-1a-delivery-scripts --body-file <report>` (change name, part 1 of 3 of #111, the
  scenario → test map, deferrals); `python .agent-process/scripts/request_codex_review.py
  --request <PR>`; verify `gh pr view` shows the PR.
- [ ] 4.2 `python .agent-process/scripts/wait_for_pr.py <PR>`; apply every unresolved thread,
  push, re-request, at most three rounds; verify exit 0.
- [ ] 4.3 `python .agent-process/scripts/finish_change.py v2-1a-delivery-scripts`; verify the
  archive commit's checks green and no `.openspec-archive.lock` is tracked. The person merges.

## Scenario → test map

- Behavioural change → `test_behavioural_change`, `test_class_scoped_node_id`
- Tracking issue created → `test_tracking_issue_created`, `test_issue_in_unlinked_project`
- Priority field drift → `test_priority_field_drift`
- Pending review → `test_pending_review`
- Archive commit, Stale archive lock → `test_archive_commit`
- Merge → `n/a: observed on this PR`
