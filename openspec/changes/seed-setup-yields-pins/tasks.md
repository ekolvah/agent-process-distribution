## 0. Delivery start

- [x] 0.1 Run `agent-process start_change seed-setup-yields-pins --planner Claude --implementer Claude` (tracking issue 470), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_init.py` set `_seeded()["setup"]` to the rendered seed of design D1 (`$$` rendered as `$`) and remove the `pins` import, which only `_seeded` used
- [x] 1.2 Run `agent-process check_red "tests/publisher/test_init.py::test_quality_command_marker[fresh]"` and commit RED with these ticks

## 2. Seed

- [ ] 2.1 Apply design D1 to `skills/agent-process/templates/agent-process-quality.json` (spec distribution: Init asks for no quality command); verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_init_config.py -q` is green
- [ ] 2.2 Amend in place D3 and D4 of `.agent-process/docs/adr/0035-init-seeds-a-baseline-quality-toolchain.md`: the seed installs `pre-commit` and `pytest` unpinned in one install with the requirements, so the project's requirements own every version they pin, and D3 no longer claims `test_init.py` checks seeded pins; verify `python -m pytest tests/agent_process/test_adr_records.py -q` is green, then commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change seed-setup-yields-pins`, then `gh pr create --title "fix: seed-setup-yields-pins" --body-file <report>`; the report names tracking issue 470 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, §I, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Fresh install seeds the declaration | `tests/publisher/test_init.py::test_quality_command_marker[fresh]` (expected seed updated) |
| distribution / Project requirements own the tool versions | `tests/publisher/test_init.py::test_quality_command_marker[fresh]` asserts one install with the tools unpinned; pip keeping the pinned versions in one resolution is observed in design.md (D1, Standard approach) |
| distribution / Install without tests | `tests/publisher/test_init.py::test_quality_command_marker[existing-config]` (unchanged) |
| distribution / Declared quality command | `tests/publisher/test_init.py::test_quality_command_marker[declared]` (unchanged) |
| distribution / Upgrade over a passed test command | `tests/publisher/test_init_conflicts.py::test_upgrade_over_passed_test_conflicts` (unchanged) |
