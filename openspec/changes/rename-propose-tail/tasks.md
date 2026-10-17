## 0. Delivery start

- [x] 0.1 Run `agent-process start_change rename-propose-tail --planner Claude --implementer Claude` (tracking issue 456), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [ ] 1.1 Add `"create_tracking_issue"` to the `absent` tuple of `test_tasks_of_a_new_change` in `tests/publisher/test_planning_workflow.py` (design: The old name is a guarded absence); run `agent-process check_red` with its node id and commit RED with this tick

## 2. Rename

- [ ] 2.1 `git mv skills/agent-process/scripts/create_tracking_issue.py skills/agent-process/scripts/finish_propose.py`; rename its function and docstring usage line to `finish_propose` (design: The name is `finish_propose`)
- [ ] 2.2 Replace `create_tracking_issue` with `finish_propose` in the other edited files of the proposal's Impact (tests: `load_script`, `_SCRIPTS`, `MOVED_SCRIPTS`, `test_plan_approved`); add the ADR 0027 dated entry in a few lines (design: No alias for the old name, Which documents change)
- [ ] 2.3 Verify `test_tasks_of_a_new_change` is GREEN and commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change rename-propose-tail`, then `gh pr create --title "refactor: rename-propose-tail" --body-file <report>`; the report names tracking issue 456 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, §I, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| planning / Review finding | `tests/publisher/test_planning_workflow.py::test_review_finding` |
| planning / Review class without evidence | `tests/publisher/test_start_change.py::test_review_not_valid` |
| planning / Over-long rule or bespoke check | `tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check` |
| planning / Plan without a standard approach | `tests/publisher/test_start_change.py::test_plan_without_a_standard_approach` |
| planning / Plan without a prior issue | `tests/publisher/test_start_change.py::test_plan_without_a_prior_issue` |
| planning / Addition without evidence | `tests/publisher/test_start_change.py::test_addition_without_evidence` |
| planning / Rework verdict | `tests/publisher/test_planning_workflow.py::test_rework_verdict` |
| planning / Plan approved | `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue`, `tests/publisher/test_planning_workflow.py::test_plan_approved` |
| planning / Existing tracking issue | `tests/publisher/test_start_change.py::test_existing_tracking_issue` |
| planning / Review archives with the change | `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change` |
| planning / Review round | `tests/publisher/test_planning_workflow.py::test_review_round` |
| planning / Plan from an existing issue | `tests/publisher/test_planning_workflow.py::test_plan_from_an_existing_issue` |
| measurement / Second task in one session | `tests/publisher/test_session_binding.py::test_second_task_in_one_session` |
| measurement / Plan creates the issue | `tests/publisher/test_session_binding.py::test_plan_creates_the_issue` |
| measurement / No session variable | `tests/publisher/test_session_binding.py::test_no_session_variable` |
| measurement / Plan and implementation in two sessions | `tests/publisher/test_session_binding.py::test_plan_and_implementation_in_two_sessions` |
| distribution / Release recorded | `tests/publisher/test_init_config.py::test_config_block_records_release` |
| distribution / Release drift | `tests/publisher/test_start_change.py::test_release_drift` |
| distribution / Publisher checkout | `tests/publisher/test_start_change.py::test_publisher_checkout_is_exempt` |
