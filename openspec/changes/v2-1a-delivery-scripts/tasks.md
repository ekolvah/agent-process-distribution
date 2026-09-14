## 0. Delivery

- [x] 0.1 Tracking issue #111 (priority set); branch `v2-1a-delivery-scripts` from fresh
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

## 3. Verify

- [ ] 3.1 `npx -y @fission-ai/openspec@latest validate --strict --all` green.
- [ ] 3.2 `python .agent-process/scripts/ci_check.py` green.

## 4. Deliver

- [ ] 4.1 `git status --short` empty; push (output to a file); `gh pr create --title
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
