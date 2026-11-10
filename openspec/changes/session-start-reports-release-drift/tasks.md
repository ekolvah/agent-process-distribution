## 0. Delivery start

- [x] 0.1 Run `agent-process start_change session-start-reports-release-drift --planner Claude --implementer Claude` (tracking issue 484), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_plugin.py`, with `plugin_env` loaded in-process (as `_plugin_env` loads it) and its `main` run for `session-start` with `CLAUDE_PROJECT_DIR` at a `tmp_path` project and no `CLAUDE_PLUGIN_DATA`, so nothing installs: `test_session_start_reports_release_drift` (config block records `3.29.0`: the printed JSON's `systemMessage` and `additionalContext` name `agent-process release drift`, `3.29.0`, `init.VERSION` and `/agent-process:init`; parametrized with `CLAUDE_PROJECT_DIR` unset and the cwd at the project), `test_session_start_silent_on_release` (parametrized: block records `init.VERSION`, config without the block, no config — nothing printed for the release), `test_session_start_release_undecidable` (config is a directory: the marker names `cannot check`); each asserts `main` returns 0
- [x] 1.2 In `tests/publisher/test_plugin.py` add `test_init_imports_without_site_packages` (design D2): `python -I -S -c` with the scripts directory on `sys.path` imports `init` and exits 0, so no third-party import in its chain can break the hook before the environment exists
- [x] 1.3 In `tests/publisher/test_start_change.py` set `_INSTALL_FIX` to `/agent-process:init`; in `tests/publisher/test_planning_workflow.py` assert `agent-process release drift` and `/agent-process:init` in `test_install_names_the_skill_marker` and add the marker to the launcher-span exclusions
- [x] 1.4 Run `agent-process check_red tests/publisher/test_plugin.py::test_session_start_reports_release_drift tests/publisher/test_plugin.py::test_session_start_release_undecidable tests/publisher/test_start_change.py::test_release_drift tests/publisher/test_planning_workflow.py::test_install_names_the_skill_marker` and commit RED with these ticks; `test_session_start_silent_on_release` and `test_init_imports_without_site_packages` pass before the code and are committed with them as regression guards

## 2. Release drift at session start

- [x] 2.1 Per design D2–D5: `plugin_env.py` gains the gated, guarded drift reader and joins its marker with the environment marker in one JSON; `init.release_drift` names `/agent-process:init` beside the path to the Install anchor of `SKILL.md`; update both docstrings; `SKILL.md` Install's session-start paragraph names `agent-process release drift` and its fix. Verify `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_start_change.py tests/publisher/test_planning_workflow.py -q` is green, then commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change session-start-reports-release-drift`, then `gh pr create --title "feat: session-start-reports-release-drift" --body-file <report>`. The report names tracking issue 484 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, §I, §IV, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Repository behind the plugin | `tests/publisher/test_plugin.py::test_session_start_reports_release_drift` |
| distribution / Release current or not installed | `tests/publisher/test_plugin.py::test_session_start_silent_on_release` |
| distribution / Release undecidable | `tests/publisher/test_plugin.py::test_session_start_release_undecidable` |
| distribution / Release recorded | n/a: unchanged; `tests/publisher/test_init_config.py::test_config_block_records_release` |
| distribution / Release drift | `tests/publisher/test_start_change.py::test_release_drift` |
| distribution / Publisher checkout | n/a: unchanged; `tests/publisher/test_start_change.py::test_publisher_checkout_is_exempt` |
