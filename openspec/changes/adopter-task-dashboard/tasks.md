## 0. Delivery start

- [x] 0.1 Run `agent-process start_change adopter-task-dashboard --planner Claude --implementer Claude` (tracking issue 416), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 Add `tests/publisher/test_dashboard.py`, running `SKILL_SCRIPTS / "dashboard.py"` (`tests/publisher/delivery_fakes.py`) as `test_edit_lint.py`'s `_run` does: `test_one_repository` (for `ekolvah/kinozal_scraper`: `__inputs` declares `DS_INFINITY`, there is no `uid`, and no `grafanacloud-infinity`, `__REPOSITORY__` or `agent-process-distribution/task-readings` remains; every data panel has exactly one query, on `${DS_INFINITY}`, with that repository's CSV URL and `'ekolvah/kinozal_scraper'` as `repository`; the table's query has `replace(task_id, 'issue-', '')` as `issue`, and `task_id` links to `https://github.com/${__data.fields.repository}/issues/${__data.fields.issue}`); `test_several_repositories` (two repositories: every data panel has refIds `A` and `B`, each with its own URL and `repository`, its first transformation is `merge`, and the title names both); `test_malformed_repository` over `kinozal_scraper`, `a/b/c`, `owner/` and no argument (exit 2, empty stdout, stderr names the argument or the usage)
- [x] 1.2 In `tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` assert the row carries `agent-process dashboard {CONSUMER}` and `Dashboards → New → Import`; add `dashboard.py` to `MOVED_SCRIPTS` and `per-task-dashboard.json` to `TEMPLATES` in `tests/publisher/test_plugin.py`
- [x] 1.3 Run `agent-process check_red` with the node ids of 1.1–1.2 and commit RED with these ticks

## 2. Render

- [x] 2.1 Add `skills/agent-process/templates/per-task-dashboard.json` from `get_dashboard_by_uid aqxk4q` version 23 with the D2 edits and the D3 computed columns, override and hidden `issue`
- [x] 2.2 Add `skills/agent-process/scripts/dashboard.py` (design D1, D2; spec: The dashboard renders for a list of repositories) with a module docstring giving usage and exit codes as the other scripts do; verify the 1.1 tests and `test_package_contents_are_closed`
- [x] 2.3 Commit the group with its ticks

## 3. Installer

- [x] 3.1 Append the D4 text to the `manual task-readings` row in `skills/agent-process/scripts/manual.py` (spec: Actions credentials are printed, not set); verify `test_readings_prerequisites_are_printed` and `test_observed_manual_rows_are_omitted`
- [x] 3.2 Commit the group with its ticks

## 4. Documents

- [x] 4.1 Write `.agent-process/docs/adr/0042-the-per-task-dashboard-renders-for-a-list-of-repositories.md` (design D1, alternatives, deletion condition: Infinity or Grafana gains a query over several URLs), and verify `tests/agent_process/test_adr_records.py`
- [x] 4.2 In `.agent-process/docs/telemetry-measurement-setup.md`, have the `aqxk4q` paragraph say it is the render of the template for this repository, and that an edit goes into the template and is re-imported; in *Adopters* add the render command for one or several repositories, the import with its Infinity datasource, and the public-repository limit; verify `tests/agent_process/test_doc_links.py`
- [x] 4.3 Commit the group with its ticks

## 5. Verify

- [x] 5.1 Run `/simplify` without an argument and commit its edits
- [x] 5.2 Run `openspec validate --strict --all`
- [x] 5.3 Run the `test` that `.github/agent-process-quality.json` declares

## 6. Host state

- [ ] 6.1 Read `aqxk4q`'s version with `get_dashboard_by_uid`, re-import it from `agent-process dashboard ekolvah/agent-process-distribution` (design D5), and read the version again; verify `get_dashboard_panel_queries aqxk4q` lists only this repository's URL on `grafanacloud-infinity`, and record both versions for the PR report
- [ ] 6.2 Render the table panel and one trend panel of `aqxk4q` with `get_panel_image` and confirm the rows and the trend show as before, with a `repository` column; confirm a `task_id` link opens `https://github.com/ekolvah/agent-process-distribution/issues/<N>`; record the observation for the PR report

## 7. Deliver

- [ ] 7.1 Open an issue in ekolvah/kinozal_scraper that holds the design's Confirmation steps with its first recorded task; run `agent-process archive_change adopter-task-dashboard`, then `gh pr create --title "feat: adopter-task-dashboard" --body-file <report>`; the report names tracking issue 416 as a plain reference, carries the scenario-to-test map, the 6.1 versions and the 6.2 observation, and names that kinozal issue as the holder of the deferred Confirmation
- [ ] 7.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure; after a push that changes the template or `dashboard.py`, repeat 6.1–6.2 before the next `wait_for_pr`

## Scenario → test map

| Scenario | Test |
| --- | --- |
| measurement / One repository | `tests/publisher/test_dashboard.py::test_one_repository` |
| measurement / Several repositories | `tests/publisher/test_dashboard.py::test_several_repositories` |
| measurement / Malformed repository | `tests/publisher/test_dashboard.py::test_malformed_repository` |
| distribution / Review prerequisites | `tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed` |
| distribution / Readings prerequisites | `tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` |
