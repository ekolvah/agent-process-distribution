## 0. Delivery start

- [x] 0.1 Run `agent-process start_change agent-working-time --planner Claude --implementer Claude` (tracking issue 425), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/agent_process/test_task_readings.py`, give `_Grafana` a per-session `active` dict (default `s-a` 1800, `s-b` 900), matched by the existing `_matches` the way `starts` is. `prometheus` answers the `claude_code_active_time_seconds_total` query from it and the token-start query from `starts`. Add `agent_hours` to `_HEADER` and `_TELEMETRY`, and `"agent_hours": "0.75"` to `test_task_pr_merged`'s expected row. Add `test_agent_time_recorded`: one active-time query is sent, at `merged_at`, carrying `type="cli"`, `resets(`, `session_id=~"s-a|s-b"`, `vcs_repository_name="o/r"` and the window `[5400s]`, and the row's `agent_hours` is `0.75`. In `test_bound_session_without_telemetry`, drop `s-b` from `active` too and assert `agent_hours` is `0.50` with the gap unchanged. Add `test_active_time_counter_reset` (`s-b` missing from `active`, as the query's `and` drops a reset session: empty `agent_hours`, `cost_usd` written, `gap` holds `agent_hours: no reset-free active time of s-b`, exit 1)
- [x] 1.2 Add `test_hours_panel` to `tests/publisher/test_dashboard.py` with the existing `_render` and `_data_panels`, and move `test_one_repository`'s inline override map into a helper that both tests use. For one repository, the panel whose query reads `hours` also reads `agent_hours`, and the two fields have distinct display names. The table's `indexByName` puts `agent_hours` at the index of `hours` plus one
- [x] 1.3 Run `agent-process check_red` with the node ids of 1.1–1.2 and commit RED with these ticks

## 2. Readings

- [ ] 2.1 In `.agent-process/scripts/task_readings.py`, add `agent_hours` after `hours` in `COLUMNS`, and add the D2 query over `_telemetry`'s window with its gap (spec: Agent time is the sessions' CLI active time; Merged task records its readings). Verify `tests/agent_process/test_task_readings.py`
- [ ] 2.2 Commit the group with its ticks

## 3. Dashboard

- [ ] 3.1 In `skills/agent-process/templates/per-task-dashboard.json`, apply D3 to the hours panel (id 19) and to the table's `indexByName` (spec: The dashboard shows agent time beside hours). Verify `tests/publisher/test_dashboard.py`
- [ ] 3.2 Commit the group with its ticks

## 4. Documents

- [ ] 4.1 In `.agent-process/docs/telemetry-measurement-setup.md` *Per-task readings*, add the `agent_hours` row (the D2 query and its gap). In the opening question, add agent time beside time to merge. Verify `tests/agent_process/test_doc_links.py`
- [ ] 4.2 Commit the group with its ticks

## 5. Verify

- [ ] 5.1 Run `/simplify` without an argument and commit its edits
- [ ] 5.2 Run `openspec validate --strict --all`
- [ ] 5.3 Run the `test` that `.github/agent-process-quality.json` declares

## 6. Host state

- [ ] 6.1 Run `.agent-process/scripts/task_readings.py --pr 419 --csv <scratch>` and then `--pr 422`, with `GITHUB_REPOSITORY`, `GRAFANA_URL` and the token from the owner's environment. Verify each scratch row's `agent_hours` equals the D2 query run by hand over its window, and record both for the PR report
- [ ] 6.2 Read `aqxk4q`'s version with `get_dashboard_by_uid`, re-import it from `agent-process dashboard ekolvah/agent-process-distribution`, and read the version again. Render the hours panel with `get_panel_image` and confirm that the `to merge` series and its trend show as before. Record the versions and the observation for the PR report

## 7. Deliver

- [ ] 7.1 Run `agent-process archive_change agent-working-time`, then `gh pr create --title "feat: agent-working-time" --body-file <report>`. The report names tracking issue 425 as a plain reference and carries the scenario-to-test map, the 6.1–6.2 records and the design's post-merge dispatch for PR 401–422 as the person's step
- [ ] 7.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure; if a push changed the template, repeat 6.2 once before the last `wait_for_pr`

## Scenario → test map

| Scenario | Test |
| --- | --- |
| measurement / Task PR merged | `tests/agent_process/test_task_readings.py::test_task_pr_merged` |
| measurement / First task of a repository | `tests/agent_process/test_task_readings.py::test_first_task_of_a_repository` |
| measurement / Re-run for a recorded PR | `tests/agent_process/test_task_readings.py::test_rerun_for_a_recorded_pr` |
| measurement / File with an earlier header | `tests/agent_process/test_task_readings.py::test_file_with_an_earlier_header` |
| measurement / Agent time recorded | `tests/agent_process/test_task_readings.py::test_agent_time_recorded` |
| measurement / Counter reset | `tests/agent_process/test_task_readings.py::test_active_time_counter_reset` |
| measurement / Hours panel | `tests/publisher/test_dashboard.py::test_hours_panel` |
