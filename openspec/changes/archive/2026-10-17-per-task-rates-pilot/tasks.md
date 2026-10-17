## 0. Delivery start

- [x] 0.1 Run `agent-process start_change per-task-rates-pilot --planner Claude --implementer Claude` (tracking issue 459), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 Add `test_rate_panels` to `tests/publisher/test_dashboard.py`, reusing `_data_panels`, `_selectors` and `_overrides`: for the panels titled `compactions` and `failed + denied calls`, assert `api_requests` is among `_selectors(panel)`; the null `filterByValue` names `api_requests`; a `calculateField` binary step divides the count by `api_requests`, aliased `per 100 requests`, and comes before the `organize` that excludes `api_requests`; its override sets unit `percentunit` and `custom.axisPlacement` `right`
- [x] 1.2 Run `agent-process check_red tests/publisher/test_dashboard.py::test_rate_panels` and commit RED with these ticks

## 2. Panels

- [x] 2.1 In `skills/agent-process/templates/per-task-dashboard.json`, panel 23: add the `api_requests` column and its entry in the null filter, the binary step after the null filter and an `organize` excluding `api_requests` (D1), and the override with unit `percentunit` and the right axis (D2); panel 22: the same, the binary step after the `failed + denied` sum and `api_requests` added to its `organize`. Verify `python -m pytest tests/publisher/test_dashboard.py`
- [x] 2.2 Commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares; then, with the person's confirmation, re-import `aqxk4q` from `agent-process dashboard ekolvah/agent-process-distribution` over its UID and record in the PR body the `per 100 requests` value the `compactions` panel shows for PR 401 (expected 1.46%) — the test passed; the live re-import was skipped by the person's decision, recorded in the PR body

## 4. Deliver

- [x] 4.1 Run `agent-process archive_change per-task-rates-pilot`, then `gh pr create --title "feat: per-task-rates-pilot" --body-file <report>`. The report names the tracking issue as a plain reference, the principles the change interacts with, and the scenario-to-test map
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| measurement / Rate panels | `tests/publisher/test_dashboard.py::test_rate_panels` |
