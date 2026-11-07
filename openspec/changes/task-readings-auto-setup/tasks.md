## 0. Delivery start

- [x] 0.1 Run `agent-process start_change task-readings-auto-setup --planner Claude --implementer Claude` (tracking issue 473), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/init_harness.py`: `FakeGitHub.variables` becomes name → value and answers `variable list --json name,value` as well as today's `--json name` (update `test_init_remote.py::test_observed_manual_rows_are_omitted`, which calls `variables.add`); it handles `gh variable set NAME --body V` and `gh secret set NAME` with the value from the runner's `input` (argv and value recorded apart); `Runner` passes `input` through; add an in-memory `FakeGrafana` (datasources, dashboard titles, `faults` for `datasources` and `post`, posted dashboards recorded) with a log of every request, injected through the `Host` factory only by the new tests; a `secret-set` fault makes `gh secret set` exit 1; and a `grafana_config(home, url, token=…, token_file=…)` helper writing `~/.claude.json`
- [x] 1.2 Add `tests/publisher/test_init_readings.py`: `test_setup_planned_from_mcp_config` (dry-run: three `planned task-readings-*` lines with the URL and the datasource uid, no `gh … set`, no POST, no `manual task-readings` row, the token absent from stdout, stderr and every recorded argv); `test_setup_performed`, parametrized inline token / token file (confirm: the variable is the URL, the secret value is the token and came on `input`, one posted dashboard without `${DS_INFINITY}` and with the uid in its place, its URL printed, no row); `test_setup_observed` (three `unchanged`, no write); `test_setup_not_possible`, parametrized another `GRAFANA_URL` with the secret missing / no Infinity datasource / `datasources` 401 (exit 0, no dashboard line — for another URL no `task-readings-*` line, no `gh … set` and an empty Grafana request log — and the row ends with `(another stack: <URL>)`, `(not found: Infinity datasource in <URL>)` or `(cannot read: …401…)`); `test_another_stack_already_set` (another `GRAFANA_URL`, secret set: no `task-readings-*` line, no row — a guard of today's behaviour, green before and after); `test_setup_write_fails`, parametrized `secret-set` fault / `post` 403 (confirm: stderr names `task-readings-token` or `task-readings-dashboard` with the failure, not the token, exit 1)
- [x] 1.3 In `tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` assert the row ends with `(not found: grafana MCP server in ~/.claude.json)`
- [x] 1.4 Run `agent-process check_red` with the node ids of 1.2 except `test_another_stack_already_set`, and `tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed`; run the guard and `test_init_remote.py` green and commit RED with these ticks

## 2. Setup steps

- [ ] 2.1 In `skills/agent-process/scripts/manual.py` (design D1, D4–D6): the `Grafana` Protocol (`datasources()`, `dashboard_titles(query)`, `post_dashboard(json) -> url`), `Target.grafana` and `Target.gh_write`, `_names` reading `--json name,value` for variables, and `readings(t) -> Readings` reading the config through `_plugin_file` and the names through the shared reads, in the D6 order. Add `skills/agent-process/scripts/readings_setup.py` (D4, D7, D8), importing `manual` and never imported by it: the `urllib` Bearer client raising `manual.Unreadable` on a failed read, and `steps(t, readings) -> list[Step]` binding `${DS_INFINITY}` in `dashboard.render`'s output. Verify `python -m pytest tests/publisher/test_init_readings.py -q -k "planned or observed or not_possible"` is green
- [ ] 2.2 `manual.py`: the task-readings row prints from `readings(t)` after the writes, ending with `blocked`. `skills/agent-process/scripts/init.py` (D4 line budget): `run` moves to `steps.py` with an `input` argument and is imported back by name; the Grafana factory on `Host` and `Context`, passed in `_target` with `gh_write` (`ctx.call("gh", …, input=…)` with `check=True`); `input` on `Context.call`; the steps appended after the pre-push step. Verify `python -m pytest tests/publisher -q` is green and `wc -l skills/agent-process/scripts/init.py` ≤ 1000
- [ ] 2.3 If `tests/publisher/test_plugin.py` or the footprint list of `init_harness.py` enumerates shipped scripts, add `readings_setup.py`; verify `python -m pytest tests/publisher/test_plugin.py -q` is green, then commit the group with its ticks

## 3. Docs

- [ ] 3.1 Add `.agent-process/docs/adr/0048-init-sets-up-task-readings-from-the-grafana-mcp-config.md` (D1–D3, the token-copy risk; Confirmation names `test_init_readings.py`); point ADR 0041 D4 at it; in `skills/agent-process/SKILL.md` Install step 4 say the `task-readings` row appears only when `init` could not set it up and names why; update the row text in `.agent-process/docs/telemetry-measurement-setup.md`. Verify `grep -rn "manual task-readings" skills .agent-process/docs` shows only consistent wording, then commit with the ticks

## 4. Verify

- [ ] 4.1 Run `/simplify` without an argument and commit its edits
- [ ] 4.2 Run `openspec validate --strict --all`
- [ ] 4.3 Run the `test` that `.github/agent-process-quality.json` declares

## 5. Deliver

- [ ] 5.1 Run `agent-process archive_change task-readings-auto-setup`, then `gh pr create --title "fix: task-readings-auto-setup" --body-file <report>`. The report names tracking issue 473 as a plain reference, carries the scenario-to-test map, the token-copy risk, and the principles it interacts with (goal 1, goal 3, §II, §III, §IV, §VII)
- [ ] 5.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Review prerequisites | `tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed` (unchanged) |
| distribution / Readings prerequisites | `tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` |
| distribution / Setup planned from the MCP config | `tests/publisher/test_init_readings.py::test_setup_planned_from_mcp_config` |
| distribution / Setup performed | `tests/publisher/test_init_readings.py::test_setup_performed` |
| distribution / Setup observed | `tests/publisher/test_init_readings.py::test_setup_observed` |
| distribution / Setup not possible | `tests/publisher/test_init_readings.py::test_setup_not_possible` |
| distribution / Another stack already set | `tests/publisher/test_init_readings.py::test_another_stack_already_set` |
| distribution / Setup write fails | `tests/publisher/test_init_readings.py::test_setup_write_fails` |
