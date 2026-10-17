## 0. Delivery start

- [x] 0.1 Run `agent-process start_change per-task-rates --planner Claude --implementer Claude` (tracking issue 447), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 Revise `tests/publisher/test_dashboard.py::test_rate_panels` for scenario *Rate panels* with the file's helpers: each panel carries its D1 computed column, its rate override gives it unit `suffix:/100 req` on the right axis, the window trend and the `per task` override stay on the count, and `organize` also hides `api_requests`
- [x] 1.2 Run `agent-process check_red tests/publisher/test_dashboard.py::test_rate_panels` and commit the revised RED with these ticks

## 2. Rate panels

- [x] 2.1 Apply D1 to panels 22 and 23 of `skills/agent-process/templates/per-task-dashboard.json` (spec measurement: The dashboard draws step events per 100 requests next to the count); verify `tests/publisher/test_dashboard.py`
- [x] 2.2 In the `aqxk4q` paragraph of `.agent-process/docs/telemetry-measurement-setup.md`, say that compactions and failed plus denied calls also draw a per-100-API-requests line on a right axis and that the table keeps the counts
- [x] 2.3 Commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change per-task-rates`, then `gh pr create --title "feat: per-task-rates" --body-file <report>`; the report names the tracking issue as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (§VII, goal 1)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure
- [ ] 4.3 After merge, re-import `aqxk4q` from `agent-process dashboard ekolvah/agent-process-distribution` and record the version it returns; run panel 23's query through `grafana_api_request` `/api/ds/query` and confirm PR 401 matches the D1 observation; render panel 23 with `get_panel_image` and confirm a right axis scaled to the rate; record all three in the PR

## Scenario → test map

| Scenario | Test |
| --- | --- |
| measurement / Rate panels | `tests/publisher/test_dashboard.py::test_rate_panels` |
