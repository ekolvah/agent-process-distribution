## 0. Delivery start

- [x] 0.1 No Group 0: a change of its own on the branch of PR 145 (`tasks` rule, review loop), issue 132 tracks it; the branch and the Status are the PR's

## 1. RED first

- [x] 1.1 `tests/publisher/test_delivery_scripts.py`: `test_behavioural_change` and `test_runner_owns_the_selection` monkeypatch `check_red.subprocess.run` with a fake that records the command, writes the fixture at the `--junitxml=` argument and returns a `CompletedProcess`; `test_behavioural_change` asserts `cmd[:3] == [sys.executable, "-m", "pytest"]`, `--tb=no`, `--maxfail=0`, `-p no:cacheprovider`, one `--junitxml=`, the node id last, `--test` → `SystemExit(2)`; `_RUNNER`, `_fake_runner`, `test_partial_report_is_no_verdict` and the launch/split cases go; module docstring follows. `tests/publisher/test_planning_workflow.py`: `test_tasks_of_a_new_change` asserts `check_red.py <node ids>` in the rule and `"--test" not in rule`. Verify `python .agent-process/scripts/check_red.py tests/publisher/test_delivery_scripts.py::test_behavioural_change tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` exits 0; commit `test(implementation): RED — check_red runs its own pytest under its own configuration`

## 2. The runner and its configuration (D1)

- [x] 2.1 `.agent-process/scripts/check_red.py`: `--test`, `shlex`, `os`, the split and launch branches go; `cmd = [sys.executable, "-m", "pytest", "--tb=no", "--maxfail=0", "-p", "no:cacheprovider", f"--junitxml={report}", *paths]`; `evaluate_report` loses `at_least` and its paragraph; the module docstring states the boundary. Verify `python -m pytest tests/publisher/test_delivery_scripts.py tests/publisher/test_planning_workflow.py -q` green except `test_tasks_of_a_new_change`, and `python .agent-process/scripts/check_red.py tests/publisher/test_delivery_scripts.py::test_behavioural_change` exits 1 (green test → not RED, the runner ran under `-p no:cacheprovider`); commit `fix(implementation): check_red runs its own pytest under its own configuration`

## 3. The `tasks` rule and the record

- [x] 3.1 `openspec/config.yaml`, rule `tasks`, Group 1: `python .agent-process/scripts/check_red.py <node ids>` (the script runs `python -m pytest` under its own configuration with a report path of its own). `.agent-process/docs/architecture/agent-process.md` step 3 names the same call. ADR 0027, the bullet of issue 132: the runner is the script's own, the flags and the boundary, the count guard deleted (round 8). `openspec/changes/archive/2026-09-19-v2-2d-check-red-test/design.md` D1: one pointer paragraph to this change. Verify `python -m pytest tests/publisher/test_planning_workflow.py tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py tests/agent_process/test_adr_records.py -q` green; commit `docs(planning): the tasks rule names check_red without a runner argument; ADR 0027 on the boundary`

## 4. Verify

- [x] 4.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` valid and `python .agent-process/scripts/ci_check.py` green

## 5. Deliver

- [x] 5.1 `python .agent-process/scripts/archive_change.py v2-2d-check-red-own-runner` (marks its own task, archives, commits, pushes); then the review loop of PR 145 continues (task 6.3 of the archived `v2-2d-check-red-test`)

## Scenario → test map

- implementation / Behavioural change → `tests/publisher/test_delivery_scripts.py::test_behavioural_change` (RED → return, GREEN → exit 1)
- implementation / Runner given → the same `test_behavioural_change` (the command is `python -m pytest` of `sys.executable` with `--tb=no`, `--maxfail=0`, `-p no:stepwise`, `-o cache_dir=` beside one `--junitxml=`, the node id last; `--test` → 2) and `test_runner_owns_the_selection` (the report is judged whole)
- implementation / Configuration that cuts the run → the same `test_behavioural_change` (the flags in the command) and `test_interrupted_run_is_no_verdict` (rc 2, 3, 4 → exit 2 whatever the report says; rc 5 → the report is judged; review round 9); the pytest behaviour behind them is the observation in design.md D1; the rule text → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change`
