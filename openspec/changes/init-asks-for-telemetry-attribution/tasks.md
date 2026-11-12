## 0. Delivery start

- [x] 0.1 Run `agent-process start_change init-asks-for-telemetry-attribution --planner Claude --implementer Claude` (tracking issue 475), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

Every consumer `.claude/settings.json` a Group 1 test seeds is written in the form `init` writes (`json.dumps(..., indent=2)` plus a final newline) and committed with `commit_seed` before the run, unless the test is about another form; `ATTRIBUTION` below is `vcs.repository.name=<CONSUMER>,vcs.repository.url.full=https://github.com/<CONSUMER>`.

- [x] 1.1 In `tests/publisher/conftest.py`, the autouse fixture `_no_session` also deletes `OTEL_RESOURCE_ATTRIBUTES` (design, **Tests**; `test_init.py` builds sandboxes without the `sandbox` fixture), with its docstring naming both
- [x] 1.2 In `tests/publisher/test_init_remote.py`, add `test_attribution_is_written` over two seeds, no consumer `.claude/settings.json` and `{"env": {"KEEP": "1"}, "permissions": {}}`: a `--dry-run` leaves the file as seeded, then a `--confirm` exits 0 and leaves `env.OTEL_RESOURCE_ATTRIBUTES == ATTRIBUTION` with every seeded key kept; neither output carries a `telemetry-attribution` row; a second `--confirm` prints `unchanged settings`
- [x] 1.3 Add `test_machine_attribution_is_kept` over two cases: `monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "team=media")`, and `env.OTEL_RESOURCE_ATTRIBUTES` = `team=media` in the sandbox's `~/.claude/settings.json` (`_user_settings`). A `--confirm` exits 0, the file has no `env` key, and one `manual telemetry-attribution` row names `ATTRIBUTION`, `replaces` and `team=media`
- [x] 1.4 Add `test_other_repository_attribution_is_manual`: `env.OTEL_RESOURCE_ATTRIBUTES` = `vcs.repository.name=other/repo`; a `--confirm` exits 0, leaves that value, and prints the row
- [x] 1.5 Add `test_hand_formatted_settings_is_manual`: the settings a fresh install writes (as in `test_installed_footprint_is_closed`, without `env`) plus `"model": "opus"`, serialised with `indent=4` and committed; a `--dry-run` exits 0 with `unchanged settings` and the row naming `not in the form init writes`
- [x] 1.6 Guards, passing before the change and left out of `check_red`: in `test_observed_manual_rows_are_omitted`, seed `env.OTEL_RESOURCE_ATTRIBUTES` = `service.version=1, vcs.repository.name=<CONSUMER>` (another pair and a space after the comma, design D2); in `tests/publisher/test_init_config.py::test_update_keeps_consumer_bytes` (a done file in another form, design D4), assert the output carries no `telemetry-attribution` row
- [x] 1.7 In `UNREADABLE`, add `telemetry-attribution` to the labels of `user-settings-malformed`, and add the cases `project-settings-shape` (`{"env": []}`) and `project-settings-value` (`{"env": {"OTEL_RESOURCE_ATTRIBUTES": 1}}`), both `--dry-run`, label `telemetry-attribution`. Add `test_malformed_project_settings_is_printed`: the file as `not json` (committed) is a `settings` conflict, so a `--dry-run` exits 2 as without this row; assert exit 2 and the row with `(cannot read: `
- [x] 1.8 In `test_installed_footprint_is_closed`, the expected settings carry `"env": {"OTEL_RESOURCE_ATTRIBUTES": ATTRIBUTION}`
- [x] 1.9 Run `agent-process check_red` with the node ids of 1.2–1.5, `test_malformed_project_settings_is_printed`, `test_installed_footprint_is_closed` and only the parametrized ids `test_unreadable_manual_state_is_printed[user-settings-malformed]`, `[project-settings-shape]`, `[project-settings-value]`; run the guards of 1.6 green; commit RED with the group's ticks

## 2. Implementation

- [ ] 2.1 Design D4, D2, D3: in `skills/agent-process/scripts/manual.py`, extract `_settings_env(path)` from `_identity_pending`, move `init._json_text` to `json_text`, and add `attribution(t)` (target value, done, blocked) over `t.root / ".claude" / "settings.json"`, `os.environ` and `t.home / ".claude" / "settings.json"`. Verify: `python -m pytest tests/publisher/test_init_remote.py -k "attribution or observed or unreadable or malformed_project or hand_formatted"`
- [ ] 2.2 Design D5: in `skills/agent-process/scripts/init.py`, read `_repository(ctx)` before `_consumer_steps`, pass `<owner>/<name>` to the `settings` render; `_settings_text` adds the value when `attribution` is neither done nor blocked, treats `manual.Unreadable` as left, and its no-op return requires the attribution done or left. Verify: `python -m pytest tests/publisher/test_init.py tests/publisher/test_init_remote.py tests/publisher/test_init_config.py tests/publisher/test_init_conflicts.py`
- [ ] 2.3 Design D6: add the `telemetry-attribution` row through `_outstanding` directly before `_readings_row` in `rows()`, printed while `attribution` is blocked or unreadable, with the text of D6. Verify: `python -m pytest tests/publisher/test_init_remote.py tests/publisher/test_init_readings.py`
- [ ] 2.4 Design D7: in `.agent-process/docs/telemetry-measurement-setup.md`, "Which label carries the project" replaces "An adopter sets the pairs by hand" and the paragraph on a tree without the `env` key with the write, its condition and the row; the `OTEL_RESOURCE_ATTRIBUTES` bullet of "Adopters" says the same in one clause. Verify: `git grep -n "by hand" -- .agent-process/docs/telemetry-measurement-setup.md` names no adopter attribution step. Commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change init-asks-for-telemetry-attribution`, then `gh pr create --title "fix: init-asks-for-telemetry-attribution" --body-file <report>`, then `gh pr merge <PR> --auto --squash`. The report names tracking issue 475 as a plain reference, carries the scenario-to-test map, and states the principles involved (goal 1, goal 3, §I, §IV, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

- Attribution written: `tests/publisher/test_init_remote.py::test_attribution_is_written`, `::test_installed_footprint_is_closed`
- Machine attribution kept: `tests/publisher/test_init_remote.py::test_machine_attribution_is_kept`
- Another repository's attribution: `tests/publisher/test_init_remote.py::test_other_repository_attribution_is_manual`
- Settings in another form: `tests/publisher/test_init_remote.py::test_hand_formatted_settings_is_manual`; guard `tests/publisher/test_init_config.py::test_update_keeps_consumer_bytes`
- Observed done: `tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted` (guard)
- Unreadable state: `tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed` (cases `user-settings-malformed`, `project-settings-shape`, `project-settings-value`) and `::test_malformed_project_settings_is_printed`
