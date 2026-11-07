## 0. Delivery start

- [x] 0.1 Run `agent-process start_change detect-secrets-utf8-mode --planner Claude --implementer Claude` (tracking issue 471), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_init_config.py::_baseline()` replace the `Yelp/detect-secrets` entry with the local hook of design D1 (`name: detect-secrets`, `stages: EDIT_AND_GATE`, the pin from `pin['detect-secrets']`)
- [x] 1.2 Extract from `test_baseline_runs_tests_once_they_exist` a module-level helper. It takes the seeded `repo: local` entry by hook id, writes it alone into a fresh git repository, and returns a `run()` that commits and runs `pre-commit run --hook-stage manual --all-files` with extra environment. The `pytest` test calls it, and it keeps passing
- [x] 1.3 Add `test_seeded_secret_scan_decodes_utf8` (design D4) on that helper. Its file `ru2.md` holds `ключ сервиса: ` followed by an `aws_secret_access_key` assignment of the AWS documentation example key; mark the test line `pragma: allowlist secret`. It asserts a non-zero exit and `ru2.md:1` in stdout
- [x] 1.4 Run `agent-process check_red tests/publisher/test_init_config.py::test_created_config_carries_the_baseline tests/publisher/test_init_config.py::test_seeded_secret_scan_decodes_utf8` and commit RED with these ticks

## 2. Template

- [x] 2.1 Apply design D1 to `skills/agent-process/templates/pre-commit-config.yaml`: put the local hook where the `Yelp/detect-secrets` repository was, with a one-line comment that `-X utf8` stops the scanner from skipping files the locale cannot decode (spec distribution: Init seeds the baseline toolchain); verify `python -m pytest tests/publisher/test_init_config.py -q` is green
- [x] 2.2 Amend in place `.agent-process/docs/adr/0035-init-seeds-a-baseline-quality-toolchain.md`. Decision Outcome: "every check is a standard tool through its own hook repository" gets the detect-secrets exception. D2: `detect-secrets` is a local `language: python` hook under `-X utf8`, with the deletion condition of design D1. D3: its pin is the `additional_dependencies` line. Consequences: `pre-commit autoupdate` does not move that pin. Confirmation: add `test_seeded_secret_scan_decodes_utf8`. Verify `python -m pytest tests/agent_process/test_adr_records.py -q` is green, then commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change detect-secrets-utf8-mode`, then `gh pr create --title "fix: detect-secrets-utf8-mode" --body-file <report>`. The report names tracking issue 471 as a plain reference, carries the scenario-to-test map, gives the consumer migration of design's Migration Plan, and states the principles it interacts with (goal 1, §I, §IV, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Created config | `tests/publisher/test_init_config.py::test_created_config_carries_the_baseline` (expected baseline updated) |
| distribution / Tests run once they exist | `tests/publisher/test_init_config.py::test_baseline_runs_tests_once_they_exist` (moved onto the shared helper) |
| distribution / Secret in a file the locale cannot decode | `tests/publisher/test_init_config.py::test_seeded_secret_scan_decodes_utf8` |
| distribution / Existing config keeps its hooks | `tests/publisher/test_init_config.py::test_existing_config_keeps_its_hooks` (unchanged) |
